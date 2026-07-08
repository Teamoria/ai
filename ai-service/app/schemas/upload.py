"""Upload processing schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ProcessUploadRequest(BaseModel):
    upload_id: str
    company_id: str | None = None
    project_id: str | None = None
    task_id: str | None = None
    scope: str | None = None
    visibility: str | None = None
    file_path: str | None = None
    file_url: str | None = None
    file_url_headers: dict[str, str] | None = None
    file_url_api_key: str | None = None
    file_url_bearer_token: str | None = None
    content: str | None = None
    job_description: str | None = None
    transcription_language: str | None = None


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
    document_type: str = "document"
    transcript: str
    transcript_quality: TranscriptQualityPayload | None = None
    summary: str
    structured_summary: StructuredSummaryPayload | None = None
    structured_result: dict[str, Any] = Field(default_factory=dict)
    decisions: list[str] = Field(default_factory=list)
    decision_items: list[StructuredDecisionPayload] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    task_items: list[StructuredTaskPayload] = Field(default_factory=list)
    quality: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    chunks: list[KnowledgeChunkResponse] = Field(default_factory=list, exclude=True)
    indexed_chunk_count: int = 0
    persisted: bool = False
