"""Chat session and message service."""

import logging

from app.core.database import get_session
from app.repositories.laravel_repository import LaravelRepository
from app.schemas.chat import (
    AiChatGenerateData,
    AiChatGenerateRequest,
    AiChatGenerateResponse,
    ChatRequest,
    ChatResponse,
    ChatSource,
)
from app.services.llm_service import LlmService
from app.services.rag_service import RagService


logger = logging.getLogger(__name__)


class ChatService:
    """Stateless project Q&A service."""

    def answer(self, request: ChatRequest) -> ChatResponse:
        if request.user is not None:
            with get_session() as session:
                answer, sources = RagService(session).answer(request)

            return ChatResponse(
                project_id=request.project_id,
                question=request.question or request.message or "",
                answer=answer,
                sources=sources,
            )

        sources = [
            ChatSource(content=context, metadata={"rank": index + 1})
            for index, context in enumerate(request.context[:5])
        ]
        context_text = " ".join(source.content for source in sources)

        if context_text:
            answer = f"Based on the project knowledge, {self._compact_answer(request.question, context_text)}"
        else:
            answer = (
                "I do not have project knowledge context in this request yet. "
                "Send relevant chunks from Laravel or call the upload processing endpoint first."
            )

        return ChatResponse(
            project_id=request.project_id,
            question=request.question,
            answer=answer,
            sources=sources,
        )

    def _compact_answer(self, question: str, context: str) -> str:
        context_preview = context[:600].strip()

        return f"the answer to '{question}' is most likely found in: {context_preview}"


class AiChatGenerateService:
    """Laravel-ready AI chat generation over permission-filtered knowledge chunks."""

    def __init__(self, llm_service: LlmService | None = None) -> None:
        self.llm_service = llm_service or LlmService()

    def generate(self, request: AiChatGenerateRequest) -> AiChatGenerateResponse:
        try:
            with get_session() as session:
                repository = LaravelRepository(session)
                project_id = str(request.project_id) if request.project_id is not None else None
                uploads = repository.ai_chat_visible_uploads(
                    user_id=str(request.user_id),
                    company_id=str(request.company_id),
                    project_id=project_id,
                )
                chunks = repository.ai_chat_knowledge_chunks(
                    user_id=str(request.user_id),
                    company_id=str(request.company_id),
                    project_id=project_id,
                )
        except Exception:
            logger.exception("AI chat failed to read visible database context.")
            return self._fallback_response(
                reply=(
                    "\u062a\u0639\u0630\u0631 \u0642\u0631\u0627\u0621\u0629 \u0628\u064a\u0627\u0646\u0627\u062a "
                    "\u0627\u0644\u0634\u0627\u062a \u0645\u0646 \u0642\u0627\u0639\u062f\u0629 "
                    "\u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u062d\u0627\u0644\u064a\u0627. "
                    "\u062a\u062d\u0642\u0642 \u0645\u0646 \u0644\u0648\u062c\u0627\u062a \u062e\u062f\u0645\u0629 "
                    "AI \u0644\u0645\u0639\u0631\u0641\u0629 \u0627\u0644\u0633\u0628\u0628."
                ),
                chat_history=request.chat_history,
            )

        sources_used = self._source_names(uploads, chunks)
        context = self._context(uploads, chunks)
        chat_history = request.chat_history or []
        response_chat_history = request.chat_history or None

        if not context:
            reply = self._empty_context_reply()
        else:
            try:
                reply = self.llm_service.answer_with_history(
                    request.message,
                    context,
                    chat_history,
                )
            except Exception:
                logger.exception("AI chat failed to generate LLM reply.")
                reply = (
                    "\u0642\u0631\u0623\u062a \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u0645\u062a\u0627\u062d\u0629\u060c "
                    "\u0644\u0643\u0646 \u062a\u0639\u0630\u0631 \u062a\u0648\u0644\u064a\u062f \u0631\u062f "
                    "\u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a "
                    "\u062d\u0627\u0644\u064a\u0627. \u062c\u0631\u0628 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649."
                )

        return AiChatGenerateResponse(
            status="success",
            data=AiChatGenerateData(
                reply=reply,
                sources_used=sources_used,
                chat_history=response_chat_history,
            ),
        )

    def _context(self, uploads: list[dict], chunks: list[dict]) -> str:
        parts: list[str] = []
        upload_context = self._upload_context(uploads)
        if upload_context:
            parts.append(upload_context)

        chunk_context = self._chunk_context(chunks)
        if chunk_context:
            parts.append(chunk_context)

        return "\n\n".join(parts)

    def _upload_context(self, uploads: list[dict]) -> str:
        if not uploads:
            return ""

        lines = ["Latest visible uploads, ordered newest first:"]
        for index, upload in enumerate(uploads, start=1):
            file_name = str(upload.get("file_name") or "unknown source")
            uploaded_at = upload.get("upload_date") or upload.get("updated_at") or ""
            project_id = upload.get("project_id") or ""
            access_reason = upload.get("access_reason") or "visible"
            details = [
                f"{index}. File: {file_name}",
                f"Upload ID: {upload.get('id')}",
                f"Uploaded at: {uploaded_at}",
                f"Access: {access_reason}",
                f"Status: {upload.get('status') or ''}",
                f"Type: {upload.get('file_type') or ''}",
                f"Category: {upload.get('category') or ''}",
                f"Scope: {upload.get('scope') or ''}",
                f"Visibility: {upload.get('visibility') or ''}",
            ]
            if project_id:
                details.append(f"Project ID: {project_id}")
            lines.append("\n".join(details))

        return "\n\n".join(lines)

    def _chunk_context(self, chunks: list[dict]) -> str:
        parts: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            content = str(chunk.get("content") or "").strip()
            if not content:
                continue

            file_name = str(chunk.get("file_name") or "unknown source")
            project_id = chunk.get("upload_project_id") or chunk.get("project_id") or ""
            uploaded_at = chunk.get("upload_date") or chunk.get("upload_updated_at") or chunk.get("updated_at") or ""
            metadata = [
                f"Processed source {index}: {file_name}",
                f"Uploaded at: {uploaded_at}",
            ]
            if project_id:
                metadata.append(f"Project ID: {project_id}")

            metadata_text = "\n".join(metadata)
            parts.append(f"{metadata_text}\nContent:\n{content}")

        return "\n\n".join(parts)

    def _empty_context_reply(self) -> str:
        return (
            "\u0644\u0627 \u0623\u0633\u062a\u0637\u064a\u0639 \u0627\u0644\u0639\u062b\u0648\u0631 "
            "\u0639\u0644\u0649 \u0645\u0644\u0641\u0627\u062a \u0645\u0639\u0631\u0641\u0629 "
            "\u0645\u062a\u0627\u062d\u0629 \u0644\u0647\u0630\u0627 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645 "
            "\u062f\u0627\u062e\u0644 \u0627\u0644\u0634\u0631\u0643\u0629 \u062d\u0627\u0644\u064a\u0627. "
            "\u062a\u0623\u0643\u062f \u0645\u0646 \u0648\u062c\u0648\u062f \u0645\u0644\u0641\u0627\u062a "
            "\u0645\u0639\u0627\u0644\u062c\u0629 \u0623\u0648 \u0635\u0644\u0627\u062d\u064a\u0627\u062a "
            "\u0648\u0635\u0648\u0644 \u0645\u0646\u0627\u0633\u0628\u0629."
        )

    def _fallback_response(
        self,
        reply: str,
        chat_history: list | None,
    ) -> AiChatGenerateResponse:
        return AiChatGenerateResponse(
            status="success",
            data=AiChatGenerateData(
                reply=reply,
                sources_used=[],
                chat_history=chat_history or None,
            ),
        )

    def _source_names(self, uploads: list[dict], chunks: list[dict]) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        for item in [*uploads, *chunks]:
            name = str(item.get("file_name") or "").strip()
            if name and name not in seen:
                seen.add(name)
                names.append(name)

        return names
