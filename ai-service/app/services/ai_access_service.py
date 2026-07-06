"""Permission-aware platform data access for the AI agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.laravel_repository import LaravelRepository, LaravelUserContext
from app.schemas.chat import ChatUserContext


@dataclass(frozen=True)
class AiContextBundle:
    project_ids: list[str]
    tasks: list[dict[str, Any]]
    uploads: list[dict[str, Any]]
    meeting_summaries: list[dict[str, Any]]
    knowledge_chunks: list[dict[str, Any]]


class AiAccessService:
    """Builds the exact data window the current Laravel user may see."""

    def __init__(self, session: Session) -> None:
        self.repository = LaravelRepository(session)

    def context_for_user(
        self,
        user_context: ChatUserContext,
        project_id: str | None = None,
    ) -> AiContextBundle:
        user = LaravelUserContext(
            id=user_context.id,
            role=user_context.role,
            company_id=user_context.company_id,
        )
        project_ids = self.repository.visible_project_ids(user, project_id)
        tasks = self.repository.visible_tasks(user, project_ids)
        uploads = self.repository.visible_uploads(user, project_ids)
        upload_ids = [str(upload["id"]) for upload in uploads]
        meeting_summaries = self.repository.visible_meeting_summaries(upload_ids)
        knowledge_chunks = self.repository.visible_knowledge_chunks(project_ids, upload_ids)

        return AiContextBundle(
            project_ids=project_ids,
            tasks=tasks,
            uploads=uploads,
            meeting_summaries=meeting_summaries,
            knowledge_chunks=knowledge_chunks,
        )
