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


class StructuredSummaryPayload(BaseModel):
    title: str | None = None
    overview: str
    priority: str | None = None
    key_points: list[str] = Field(default_factory=list)
    task_count: int = 0
    decision_count: int = 0


class StructuredDecisionPayload(BaseModel):
    title: str
    description: str | None = None
    confidence: str | None = None


class StructuredTaskPayload(BaseModel):
    title: str
    description: str | None = None
    category: str | None = None
    priority: str | None = None
    assignee: str | None = None
    status: str = "pending"


class TranscriptQualityPayload(BaseModel):
    level: str
    score: int
    word_count: int
    unique_word_ratio: float
    warning: str | None = None
    suggestions: list[str] = Field(default_factory=list)


class ProcessUploadResponse(BaseModel):
    upload_id: str
    project_id: str
    source_type: str = "text"
    transcript: str
    transcript_quality: TranscriptQualityPayload | None = None
    summary: str
    structured_summary: StructuredSummaryPayload | None = None
    decisions: list[str] = Field(default_factory=list)
    decision_items: list[StructuredDecisionPayload] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    task_items: list[StructuredTaskPayload] = Field(default_factory=list)
    chunks: list[KnowledgeChunkResponse] = Field(default_factory=list)
    indexed_chunk_count: int = 0
    persisted: bool = False


class UploadActor(BaseModel):
    user_id: str = "system"
    role: str = "member"
    company_id: str | None = None


class UploadSummary(BaseModel):
    id: str
    user_id: str
    company_id: str | None = None
    project_id: str | None = None
    task_id: str | None = None
    original_name: str
    mime_type: str | None = None
    content_hash: str | None = None
    extension: str | None = None
    size: int
    scope: str
    visibility: str
    processing_status: str
    processing_stage: str
    processing_progress: int
    processing_message: str
    processing_error: str | None = None
    processed_at: str | None = None
    created_at: str | None = None


class MeetingSummaryPayload(BaseModel):
    id: str
    transcript: str
    transcript_quality: TranscriptQualityPayload | None = None
    summary: str
    structured_summary: StructuredSummaryPayload | None = None
    source_type: str
    created_at: str | None = None


class ExtractedDecisionPayload(BaseModel):
    id: str
    decision_text: str
    title: str | None = None
    description: str | None = None
    confidence: str | None = None


class ExtractedTaskPayload(BaseModel):
    id: str
    task_text: str
    title: str | None = None
    description: str | None = None
    category: str | None = None
    priority: str | None = None
    assignee: str | None = None
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
