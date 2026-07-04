"""Chat and RAG endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import validate_internal_api_key
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService


router = APIRouter()


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(validate_internal_api_key)])
def create_chat_response(request: ChatRequest) -> ChatResponse:
    return ChatService().answer(request)


@router.get("/chat/sessions", dependencies=[Depends(validate_internal_api_key)])
def list_chat_sessions() -> dict[str, str]:
    return {"status": "stateless"}
