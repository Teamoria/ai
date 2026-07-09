"""AI Service application entrypoint."""

from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import validate_internal_api_key
from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.schemas.chat import AiChatGenerateRequest
from app.schemas.chat import AiChatGenerateResponse
from app.schemas.chat import ChatRequest
from app.schemas.chat import ChatResponse
from app.services.chat_service import AiChatGenerateService
from app.services.chat_service import ChatService


app = FastAPI(title="Teamoria AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.resolved_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/ai/conversations/",
    response_model=ChatResponse,
    dependencies=[Depends(validate_internal_api_key)],
    include_in_schema=False,
)
@app.post("/ai/conversations", response_model=ChatResponse, dependencies=[Depends(validate_internal_api_key)])
def create_ai_conversation(request: ChatRequest) -> ChatResponse:
    return ChatService().answer(request)


@app.post(
    "/ai/chat/generate/",
    response_model=AiChatGenerateResponse,
    dependencies=[Depends(validate_internal_api_key)],
    include_in_schema=False,
)
@app.post("/ai/chat/generate", response_model=AiChatGenerateResponse, dependencies=[Depends(validate_internal_api_key)])
def generate_ai_chat_reply(request: AiChatGenerateRequest) -> AiChatGenerateResponse:
    return AiChatGenerateService().generate(request)


app.include_router(v1_router, prefix="/api/v1")
