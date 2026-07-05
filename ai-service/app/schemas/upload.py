"""Upload processing schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ProcessUploadRequest(BaseModel):
    upload_id: str
    project_id: str
    file_path: str | None = None
    file_url: str | None = None
    content: str | None = None


class KnowledgeChunkResponse(BaseModel):
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProcessUploadResponse(BaseModel):
    upload_id: str
    project_id: str
    source_type: str = "text"
    transcript: str
    summary: str
    decisions: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    chunks: list[KnowledgeChunkResponse] = Field(default_factory=list)
    indexed_chunk_count: int = 0
    persisted: bool = False


class UploadActor(BaseModel):
    user_id: str = "system"
    role: str = "admin"
    company_id: str | None = None


class UploadSummary(BaseModel):
    id: str
    user_id: str
    company_id: str | None = None
    project_id: str | None = None
    task_id: str | None = None
    original_name: str
    mime_type: str | None = None
    extension: str | None = None
    size: int
    scope: str
    visibility: str
    processing_status: str
    processing_error: str | None = None
    processed_at: str | None = None
    created_at: str | None = None


class MeetingSummaryPayload(BaseModel):
    id: str
    transcript: str
    summary: str
    source_type: str
    created_at: str | None = None


class ExtractedDecisionPayload(BaseModel):
    id: str
    decision_text: str
    confidence: str | None = None


class ExtractedTaskPayload(BaseModel):
    id: str
    task_text: str
    status: str = "pending"


class KnowledgeChunkPayload(BaseModel):
    id: str
    content: str
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class UploadDetail(UploadSummary):
    summary: MeetingSummaryPayload | None = None
    decisions: list[ExtractedDecisionPayload] = Field(default_factory=list)
    tasks: list[ExtractedTaskPayload] = Field(default_factory=list)
    chunks_count: int = 0
    chunks: list[KnowledgeChunkPayload] = Field(default_factory=list)


class UploadListResponse(BaseModel):
    success: bool = True
    message: str = "Uploads retrieved successfully"
    data: dict[str, Any]


class UploadResponse(BaseModel):
    success: bool = True
    message: str
    data: dict[str, Any]
