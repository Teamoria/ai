"""RAG orchestration for the Teamoria Laravel platform."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.schemas.chat import ChatRequest, ChatSource
from app.services.ai_access_service import AiAccessService, AiContextBundle
from app.services.llm_service import LlmService


class RagService:
    """Collects visible platform context and asks the LLM for an answer."""

    def __init__(self, session: Session, llm_service: LlmService | None = None) -> None:
        self.access_service = AiAccessService(session)
        self.llm_service = llm_service or LlmService()

    def answer(self, request: ChatRequest) -> tuple[str, list[ChatSource]]:
        if request.user is None:
            return (
                "Laravel user context is required. Send user.id, user.company_id, and user.role from the backend proxy.",
                [],
            )

        bundle = self.access_service.context_for_user(request.user, request.project_id)
        sources = self._sources(bundle)
        context = "\n\n".join(source.content for source in sources)

        if not context:
            return (
                "I could not find visible Teamoria data for this user and project. "
                "Check the user's company/project membership or upload knowledge first.",
                [],
            )

        answer = self.llm_service.answer(request.question or request.message or "", context)
        return answer, sources

    def _sources(self, bundle: AiContextBundle) -> list[ChatSource]:
        sources: list[ChatSource] = []

        for task in bundle.tasks:
            sources.append(
                ChatSource(
                    content=self._task_content(task),
                    metadata={"type": "task", "id": str(task["id"]), "project_id": str(task["project_id"])},
                )
            )

        for upload in bundle.uploads:
            sources.append(
                ChatSource(
                    content=self._upload_content(upload),
                    metadata={"type": "upload", "id": str(upload["id"]), "project_id": upload.get("project_id")},
                )
            )

        for meeting in bundle.meeting_summaries:
            content = meeting.get("summary") or meeting.get("transcript") or ""
            if content:
                sources.append(
                    ChatSource(
                        content=f"Meeting file: {meeting.get('file_name')}\nSummary: {content}",
                        metadata={"type": "meeting_summary", "id": str(meeting["id"]), "upload_id": str(meeting["upload_id"])},
                    )
                )

        for chunk in bundle.knowledge_chunks:
            content = str(chunk.get("content") or "").strip()
            if content:
                sources.append(
                    ChatSource(
                        content=content,
                        metadata={
                            "type": "knowledge_chunk",
                            "id": str(chunk["id"]),
                            "project_id": chunk.get("project_id"),
                            "upload_id": chunk.get("upload_id"),
                        },
                    )
                )

        return sources[:40]

    def _task_content(self, task: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"Task: {task.get('title')}",
                f"Project: {task.get('project_name')}",
                f"Status: {task.get('status')}",
                f"Priority: {task.get('priority')}",
                f"Due date: {task.get('due_date')}",
                f"Description: {task.get('description') or ''}",
            ]
        )

    def _upload_content(self, upload: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"Upload: {upload.get('file_name')}",
                f"Type: {upload.get('file_type')}",
                f"Category: {upload.get('category')}",
                f"Scope: {upload.get('scope')}",
                f"Visibility: {upload.get('visibility')}",
                f"Status: {upload.get('status')}",
            ]
        )
