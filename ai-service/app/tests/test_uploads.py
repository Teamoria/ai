"""Upload processing tests."""

import time

from fastapi.testclient import TestClient

from app.core import database
from app.core.config import settings
from app.main import app


client = TestClient(app)


def auth_headers() -> dict[str, str]:
    return {"X-Internal-API-Key": settings.internal_api_key}


def test_process_upload_returns_laravel_ready_ai_payload(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")

    response = client.post(
        "/api/v1/uploads/process",
        headers=auth_headers(),
        json={
            "upload_id": "upload-1",
            "project_id": "project-1",
            "content": (
                "Today we reviewed the backend integration. "
                "The team decided to connect Laravel uploads to FastAPI. "
                "Ahmad will prepare the frontend demo."
            ),
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["upload_id"] == "upload-1"
    assert payload["project_id"] == "project-1"
    assert payload["source_type"] == "text"
    assert "Key decision: The team decided to connect Laravel uploads to FastAPI." in payload["summary"]
    assert "Next action: Ahmad will prepare the frontend demo." in payload["summary"]
    assert payload["decisions"] == [
        "The team decided to connect Laravel uploads to FastAPI.",
    ]
    assert payload["tasks"] == ["Ahmad will prepare the frontend demo."]
    assert payload["chunks"][0]["content"]
    assert payload["chunks"][0]["embedding"]
    assert payload["chunks"][0]["metadata"]["source"] == "content"
    assert payload["persisted"] is False


def test_process_upload_requires_internal_api_key() -> None:
    response = client.post(
        "/api/v1/uploads/process",
        json={
            "upload_id": "upload-1",
            "project_id": "project-1",
            "content": "Text",
        },
    )

    assert response.status_code == 401


def test_process_media_upload_requires_groq_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")
    media_path = tmp_path / "meeting.mp3"
    media_path.write_bytes(b"not real audio")

    response = client.post(
        "/api/v1/uploads/process",
        headers=auth_headers(),
        json={
            "upload_id": "upload-1",
            "project_id": "project-1",
            "file_path": str(media_path),
        },
    )

    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]


def test_upload_file_creates_record_and_processing_results(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'uploads.db'}")
    monkeypatch.setattr(settings, "upload_temp_dir", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "groq_api_key", "")
    database.engine = None
    database.SessionLocal = None

    response = client.post(
        "/api/v1/uploads",
        headers={
            **auth_headers(),
            "X-User-Id": "user-1",
            "X-User-Role": "admin",
        },
        data={
            "scope": "personal",
            "visibility": "private",
        },
        files=[
            (
                "files",
                (
                    "meeting.txt",
                    b"The team decided to connect uploads. Ahmad will verify the frontend response.",
                    "text/plain",
                ),
            ),
        ],
    )

    assert response.status_code == 200
    upload = response.json()["data"]["uploads"][0]
    assert upload["processing_status"] == "queued"

    detail_response = None
    detail = None
    for _ in range(20):
        detail_response = client.get(
            f"/api/v1/uploads/{upload['id']}",
            headers=auth_headers(),
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()["data"]["upload"]
        if detail["processing_status"] == "processed":
            break
        time.sleep(0.05)

    assert detail_response is not None
    assert detail is not None
    assert detail_response.status_code == 200
    assert detail["processing_status"] == "processed"
    assert detail["summary"]["summary"]
    assert detail["decisions"][0]["decision_text"] == "The team decided to connect uploads."
    assert detail["chunks_count"] >= 1
