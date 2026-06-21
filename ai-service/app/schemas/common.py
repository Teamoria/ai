"""Shared request and response schemas."""

from pydantic import BaseModel


class UserContext(BaseModel):
    id: str
    role: str
    language: str = "en"


class AccessScope(BaseModel):
    company_id: str
    project_ids: list[str] = []
    visible_meeting_ids: list[str] = []
