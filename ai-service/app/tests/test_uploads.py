"""Upload processing tests."""

import time

from fastapi.testclient import TestClient

from app.core import database
from app.core.config import settings
from app.main import app
from app.services.meeting_intelligence_service import MeetingIntelligenceService
from app.services import upload_management_service
from app.utils.file_extractors import clean_extracted_text


client = TestClient(app)


def auth_headers() -> dict[str, str]:
    return {"X-Internal-API-Key": settings.internal_api_key}


def user_headers(user_id: str = "user-1", role: str = "member", company_id: str | None = None) -> dict[str, str]:
    headers = {
        **auth_headers(),
        "X-User-Id": user_id,
        "X-User-Role": role,
    }
    if company_id:
        headers["X-Company-Id"] = company_id
    return headers


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
    assert payload["structured_summary"]["overview"]
    assert payload["decisions"] == [
        "The team decided to connect Laravel uploads to FastAPI.",
    ]
    assert payload["decision_items"][0]["title"] == "The team decided to connect Laravel uploads to FastAPI"
    assert payload["tasks"] == ["Ahmad will prepare the frontend demo"]
    assert payload["task_items"][0]["title"] == "Ahmad will prepare the frontend demo"
    assert "chunks" not in payload
    assert payload["persisted"] is False


def test_extractions_process_alias_returns_laravel_ready_ai_payload(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")

    response = client.post(
        "/api/v1/extractions/process",
        headers=auth_headers(),
        json={
            "upload_id": "upload-1",
            "project_id": "project-1",
            "content": "The team decided to use one stable extraction endpoint.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["upload_id"] == "upload-1"
    assert payload["project_id"] == "project-1"
    assert payload["source_type"] == "text"
    assert payload["summary"]
    assert "chunks" not in payload
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


def test_process_upload_ignores_unavailable_pinecone(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(settings, "pinecone_api_key", "pinecone-key")
    monkeypatch.setattr(settings, "pinecone_index_name", "missing-index")
    monkeypatch.setattr(settings, "pinecone_index", "")
    monkeypatch.setattr(settings, "pinecone_host", "")

    response = client.post(
        "/api/v1/uploads/process",
        headers=auth_headers(),
        json={
            "upload_id": "upload-1",
            "project_id": "project-1",
            "content": "The team decided to connect uploads.",
        },
    )

    assert response.status_code == 200
    assert response.json()["indexed_chunk_count"] == 0


def test_meeting_intelligence_extracts_arabic_tasks_section(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")

    transcript = """
    المهام (Tasks)
    مهام الواجهة الخلفية (Backend)
    ● إنشاء واجهة برمجية لرفع ملفات الاجتماعات.
    ● تطوير خدمة تخزين الملفات.
    مهام الواجهة الأمامية (Frontend)
    ● عرض قائمة المهام القابلة للتعديل.
    """

    result = MeetingIntelligenceService().analyze(transcript)

    assert result["tasks"] == [
        "إنشاء واجهة برمجية لرفع ملفات الاجتماعات",
        "تطوير خدمة تخزين الملفات",
        "عرض قائمة المهام القابلة للتعديل",
    ]
    assert result["task_items"][0]["category"] == "Backend"
    assert result["task_items"][2]["category"] == "Frontend"


def test_clean_extracted_text_repairs_arabic_mojibake() -> None:
    mojibake = "بس الدين Thank you".encode("utf-8").decode("latin1")

    assert clean_extracted_text(mojibake) == "بس الدين Thank you"


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
        headers=user_headers("user-1"),
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
    assert upload["processing_stage"] == "queued"
    assert upload["processing_progress"] == 10
    assert "File uploaded" in upload["processing_message"]

    detail_response = None
    detail = None
    status_payload = None
    for _ in range(20):
        detail_response = client.get(
            f"/api/v1/uploads/{upload['id']}",
            headers=user_headers("user-1"),
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()["data"]["upload"]
        status_response = client.get(
            f"/api/v1/uploads/{upload['id']}/status",
            headers=user_headers("user-1"),
        )
        assert status_response.status_code == 200
        status_payload = status_response.json()
        if detail["processing_status"] == "processed":
            break
        time.sleep(0.05)

    assert detail_response is not None
    assert detail is not None
    assert detail_response.status_code == 200
    assert detail["processing_status"] == "processed"
    assert detail["processing_stage"] == "processed"
    assert detail["processing_progress"] == 100
    assert status_payload is not None
    assert status_payload["stage"] == "processed"
    assert status_payload["progress"] == 100
    assert detail["summary"]["summary"]
    assert detail["decisions"][0]["decision_text"] == "The team decided to connect uploads."
    assert detail["chunks_count"] >= 1

    duplicate_response = client.post(
        "/api/v1/uploads",
        headers=user_headers("user-1"),
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

    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["message"] == "Existing processed file returned"
    duplicate_upload = duplicate_response.json()["data"]["uploads"][0]
    assert duplicate_upload["id"] == upload["id"]
    assert duplicate_upload["processing_status"] == "processed"
    assert duplicate_upload["already_exists"] is True
    assert duplicate_upload["has_ai_analysis"] is True
    assert "already exists" in duplicate_upload["message"]

    forbidden_response = client.get(
        f"/api/v1/uploads/{upload['id']}",
        headers=user_headers("user-2"),
    )
    assert forbidden_response.status_code == 403

    missing_actor_response = client.get(
        f"/api/v1/uploads/{upload['id']}",
        headers=auth_headers(),
    )
    assert missing_actor_response.status_code == 422


def test_company_member_does_not_see_all_company_uploads(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'company_uploads.db'}")
    monkeypatch.setattr(settings, "upload_temp_dir", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "groq_api_key", "")
    database.engine = None
    database.SessionLocal = None
    upload_management_service._TABLES_READY = False

    response = client.post(
        "/api/v1/uploads",
        headers=user_headers("user-2", "member", "company-1"),
        data={
            "scope": "company",
            "visibility": "members",
        },
        files=[
            (
                "files",
                (
                    "company-plan.txt",
                    b"Company-only planning notes.",
                    "text/plain",
                ),
            ),
        ],
    )
    assert response.status_code == 200
    upload = response.json()["data"]["uploads"][0]

    member_response = client.get(
        "/api/v1/uploads?scope=company",
        headers=user_headers("user-1", "member", "company-1"),
    )
    assert member_response.status_code == 200
    member_upload_ids = [item["id"] for item in member_response.json()["data"]["uploads"]]
    assert upload["id"] not in member_upload_ids

    owner_response = client.get(
        "/api/v1/uploads?scope=company",
        headers=user_headers("owner-1", "company_owner", "company-1"),
    )
    assert owner_response.status_code == 200
    owner_upload_ids = [item["id"] for item in owner_response.json()["data"]["uploads"]]
    assert upload["id"] in owner_upload_ids
