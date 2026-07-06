"""Upload persistence, permissions, and processing result storage."""

from __future__ import annotations

import json
from hashlib import sha256
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
    created: bool = True


def ensure_upload_tables() -> None:
    global _TABLES_READY

    if _TABLES_READY:
        return

    try:
        import app.models  # noqa: F401

        Base.metadata.create_all(bind=get_engine())
        _ensure_upload_processing_columns()
        _ensure_meeting_intelligence_columns()
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
        "processing_stage": "ALTER TABLE uploads ADD COLUMN processing_stage VARCHAR(32) NULL AFTER processing_status",
        "processing_error": "ALTER TABLE uploads ADD COLUMN processing_error VARCHAR(2048) NULL",
        "processed_at": "ALTER TABLE uploads ADD COLUMN processed_at TIMESTAMP NULL",
        "deleted_at": "ALTER TABLE uploads ADD COLUMN deleted_at TIMESTAMP NULL",
        "content_hash": "ALTER TABLE uploads ADD COLUMN content_hash VARCHAR(64) NULL AFTER file_type",
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


def _ensure_meeting_intelligence_columns() -> None:
    if get_engine().dialect.name != "mysql":
        return

    with get_engine().begin() as connection:
        extracted_task_columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'extracted_tasks'"
                ),
            )
        }

        extracted_task_required_columns = {
            "upload_id": "ALTER TABLE extracted_tasks ADD COLUMN upload_id VARCHAR(36) NULL AFTER id",
            "title": "ALTER TABLE extracted_tasks ADD COLUMN title VARCHAR(255) NULL AFTER task_text",
            "description": "ALTER TABLE extracted_tasks ADD COLUMN description TEXT NULL AFTER title",
            "category": "ALTER TABLE extracted_tasks ADD COLUMN category VARCHAR(64) NULL AFTER description",
            "priority": "ALTER TABLE extracted_tasks ADD COLUMN priority VARCHAR(32) NULL AFTER category",
            "assignee": "ALTER TABLE extracted_tasks ADD COLUMN assignee VARCHAR(255) NULL AFTER priority",
            "status": "ALTER TABLE extracted_tasks ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'pending'",
        }

        for column_name, statement in extracted_task_required_columns.items():
            if column_name not in extracted_task_columns:
                connection.execute(text(statement))

        extracted_task_indexes = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'extracted_tasks'"
                ),
            )
        }

        if "ix_extracted_tasks_upload_id" not in extracted_task_indexes:
            connection.execute(text("CREATE INDEX ix_extracted_tasks_upload_id ON extracted_tasks (upload_id)"))

        meeting_summary_columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'meeting_summaries'"
                ),
            )
        }
        meeting_summary_required_columns = {
            "summary_title": "ALTER TABLE meeting_summaries ADD COLUMN summary_title VARCHAR(255) NULL AFTER summary",
            "summary_overview": "ALTER TABLE meeting_summaries ADD COLUMN summary_overview TEXT NULL AFTER summary_title",
            "summary_priority": "ALTER TABLE meeting_summaries ADD COLUMN summary_priority VARCHAR(32) NULL AFTER summary_overview",
            "summary_key_points": "ALTER TABLE meeting_summaries ADD COLUMN summary_key_points TEXT NULL AFTER summary_priority",
        }
        for column_name, statement in meeting_summary_required_columns.items():
            if column_name not in meeting_summary_columns:
                connection.execute(text(statement))

        extracted_decision_columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'extracted_decisions'"
                ),
            )
        }
        extracted_decision_required_columns = {
            "title": "ALTER TABLE extracted_decisions ADD COLUMN title VARCHAR(255) NULL AFTER decision_text",
            "description": "ALTER TABLE extracted_decisions ADD COLUMN description TEXT NULL AFTER title",
            "confidence": "ALTER TABLE extracted_decisions ADD COLUMN confidence VARCHAR(32) NULL AFTER description",
        }
        for column_name, statement in extracted_decision_required_columns.items():
            if column_name not in extracted_decision_columns:
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
        content_hash = sha256(content).hexdigest()
        existing_upload = self._find_existing_upload(
            actor=actor,
            original_name=original_name,
            file_size=len(content),
            content_hash=content_hash,
            scope=scope,
            company_id=effective_company_id,
            project_id=project_id,
            task_id=task_id,
        )
        if existing_upload is not None:
            return StoredUpload(upload=existing_upload, path=Path(existing_upload.file_path), created=False)

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
            content_hash=content_hash,
            category=_category_from_extension(extension, file.content_type),
            file_size=len(content),
            status="success",
            upload_date=datetime.now(timezone.utc),
            processing_status="queued",
            processing_stage="queued",
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

    def _find_existing_upload(
        self,
        *,
        actor: UploadActor,
        original_name: str,
        file_size: int,
        content_hash: str,
        scope: str,
        company_id: str | None,
        project_id: str | None,
        task_id: str | None,
    ) -> Upload | None:
        stmt = (
            select(Upload)
            .where(
                Upload.deleted_at.is_(None),
                Upload.user_id == actor.user_id,
                Upload.file_name == original_name,
                Upload.file_size == file_size,
                Upload.scope == scope,
                Upload.company_id == (company_id or ZERO_UUID),
                Upload.project_id.is_(None) if project_id is None else Upload.project_id == project_id,
                Upload.task_id.is_(None) if task_id is None else Upload.task_id == task_id,
            )
            .order_by(Upload.created_at.desc())
        )
        uploads = self.session.scalars(stmt).all()
        for upload in uploads:
            if upload.processing_status not in {"queued", "processing", "processed", "failed"}:
                continue
            if upload.content_hash == content_hash:
                return upload
            if not upload.content_hash and _stored_file_hash(upload.file_path) == content_hash:
                upload.content_hash = content_hash
                self.session.commit()
                self.session.refresh(upload)
                return upload
        return None

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

        upload.processing_status = _stored_processing_status(status_value)
        upload.processing_stage = status_value
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
        structured_summary: dict | None = None,
        decision_items: list[dict] | None = None,
        task_items: list[dict] | None = None,
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
            summary_title=str((structured_summary or {}).get("title") or "") or None,
            summary_overview=str((structured_summary or {}).get("overview") or "") or None,
            summary_priority=str((structured_summary or {}).get("priority") or "") or None,
            summary_key_points=json.dumps((structured_summary or {}).get("key_points") or []),
        )
        self.session.add(meeting_summary)
        self.session.flush()

        structured_decisions = decision_items or [{"title": item, "description": item} for item in decisions]
        for decision in structured_decisions:
            title = str(decision.get("title") or decision.get("description") or "").strip()
            description = str(decision.get("description") or title).strip()
            if not title and not description:
                continue
            self.session.add(
                ExtractedDecision(
                    id=str(uuid4()),
                    meeting_summary_id=meeting_summary.id,
                    decision_text=description or title,
                    title=title or description,
                    description=description or None,
                    confidence=decision.get("confidence"),
                ),
            )

        structured_tasks = task_items or [{"title": item, "description": item} for item in tasks]
        for task in structured_tasks:
            title = str(task.get("title") or task.get("description") or "").strip()
            description = str(task.get("description") or title).strip()
            if not title and not description:
                continue
            self.session.add(
                ExtractedTask(
                    id=str(uuid4()),
                    upload_id=upload.id,
                    meeting_summary_id=meeting_summary.id,
                    task_text=title or description,
                    title=title or description,
                    description=description or None,
                    category=task.get("category"),
                    priority=task.get("priority"),
                    assignee=task.get("assignee"),
                    status=str(task.get("status") or "pending"),
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
        upload.processing_stage = "processed"
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
                    "transcript_quality": _transcript_quality(meeting_summary.transcript or ""),
                    "summary": meeting_summary.summary or "",
                    "structured_summary": {
                        "title": meeting_summary.summary_title,
                        "overview": meeting_summary.summary_overview or meeting_summary.summary or "",
                        "priority": meeting_summary.summary_priority,
                        "key_points": _loads_json_list(meeting_summary.summary_key_points),
                        "task_count": len(tasks),
                        "decision_count": len(decisions),
                    },
                    "source_type": upload.category,
                    "created_at": _iso(meeting_summary.created_at),
                },
                "decisions": [
                    {
                        "id": decision.id,
                        "decision_text": decision.decision_text,
                        "title": decision.title,
                        "description": decision.description,
                        "confidence": decision.confidence,
                    }
                    for decision in decisions
                ],
                "tasks": [
                    {
                        "id": task.id,
                        "task_text": task.task_text,
                        "title": task.title,
                        "description": task.description,
                        "category": task.category,
                        "priority": task.priority,
                        "assignee": task.assignee,
                        "status": task.status,
                    }
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
        if actor.role == "company_owner" and upload.company_id and upload.company_id == actor.company_id:
            return True
        if upload.user_id == actor.user_id:
            return True
        if upload.visibility == "selected":
            return self._has_permission(upload.id, actor.user_id)
        return False

    def can_manage(self, upload: Upload, actor: UploadActor) -> bool:
        if actor.role == "admin":
            return True
        if actor.role == "company_owner" and upload.company_id and upload.company_id == actor.company_id:
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
    processing_state = _processing_state(
        upload.processing_status,
        upload.processing_error,
        getattr(upload, "processing_stage", None),
    )
    return UploadSummary(
        id=upload.id,
        user_id=upload.user_id,
        company_id=upload.company_id,
        project_id=upload.project_id,
        task_id=upload.task_id,
        original_name=upload.file_name,
        mime_type=upload.file_type,
        content_hash=upload.content_hash,
        extension=Path(upload.file_name).suffix.lower().removeprefix(".") or None,
        size=upload.file_size,
        scope=upload.scope,
        visibility=upload.visibility,
        processing_status=upload.processing_status,
        processing_stage=processing_state["stage"],
        processing_progress=processing_state["progress"],
        processing_message=processing_state["message"],
        processing_error=upload.processing_error,
        processed_at=_iso(upload.processed_at),
        created_at=_iso(upload.created_at),
    )


def upload_processing_state(upload: Upload) -> dict[str, str | int]:
    return _processing_state(upload.processing_status, upload.processing_error, getattr(upload, "processing_stage", None))


def _stored_processing_status(status_value: str) -> str:
    if status_value in {"queued", "processed", "failed", "skipped"}:
        return status_value
    return "processing"


def _processing_state(
    status_value: str | None,
    error: str | None = None,
    stage_value: str | None = None,
) -> dict[str, str | int]:
    effective_status = status_value if status_value in {"processed", "failed", "skipped"} else stage_value or status_value
    states: dict[str, dict[str, str | int]] = {
        "queued": {
            "stage": "queued",
            "progress": 10,
            "message": "File uploaded. Waiting to start AI processing.",
        },
        "processing": {
            "stage": "processing",
            "progress": 20,
            "message": "AI processing has started.",
        },
        "extracting": {
            "stage": "extracting",
            "progress": 30,
            "message": "Extracting readable text from the uploaded file.",
        },
        "transcribing": {
            "stage": "transcribing",
            "progress": 35,
            "message": "Transcribing audio or video into text.",
        },
        "analyzing": {
            "stage": "analyzing",
            "progress": 55,
            "message": "Analyzing the content and preparing the summary.",
        },
        "chunking": {
            "stage": "chunking",
            "progress": 70,
            "message": "Preparing searchable knowledge chunks.",
        },
        "indexing": {
            "stage": "indexing",
            "progress": 85,
            "message": "Indexing knowledge so it can be used by chat.",
        },
        "saving": {
            "stage": "saving",
            "progress": 95,
            "message": "Saving the summary, decisions, and tasks.",
        },
        "processed": {
            "stage": "processed",
            "progress": 100,
            "message": "Processing complete.",
        },
        "failed": {
            "stage": "failed",
            "progress": 100,
            "message": error or "Processing failed.",
        },
        "skipped": {
            "stage": "skipped",
            "progress": 100,
            "message": "Processing skipped.",
        },
    }
    return states.get(
        effective_status or "queued",
        {
            "stage": effective_status or "queued",
            "progress": 20,
            "message": "AI processing is in progress.",
        },
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


def _loads_json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []


def _stored_file_hash(file_path: str | None) -> str | None:
    if not file_path:
        return None
    path = Path(file_path)
    if not path.is_file():
        return None
    return sha256(path.read_bytes()).hexdigest()


def _transcript_quality(transcript: str) -> dict:
    from app.services.meeting_intelligence_service import MeetingIntelligenceService

    return MeetingIntelligenceService().assess_transcript_quality(transcript)


def _iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
