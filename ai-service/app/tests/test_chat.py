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


def test_root_ai_chat_generate_alias_uses_generate_service(monkeypatch) -> None:
    from app import main

    captured = {}

    class FakeAiChatGenerateService:
        def generate(self, request):
            captured["request"] = request
            return AiChatGenerateResponse(
                status="success",
                data=AiChatGenerateData(reply="Root generate endpoint is available."),
            )

    monkeypatch.setattr(main, "AiChatGenerateService", FakeAiChatGenerateService)

    response = client.post(
        "/ai/chat/generate",
        headers=auth_headers(),
        json={
            "user_id": 15,
            "company_id": 2,
            "message": "Hello",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["reply"] == "Root generate endpoint is available."
    assert captured["request"].user_id == 15


def test_ai_chat_generate_accepts_trailing_slash(monkeypatch) -> None:
    from app.api.v1 import chat

    class FakeAiChatGenerateService:
        def generate(self, request):
            return AiChatGenerateResponse(
                status="success",
                data=AiChatGenerateData(reply="Trailing slash endpoint is available."),
            )

    monkeypatch.setattr(chat, "AiChatGenerateService", FakeAiChatGenerateService)

    response = client.post(
        "/api/v1/ai/chat/generate/",
        headers=auth_headers(),
        json={
            "user_id": 15,
            "company_id": 2,
            "message": "Hello",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["reply"] == "Trailing slash endpoint is available."


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


def test_ai_chat_generate_answers_simple_greeting_without_database(monkeypatch) -> None:
    from app.services import chat_service

    def fail_get_session():
        raise AssertionError("Greeting should not read database context.")

    monkeypatch.setattr(chat_service, "get_session", fail_get_session)

    response = client.post(
        "/api/v1/ai/chat/generate",
        headers=auth_headers(),
        json={
            "user_id": 15,
            "company_id": 2,
            "message": "الووووو",
        },
    )

    assert response.status_code == 200
    assert "Teamoria AI" in response.json()["data"]["reply"]
    assert response.json()["data"]["sources_used"] == []


def test_ai_chat_generate_answers_general_question_without_database(monkeypatch) -> None:
    from app.services import chat_service

    class FakeLlmService:
        def answer_general_with_history(self, question, chat_history):
            return f"general reply: {question}"

    def fail_get_session():
        raise AssertionError("General questions should not read database context.")

    monkeypatch.setattr(chat_service, "LlmService", lambda: FakeLlmService())
    monkeypatch.setattr(chat_service, "get_session", fail_get_session)

    response = client.post(
        "/api/v1/ai/chat/generate",
        headers=auth_headers(),
        json={
            "user_id": 15,
            "company_id": 2,
            "message": "اشرحلي شو يعني agile",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["reply"] == "general reply: اشرحلي شو يعني agile"
    assert response.json()["data"]["sources_used"] == []


def test_ai_chat_generate_routes_task_questions_to_tasks(monkeypatch) -> None:
    from app.services import chat_service

    class FakeSession:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeRepository:
        def __init__(self, session):
            pass

        def ai_chat_identity_exists(self, **kwargs):
            return {
                "user_exists": True,
                "company_exists": True,
                "user_in_company": True,
            }

        def ai_chat_visible_tasks(self, **kwargs):
            return [
                {
                    "id": "task-1",
                    "project_id": "project-1",
                    "title": "Prepare frontend demo",
                    "description": "Build the demo screen.",
                    "status": "open",
                    "priority": "high",
                    "due_date": None,
                    "project_name": "Launch",
                    "access_reason": "assigned",
                }
            ]

    class FakeLlmService:
        def answer_with_history(self, question, context, chat_history):
            assert "Prepare frontend demo" in context
            return "You have one open task."

    monkeypatch.setattr(chat_service, "get_session", lambda: FakeSession())
    monkeypatch.setattr(chat_service, "LaravelRepository", FakeRepository)

    service = chat_service.AiChatGenerateService(llm_service=FakeLlmService())
    response = service.generate(
        chat_service.AiChatGenerateRequest(
            user_id=15,
            company_id=2,
            message="شو المهام عندي؟",
        )
    )

    assert response.data.reply == "You have one open task."
    assert response.data.sources_used == ["Prepare frontend demo"]


def test_ai_chat_generate_reports_invalid_identity(monkeypatch) -> None:
    from app.services import chat_service

    class FakeSession:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeRepository:
        def __init__(self, session):
            pass

        def ai_chat_identity_exists(self, **kwargs):
            return {
                "user_exists": False,
                "company_exists": False,
                "user_in_company": False,
            }

        def ai_chat_visible_tasks(self, **kwargs):
            return []

    monkeypatch.setattr(chat_service, "get_session", lambda: FakeSession())
    monkeypatch.setattr(chat_service, "LaravelRepository", FakeRepository)

    response = chat_service.AiChatGenerateService().generate(
        chat_service.AiChatGenerateRequest(
            user_id=15,
            company_id=2,
            message="شو المهام عندي؟",
        )
    )

    assert "user_id=15" in response.data.reply
    assert "company_id=2" in response.data.reply


def test_ai_chat_generate_routes_project_questions_to_projects(monkeypatch) -> None:
    from app.services import chat_service

    class FakeSession:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeRepository:
        def __init__(self, session):
            pass

        def ai_chat_identity_exists(self, **kwargs):
            return {
                "user_exists": True,
                "company_exists": True,
                "user_in_company": True,
            }

        def ai_chat_visible_projects(self, **kwargs):
            return [
                {
                    "id": "project-1",
                    "name": "Active Product Launch",
                    "status": "active",
                    "progress": 35,
                    "description": "Launch project",
                    "access_reason": "member",
                },
                {
                    "id": "project-2",
                    "name": "Completed Brand Refresh",
                    "status": "completed",
                    "progress": 100,
                    "description": "",
                    "access_reason": "company",
                },
            ]

    class FakeLlmService:
        def answer_with_history(self, question, context, chat_history):
            assert "Visible projects count: 2" in context
            return "عندك مشروعين."

    monkeypatch.setattr(chat_service, "get_session", lambda: FakeSession())
    monkeypatch.setattr(chat_service, "LaravelRepository", FakeRepository)

    service = chat_service.AiChatGenerateService(llm_service=FakeLlmService())
    response = service.generate(
        chat_service.AiChatGenerateRequest(
            user_id=15,
            company_id=2,
            message="حاليا اكم مشروع عندي",
        )
    )

    assert response.data.reply == "عندك مشروعين."
    assert response.data.sources_used == ["Active Product Launch", "Completed Brand Refresh"]


def test_ai_chat_generate_falls_back_to_task_list_when_llm_fails() -> None:
    from app.services.chat_service import AiChatGenerateService

    class BrokenLlmService:
        def answer_with_history(self, question, context, chat_history):
            raise RuntimeError("LLM unavailable")

    service = AiChatGenerateService(llm_service=BrokenLlmService())
    reply = service._context_fallback_reply(  # type: ignore[attr-defined]
        "tasks",
        [
            {
                "title": "Prepare frontend demo",
                "status": "todo",
                "priority": "high",
                "project_name": "Launch",
            }
        ],
        [],
        [],
        [],
    )

    assert "وجدت 1 مهام متاحة" in reply
    assert "Prepare frontend demo" in reply


def test_ai_chat_context_includes_latest_upload_metadata() -> None:
    from app.services.chat_service import AiChatGenerateService

    service = AiChatGenerateService()
    context = service._context(  # type: ignore[attr-defined]
        uploads=[
            {
                "id": "upload-1",
                "file_name": "latest-plan.pdf",
                "upload_date": "2026-07-09 10:00:00",
                "project_id": "project-1",
                "access_reason": "shared",
                "status": "processed",
                "file_type": "pdf",
                "category": "plan",
                "scope": "project",
                "visibility": "members",
            }
        ],
        chunks=[],
    )

    assert "Latest visible uploads, ordered newest first" in context
    assert "latest-plan.pdf" in context
    assert "Access: shared" in context
    assert "Project ID: project-1" in context


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
