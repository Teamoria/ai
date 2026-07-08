"""Chat tests."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.schemas.chat import AiChatGenerateData, AiChatGenerateResponse


client = TestClient(app)


def auth_headers() -> dict[str, str]:
    return {"X-Internal-API-Key": settings.internal_api_key}


def test_chat_answers_with_supplied_project_context() -> None:
    response = client.post(
        "/api/v1/chat",
        headers=auth_headers(),
        json={
            "project_id": "project-1",
            "question": "What did the team decide?",
            "context": ["The team decided to connect Laravel uploads to FastAPI."],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["project_id"] == "project-1"
    assert "connect Laravel uploads to FastAPI" in payload["answer"]
    assert payload["sources"][0]["metadata"]["rank"] == 1


def test_chat_is_stateless_without_context() -> None:
    response = client.post(
        "/api/v1/chat",
        headers=auth_headers(),
        json={
            "project_id": "project-1",
            "question": "What is the status?",
        },
    )

    assert response.status_code == 200
    assert "do not have project knowledge context" in response.json()["answer"]


def test_ai_conversations_alias_uses_chat_service() -> None:
    response = client.post(
        "/api/v1/ai/conversations",
        headers=auth_headers(),
        json={
            "project_id": "project-1",
            "message": "What did the team decide?",
            "context": ["The team decided to expose a conversations endpoint."],
        },
    )

    assert response.status_code == 200
    assert "conversations endpoint" in response.json()["answer"]


def test_root_ai_conversations_alias_uses_chat_service() -> None:
    response = client.post(
        "/ai/conversations",
        headers=auth_headers(),
        json={
            "project_id": "project-1",
            "message": "What did the team decide?",
            "context": ["The root conversations endpoint is available."],
        },
    )

    assert response.status_code == 200
    assert "root conversations endpoint" in response.json()["answer"]


def test_ai_chat_generate_returns_laravel_ready_payload(monkeypatch) -> None:
    from app.api.v1 import chat

    captured = {}

    class FakeAiChatGenerateService:
        def generate(self, request):
            captured["request"] = request
            return AiChatGenerateResponse(
                status="success",
                data=AiChatGenerateData(
                    reply="لتقديم طلب إجازة، استخدم نموذج الإجازات.",
                    sources_used=["سياسة_الإجازات.pdf"],
                ),
            )

    monkeypatch.setattr(chat, "AiChatGenerateService", FakeAiChatGenerateService)

    response = client.post(
        "/api/v1/ai/chat/generate",
        headers=auth_headers(),
        json={
            "user_id": 15,
            "company_id": 2,
            "project_id": 9,
            "message": "كيف يمكنني تقديم طلب إجازة؟",
            "chat_history": [
                {"role": "user", "content": "مرحباً"},
                {"role": "assistant", "content": "أهلاً بك، كيف يمكنني مساعدتك؟"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "data": {
            "reply": "لتقديم طلب إجازة، استخدم نموذج الإجازات.",
            "sources_used": ["سياسة_الإجازات.pdf"],
            "chat_history": None,
        },
    }
    assert captured["request"].user_id == 15
    assert captured["request"].company_id == 2
    assert captured["request"].project_id == 9
    assert captured["request"].chat_history[0].role == "user"


def test_ai_chat_generate_accepts_null_chat_history(monkeypatch) -> None:
    from app.api.v1 import chat

    class FakeAiChatGenerateService:
        def generate(self, request):
            return AiChatGenerateResponse(
                status="success",
                data=AiChatGenerateData(
                    reply="No history was provided.",
                    sources_used=[],
                    chat_history=request.chat_history,
                ),
            )

    monkeypatch.setattr(chat, "AiChatGenerateService", FakeAiChatGenerateService)

    response = client.post(
        "/api/v1/ai/chat/generate",
        headers=auth_headers(),
        json={
            "user_id": 15,
            "company_id": 2,
            "message": "Hello",
            "chat_history": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["chat_history"] is None


def test_retrieval_query_returns_vector_sources(monkeypatch) -> None:
    from app.services import retrieval_service

    captured = {}

    class FakePineconeService:
        def search_chunks(
            self,
            *,
            project_id: str,
            company_id: str | None = None,
            scope: str | None = None,
            visibility: str | None = None,
            question: str,
            top_k: int = 5,
        ) -> list[dict]:
            captured.update(
                {
                    "project_id": project_id,
                    "company_id": company_id,
                    "scope": scope,
                    "visibility": visibility,
                    "question": question,
                    "top_k": top_k,
                }
            )
            return [
                {
                    "content": "The meeting assigned Ahmad to prepare the frontend demo.",
                    "score": 0.91,
                    "metadata": {
                        "upload_id": "upload-1",
                        "project_id": project_id,
                        "chunk_index": 0,
                    },
                }
            ]

    class FakeLlmService:
        def answer(self, question: str, context: str) -> str:
            return f"Answer from vector context: {context}"

    monkeypatch.setattr(
        retrieval_service,
        "PineconeService",
        lambda: FakePineconeService(),
    )
    monkeypatch.setattr(
        retrieval_service,
        "LlmService",
        lambda: FakeLlmService(),
    )

    response = client.post(
        "/api/v1/retrieval/query",
        headers=auth_headers(),
        json={
            "project_id": "project-1",
            "company_id": "company-1",
            "scope": "project",
            "visibility": "members",
            "question": "Who owns the frontend demo?",
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "project-1"
    assert "Ahmad" in payload["answer"]
    assert payload["sources"][0]["score"] == 0.91
    assert payload["sources"][0]["metadata"]["upload_id"] == "upload-1"
    assert captured == {
        "project_id": "project-1",
        "company_id": "company-1",
        "scope": "project",
        "visibility": "members",
        "question": "Who owns the frontend demo?",
        "top_k": 3,
    }
