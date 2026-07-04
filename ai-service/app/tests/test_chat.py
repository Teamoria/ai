"""Chat tests."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


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
