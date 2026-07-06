"""Chat schemas."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ChatUserContext(BaseModel):
    id: str
    company_id: str | None = None
    role: str


class ChatRequest(BaseModel):
    project_id: str | None = None
    question: str | None = Field(default=None, min_length=2, max_length=2000)
    message: str | None = Field(default=None, min_length=2, max_length=2000)
    context: list[str] = Field(default_factory=list)
    user: ChatUserContext | None = None

    @model_validator(mode="after")
    def normalize_question(self) -> "ChatRequest":
        if self.question is None and self.message is not None:
            self.question = self.message

        if self.message is None and self.question is not None:
            self.message = self.question

        if self.question is None:
            raise ValueError("Either question or message is required.")

        return self


class ChatSource(BaseModel):
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    project_id: str | None = None
    question: str
    answer: str
    sources: list[ChatSource] = Field(default_factory=list)
