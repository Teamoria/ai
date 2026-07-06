"""Meeting intelligence database models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def uuid_string() -> str:
    return str(uuid4())


class MeetingSummary(Base):
    __tablename__ = "meeting_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string, index=True)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), index=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary_overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_priority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary_key_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExtractedDecision(Base):
    __tablename__ = "extracted_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string, index=True)
    meeting_summary_id: Mapped[str] = mapped_column(
        ForeignKey("meeting_summaries.id", ondelete="CASCADE"),
        index=True,
    )
    decision_text: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExtractedTask(Base):
    __tablename__ = "extracted_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string, index=True)
    upload_id: Mapped[str] = mapped_column(String(36), index=True)
    meeting_summary_id: Mapped[str] = mapped_column(String(36), index=True)
    task_text: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
