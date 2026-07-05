"""Upload persistence, permissions, and processing result storage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, get_engine, get_session
from app.models import ExtractedDecision, ExtractedTask, KnowledgeChunk, MeetingSummary, Upload, UploadPermission
from app.schemas.upload import UploadActor, UploadDetail, UploadSummary


VALID_SCOPES = {"company", "project", "task", "personal"}
VALID_VISIBILITIES = {"private", "members", "selected"}
VALID_ACCESS_LEVELS = {"view", "manage"}
ZERO_UUID = "00000000-0000-0000-0000-000000000000"
_TABLES_READY = False


@dataclass(frozen=True)
class StoredUpload:
    upload: Upload
    path: Path


def ensure_upload_tables() -> None:
    global _TABLES_READY

    if _TABLES_READY:
        return

    try:
        import app.models  # noqa: F401

        Base.metadata.create_all(bind=get_engine())
        _ensure_upload_processing_columns()
        _TABLES_READY = True
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Upload database is not available: {exc}",
        ) from exc


def _ensure_upload_processing_columns() -> None:
    if get_engine().dialect.name != "mysql":
        return

    required_columns = {
        "processing_status": "ALTER TABLE uploads ADD COLUMN processing_status VARCHAR(32) NOT NULL DEFAULT 'queued'",
        "processing_error": "ALTER TABLE uploads ADD COLUMN processing_error VARCHAR(2048) NULL",
        "processed_at": "ALTER TABLE uploads ADD COLUMN processed_at TIMESTAMP NULL",
        "deleted_at": "ALTER TABLE uploads ADD COLUMN deleted_at TIMESTAMP NULL",
    }

    with get_engine().begin() as connection:
        existing = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'uploads'"
                ),
            )
        }

        for column_name, statement in required_columns.items():
            if column_name not in existing:
                connection.execute(text(statement))


def get_upload_session() -> Session:
    ensure_upload_tables()
    return get_session()


class UploadManagementService:
    def __init__(self, session: Session | None = None) -> None:
        self.session = session or get_upload_session()

    def create_upload(
        self,
        *,
        file: UploadFile,
        content: bytes,
        actor: UploadActor,
        scope: str,
        visibility: str,
        company_id: str | None,
        project_id: str | None,
        task_id: str | None,
        shared_with_user_ids: Iterable[str],
        access_level: str,
    ) -> StoredUpload:
        effective_company_id = company_id or actor.company_id
        self._validate_scope(scope=scope, company_id=effective_company_id, project_id=project_id, task_id=task_id)
        self._validate_visibility(visibility, shared_with_user_ids)

        if access_level not in VALID_ACCESS_LEVELS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid access_level.")

        original_name = Path(file.filename or "upload").name
        extension = Path(original_name).suffix.lower().removeprefix(".") or None
        stored_name = f"{uuid4().hex}{'.' + extension if extension else ''}"
        storage_dir = Path(settings.upload_temp_dir).resolve()
        storage_dir.mkdir(parents=True, exist_ok=True)
        stored_path = storage_dir / stored_name
        stored_path.write_bytes(content)

        upload = Upload(
            id=str(uuid4()),
            company_id=effective_company_id or ZERO_UUID,
            project_id=project_id,
            task_id=task_id,
            user_id=actor.user_id,
            scope=scope,
            visibility=visibility,
            file_path=str(stored_path),
            file_name=original_name,
            file_type=file.content_type or extension or "application/octet-stream",
            category=_category_from_extension(extension, file.content_type),
            file_size=len(content),
            status="success",
            upload_date=datetime.now(timezone.utc),
            processing_status="queued",
        )
        self.session.add(upload)
        self.session.flush()

        for user_id in sorted({item for item in shared_with_user_ids if item}):
            self.session.add(
                UploadPermission(
                    upload_id=upload.id,
                    user_id=user_id,
                    granted_by=actor.user_id,
                    access_level=access_level,
                ),
            )

        self.session.commit()
        self.session.refresh(upload)
        return StoredUpload(upload=upload, path=stored_path)

    def list_uploads(
        self,
        *,
        actor: UploadActor,
        scope: str | None = None,
        visibility: str | None = None,
        project_id: str | None = None,
        task_id: str | None = None,
        per_page: int = 50,
        mine_only: bool = False,
    ) -> list[Upload]:
        stmt = select(Upload).where(Upload.deleted_at.is_(None))

        if scope:
            stmt = stmt.where(Upload.scope == scope)
        if visibility:
            stmt = stmt.where(Upload.visibility == visibility)
        if project_id:
            stmt = stmt.where(Upload.project_id == project_id)
        if task_id:
            stmt = stmt.where(Upload.task_id == task_id)
        if mine_only:
            stmt = stmt.where(Upload.user_id == actor.user_id)

        uploads = self.session.scalars(stmt.order_by(Upload.created_at.desc()).limit(min(per_page, 100))).all()
        return [upload for upload in uploads if self.can_view(upload, actor)]

    def get_upload(self, upload_id: str, *, actor: UploadActor, require_manage: bool = False) -> Upload:
        upload = self.session.get(Upload, upload_id)

        if upload is None or upload.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")

        if require_manage and not self.can_manage(upload, actor):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot manage this upload.")

        if not require_manage and not self.can_view(upload, actor):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this upload.")

        return upload

    def soft_delete_upload(self, upload_id: str, *, actor: UploadActor) -> Upload:
        upload = self.get_upload(upload_id, actor=actor, require_manage=True)
        upload.deleted_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(upload)
        return upload

    def add_permission(
        self,
        upload_id: str,
        *,
        actor: UploadActor,
        user_id: str,
        access_level: str,
    ) -> UploadPermission:
        self.get_upload(upload_id, actor=actor, require_manage=True)

        if access_level not in VALID_ACCESS_LEVELS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid access_level.")

        permission = self.session.scalar(
            select(UploadPermission).where(
                UploadPermission.upload_id == upload_id,
                UploadPermission.user_id == user_id,
            ),
        )
        if permission is None:
            permission = UploadPermission(
                upload_id=upload_id,
                user_id=user_id,
                granted_by=actor.user_id,
                access_level=access_level,
            )
            self.session.add(permission)
        else:
            permission.access_level = access_level

        self.session.commit()
        self.session.refresh(permission)
        return permission

    def remove_permission(self, upload_id: str, *, actor: UploadActor, user_id: str) -> None:
        self.get_upload(upload_id, actor=actor, require_manage=True)
        permission = self.session.scalar(
            select(UploadPermission).where(
                UploadPermission.upload_id == upload_id,
                UploadPermission.user_id == user_id,
            ),
        )
        if permission is not None:
            self.session.delete(permission)
            self.session.commit()

    def set_status(self, upload_id: str, status_value: str, error: str | None = None) -> None:
        upload = self.session.get(Upload, upload_id)
        if upload is None:
            return

        upload.processing_status = status_value
        upload.processing_error = error
        if status_value in {"processed", "failed", "skipped"}:
            upload.processed_at = datetime.now(timezone.utc)
        self.session.commit()

    def save_processing_result(
        self,
        *,
        upload: Upload,
        source_type: str,
        transcript: str,
        summary: str,
        decisions: list[str],
        tasks: list[str],
        chunks: list[dict],
    ) -> None:
        old_summaries = self.session.scalars(
            select(MeetingSummary).where(MeetingSummary.upload_id == upload.id),
        ).all()
        old_summary_ids = [item.id for item in old_summaries]

        self.session.query(KnowledgeChunk).filter(KnowledgeChunk.upload_id == upload.id).delete()
        if old_summary_ids:
            self.session.query(ExtractedDecision).filter(
                ExtractedDecision.meeting_summary_id.in_(old_summary_ids),
            ).delete(synchronize_session=False)
            self.session.query(ExtractedTask).filter(
                ExtractedTask.meeting_summary_id.in_(old_summary_ids),
            ).delete(synchronize_session=False)
        self.session.query(MeetingSummary).filter(MeetingSummary.upload_id == upload.id).delete()

        meeting_summary = MeetingSummary(
            id=str(uuid4()),
            upload_id=upload.id,
            transcript=transcript,
            summary=summary,
        )
        self.session.add(meeting_summary)
        self.session.flush()

        for decision in decisions:
            self.session.add(
                ExtractedDecision(
                    id=str(uuid4()),
                    meeting_summary_id=meeting_summary.id,
                    decision_text=decision,
                ),
            )

        for task in tasks:
            self.session.add(
                ExtractedTask(
                    id=str(uuid4()),
                    upload_id=upload.id,
                    meeting_summary_id=meeting_summary.id,
                    task_text=task,
                    status="pending",
                ),
            )

        for index, chunk in enumerate(chunks):
            metadata = dict(chunk.get("metadata") or {})
            self.session.add(
                KnowledgeChunk(
                    id=str(uuid4()),
                    upload_id=upload.id,
                    project_id=upload.project_id,
                    content=str(chunk.get("content") or ""),
                    chunk_metadata=json.dumps(metadata),
                    embedding=json.dumps(chunk.get("embedding")),
                ),
            )

        upload.processing_status = "processed"
        upload.processing_error = None
        upload.processed_at = datetime.now(timezone.utc)
        self.session.commit()

    def get_detail(self, upload: Upload) -> UploadDetail:
        payload = upload_to_summary(upload).model_dump()
        meeting_summary = self.session.scalar(
            select(MeetingSummary).where(MeetingSummary.upload_id == upload.id).order_by(MeetingSummary.created_at.desc()),
        )
        decisions = []
        tasks = []
        if meeting_summary is not None:
            decisions = self.session.scalars(
                select(ExtractedDecision)
                .where(ExtractedDecision.meeting_summary_id == meeting_summary.id)
                .order_by(ExtractedDecision.created_at),
            ).all()
            tasks = self.session.scalars(
                select(ExtractedTask)
                .where(ExtractedTask.meeting_summary_id == meeting_summary.id)
                .order_by(ExtractedTask.created_at),
            ).all()
        chunks_count = self.session.scalar(
            select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.upload_id == upload.id),
        )
        chunks = self.session.scalars(
            select(KnowledgeChunk).where(KnowledgeChunk.upload_id == upload.id).order_by(KnowledgeChunk.created_at).limit(20),
        ).all()

        payload.update(
            {
                "summary": None
                if meeting_summary is None
                else {
                    "id": meeting_summary.id,
                    "transcript": meeting_summary.transcript or "",
                    "summary": meeting_summary.summary or "",
                    "source_type": upload.category,
                    "created_at": _iso(meeting_summary.created_at),
                },
                "decisions": [
                    {"id": decision.id, "decision_text": decision.decision_text, "confidence": None}
                    for decision in decisions
                ],
                "tasks": [
                    {"id": task.id, "task_text": task.task_text, "status": task.status}
                    for task in tasks
                ],
                "chunks_count": int(chunks_count or 0),
                "chunks": [
                    {
                        "id": chunk.id,
                        "content": chunk.content,
                        "chunk_index": int(_loads_json_dict(chunk.chunk_metadata).get("chunk_index", 0)),
                        "metadata": _loads_json_dict(chunk.chunk_metadata),
                    }
                    for chunk in chunks
                ],
            },
        )
        return UploadDetail(**payload)

    def can_view(self, upload: Upload, actor: UploadActor) -> bool:
        if actor.role == "admin":
            return True
        if upload.user_id == actor.user_id:
            return True
        if upload.visibility == "members" and upload.company_id and upload.company_id == actor.company_id:
            return True
        if upload.visibility == "selected":
            return self._has_permission(upload.id, actor.user_id)
        return False

    def can_manage(self, upload: Upload, actor: UploadActor) -> bool:
        if actor.role == "admin":
            return True
        if upload.user_id == actor.user_id:
            return True
        return self._has_permission(upload.id, actor.user_id, access_level="manage")

    def _has_permission(self, upload_id: str, user_id: str, access_level: str | None = None) -> bool:
        stmt = select(UploadPermission).where(
            UploadPermission.upload_id == upload_id,
            UploadPermission.user_id == user_id,
        )
        if access_level:
            stmt = stmt.where(UploadPermission.access_level == access_level)
        return self.session.scalar(stmt) is not None

    def _validate_scope(
        self,
        *,
        scope: str,
        company_id: str | None,
        project_id: str | None,
        task_id: str | None,
    ) -> None:
        if scope not in VALID_SCOPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid scope.")
        if scope == "company" and not company_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="company_id is required.")
        if scope == "project" and not project_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="project_id is required.")
        if scope == "task" and not task_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="task_id is required.")

    def _validate_visibility(self, visibility: str, shared_with_user_ids: Iterable[str]) -> None:
        if visibility not in VALID_VISIBILITIES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid visibility.")
        if visibility == "selected" and not list(shared_with_user_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="shared_with_user_ids is required when visibility is selected.",
            )


def upload_to_summary(upload: Upload) -> UploadSummary:
    return UploadSummary(
        id=upload.id,
        user_id=upload.user_id,
        company_id=upload.company_id,
        project_id=upload.project_id,
        task_id=upload.task_id,
        original_name=upload.file_name,
        mime_type=upload.file_type,
        extension=Path(upload.file_name).suffix.lower().removeprefix(".") or None,
        size=upload.file_size,
        scope=upload.scope,
        visibility=upload.visibility,
        processing_status=upload.processing_status,
        processing_error=upload.processing_error,
        processed_at=_iso(upload.processed_at),
        created_at=_iso(upload.created_at),
    )


def _category_from_extension(extension: str | None, mime_type: str | None) -> str:
    value = f"{extension or ''} {mime_type or ''}".lower()

    if any(item in value for item in ["mp4", "mov", "avi", "mkv", "video"]):
        return "video"
    if any(item in value for item in ["mp3", "wav", "m4a", "webm", "audio"]):
        return "audio"
    if any(item in value for item in ["png", "jpg", "jpeg", "gif", "image"]):
        return "image"
    return "document"


def _loads_json_dict(value: str | None) -> dict:
    if not value:
        return {}
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
