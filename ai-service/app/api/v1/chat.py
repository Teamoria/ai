"""Chat and RAG endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import validate_internal_api_key


router = APIRouter()


@router.post("/chat", dependencies=[Depends(validate_internal_api_key)])
def create_chat_response() -> dict[str, str]:
    return {"status": "not_implemented"}


@router.get("/chat/sessions", dependencies=[Depends(validate_internal_api_key)])
def list_chat_sessions() -> dict[str, str]:
    return {"status": "not_implemented"}
