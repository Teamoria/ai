"""Upload records and permissions."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def uuid_string() -> str:
    return str(uuid4())


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string, index=True)
    company_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    scope: Mapped[str] = mapped_column(String(32))
    visibility: Mapped[str] = mapped_column(String(32))
    file_path: Mapped[str] = mapped_column(String(255))
    file_name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(255))
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    category: Mapped[str] = mapped_column(String(32))
    file_size: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), default="success")
    upload_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    processing_status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    processing_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UploadPermission(Base):
    __tablename__ = "upload_permissions"
    __table_args__ = (UniqueConstraint("upload_id", "user_id", name="uq_upload_permission_user"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    granted_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    access_level: Mapped[str] = mapped_column(String(32), default="view")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
