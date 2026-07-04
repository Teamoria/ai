"""Chat schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    project_id: str
    question: str = Field(min_length=2, max_length=2000)
    context: list[str] = Field(default_factory=list)


class ChatSource(BaseModel):
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    project_id: str
    question: str
    answer: str
    sources: list[ChatSource] = Field(default_factory=list)
