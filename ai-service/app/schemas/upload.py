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
