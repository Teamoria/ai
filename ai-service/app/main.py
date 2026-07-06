"""AI Service application entrypoint."""

from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import validate_internal_api_key
from app.api.v1.router import router as v1_router
from app.schemas.chat import ChatRequest
from app.schemas.chat import ChatResponse
from app.services.chat_service import ChatService


app = FastAPI(title="Teamoria AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ai/conversations", response_model=ChatResponse, dependencies=[Depends(validate_internal_api_key)])
def create_ai_conversation(request: ChatRequest) -> ChatResponse:
    return ChatService().answer(request)


app.include_router(v1_router, prefix="/api/v1")
