"""Upload processing tests."""

from fastapi.testclient import TestClient
import pytest

from app.core.config import settings
from app.main import app
from app.services.meeting_intelligence_service import MeetingIntelligenceService
from app.utils import file_extractors
from app.utils.file_extractors import clean_extracted_text, resolve_upload_source


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
    assert payload["structured_summary"]["overview"]
    assert payload["decisions"] == [
        "The team decided to connect Laravel uploads to FastAPI.",
    ]
    assert payload["decision_items"][0]["title"] == "The team decided to connect Laravel uploads to FastAPI"
    assert payload["tasks"] == ["Ahmad will prepare the frontend demo"]
    assert payload["task_items"][0]["title"] == "Ahmad will prepare the frontend demo"
    assert "chunks" not in payload
    assert payload["persisted"] is False


def test_process_file_upload_accepts_multipart_file(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")

    response = client.post(
        "/api/v1/uploads/process-file",
        headers=auth_headers(),
        data={
            "upload_id": "upload-file-1",
        },
        files={
            "file": (
                "meeting.txt",
                (
                    "The team decided to accept direct multipart uploads. "
                    "Mona will update the Laravel integration."
                ),
                "text/plain",
            ),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["upload_id"] == "upload-file-1"
    assert payload["project_id"] == ""
    assert payload["source_type"] == "text"
    assert payload["document_type"] == "meeting"
    assert payload["decisions"] == ["The team decided to accept direct multipart uploads."]
    assert payload["tasks"] == ["Mona will update the Laravel integration"]
    assert payload["structured_result"]["tasks"]
    assert "chunks" not in payload


def test_extractions_process_file_accepts_laravel_multipart_contract(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")

    response = client.post(
        "/api/v1/extractions/process-file",
        headers=auth_headers(),
        data={
            "upload_id": "upload-file-2",
            "company_id": "company-1",
            "project_id": "project-1",
            "scope": "project",
            "visibility": "members",
        },
        files={
            "file": (
                "meeting.txt",
                "The team decided to process ready files directly. Omar will review the extraction output.",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["upload_id"] == "upload-file-2"
    assert payload["project_id"] == "project-1"
    assert payload["source_type"] == "text"
    assert payload["decisions"] == ["The team decided to process ready files directly."]
    assert payload["tasks"] == ["Omar will review the extraction output"]
    assert payload["persisted"] is False


def test_process_upload_returns_cv_structured_result(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")

    response = client.post(
        "/api/v1/uploads/process",
        headers=auth_headers(),
        json={
            "upload_id": "cv-upload-1",
            "content": (
                "Mohammed Zomlot\n"
                "Software Engineer | Backend Developer\n"
                "mohammed@example.com\n"
                "Education\n"
                "Bachelor's Degree in Software Engineering, Al-Azhar University Gaza\n"
                "Technical Skills\n"
                "PHP Laravel REST API MySQL Database Design Flutter Dart Python Git GitHub Linux Postman\n"
                "Featured Projects\n"
                "Task Manager API built with Laravel and MySQL.\n"
                "Achievements\n"
                "1st Place Gaza programming contest.\n"
                "Languages\n"
                "Arabic Native English Intermediate"
            ),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_type"] == "cv"
    assert payload["structured_result"]["candidate_name"] == "Mohammed Zomlot"
    assert "Laravel" in payload["structured_result"]["skills"]
    assert payload["structured_result"]["contact"]["email"] == "mohammed@example.com"
    assert payload["structured_result"]["score"] >= 70
    assert payload["quality"]["analysis"] in {"medium", "high"}
    assert payload["decisions"] == []
    assert payload["tasks"] == []
    assert payload["decision_items"] == []
    assert payload["task_items"] == []


def test_process_upload_returns_contract_structured_result(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")

    response = client.post(
        "/api/v1/extractions/process",
        headers=auth_headers(),
        json={
            "upload_id": "contract-upload-1",
            "company_id": "company-1",
            "scope": "company",
            "visibility": "members",
            "content": (
                "Service Agreement\n"
                "Party A: Teamoria LLC\n"
                "Party B: Acme Services\n"
                "Effective Date: 2026-08-01\n"
                "End Date: 2027-08-01\n"
                "Payment Terms: Acme Services will be paid 10,000 USD in two installments.\n"
                "The provider shall deliver monthly support reports.\n"
                "Termination: Either party may terminate with 30 days written notice."
            ),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    result = payload["structured_result"]
    assert payload["document_type"] == "contract"
    assert "Teamoria LLC" in result["parties"]
    assert "Acme Services" in result["parties"]
    assert result["start_date"] == "2026-08-01"
    assert result["end_date"] == "2027-08-01"
    assert result["payments"]
    assert result["termination_terms"]
    assert "executive_summary" in result
    assert isinstance(result["legal_risk_score"], int)
    assert result["clause_review"]
    assert payload["decisions"] == []
    assert payload["tasks"] == []
    assert payload["decision_items"] == []
    assert payload["task_items"] == []


def test_cv_job_description_match_returns_score(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")

    response = client.post(
        "/api/v1/extractions/process",
        headers=auth_headers(),
        json={
            "upload_id": "cv-match-1",
            "content": (
                "Sara Ahmad\n"
                "Laravel Backend Developer\n"
                "sara@example.com\n"
                "Technical Skills\n"
                "PHP Laravel REST API MySQL Docker Git GitHub Linux Postman\n"
                "Experience\n"
                "Built REST APIs and database-backed services using Laravel and MySQL."
            ),
            "job_description": "We need a Laravel backend developer with PHP, REST API, MySQL, Docker, and Git experience.",
        },
    )

    assert response.status_code == 200
    result = response.json()["structured_result"]
    assert response.json()["document_type"] == "cv"
    assert result["job_match"]["score"] > 0
    assert "Laravel" in result["job_match"]["matched_skills"]
    assert result["recommendations"]


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


def test_extractions_process_allows_upload_without_project_id(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")

    response = client.post(
        "/api/v1/extractions/process",
        headers=auth_headers(),
        json={
            "upload_id": "upload-without-project",
            "content": "The company decided to review uploaded files.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["upload_id"] == "upload-without-project"
    assert payload["project_id"] == ""
    assert payload["summary"]
    assert payload["persisted"] is False


def test_file_url_download_can_send_laravel_headers(monkeypatch) -> None:
    captured_headers = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return b"Laravel owned file text."

    def fake_urlopen(request, timeout):
        captured_headers.update(dict(request.header_items()))
        return FakeResponse()

    monkeypatch.setattr(file_extractors, "urlopen", fake_urlopen)
    monkeypatch.setattr(settings, "backend_file_api_key", "service-key")
    monkeypatch.setattr(settings, "backend_file_api_key_header", "x-api-key")
    monkeypatch.setattr(settings, "backend_file_bearer_token", "bearer-token")

    source = resolve_upload_source(file_url="https://backend.test/internal/uploads/file.txt")

    assert source.source_type == "text"
    assert source.text == "Laravel owned file text."
    assert captured_headers["X-api-key"] == "service-key"
    assert captured_headers["Authorization"] == "Bearer bearer-token"


def test_file_url_is_used_when_laravel_file_path_is_not_local(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return b"Laravel file from internal URL."

    monkeypatch.setattr(file_extractors, "urlopen", lambda request, timeout: FakeResponse())

    source = resolve_upload_source(
        file_path="uploads/company/project/documents/missing-locally.txt",
        file_url="https://backend.test/internal/uploads/file.txt",
    )

    assert source.source_type == "text"
    assert source.text == "Laravel file from internal URL."


def test_xlsx_upload_source_extracts_sheet_text(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Tasks"
    sheet.append(["Owner", "Task"])
    sheet.append(["Ahmad", "Review upload processing"])
    path = tmp_path / "workbook.xlsx"
    workbook.save(path)

    source = resolve_upload_source(file_path=str(path))

    assert source.source_type == "xlsx"
    assert "Sheet: Tasks" in source.text
    assert "Ahmad | Review upload processing" in source.text


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


def test_ai_service_does_not_own_upload_storage_endpoint() -> None:
    response = client.post(
        "/api/v1/uploads",
        headers=auth_headers(),
        data={"scope": "personal"},
    )

    assert response.status_code == 404


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


def test_meeting_intelligence_ignores_noisy_media_tasks(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")

    transcript = (
        "[00:00:00-00:05:00] I'll give you my hand. But I'll remove the link. "
        "And I'll show you later. For more information click on the bell to post the bell "
        "to see the same. If the bell is not spoken by the bell to watch the bell."
    )

    result = MeetingIntelligenceService().analyze(transcript)

    assert result["tasks"] == []
    assert result["task_items"] == []
    assert result["transcript_quality"]["level"] == "low"


def test_meeting_intelligence_ignores_background_music_noise(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "")

    transcript = (
        "[00:00:00-00:05:00] With respect to the same people, the basic language. "
        "END Ignore subtitles background music text and background music and background music. "
        "English Matisseu will be replaced at the same time at the same time. "
        "For the reason maybe an issue is created by the Ramanic government department."
    )

    result = MeetingIntelligenceService().analyze(transcript)

    assert result["tasks"] == []
    assert result["task_items"] == []
    assert result["transcript_quality"]["level"] == "low"


def test_clean_extracted_text_repairs_arabic_mojibake() -> None:
    mojibake = "بس الدين Thank you".encode("utf-8").decode("latin1")

    assert clean_extracted_text(mojibake) == "بس الدين Thank you"


def test_clean_extracted_text_collapses_spaced_pdf_glyphs() -> None:
    spaced_pdf_text = (
        "B a c h e l o r ' s D e g r e e i n S o f t w a r e\n"
        "E n g i n e e r i n g\n"
        "A l - A z h a r U n i v e r s i t y G a z a\n"
        "2 0 2 1 - P r e s e n t"
    )

    cleaned = clean_extracted_text(spaced_pdf_text)

    assert "Bachelor's Degree" in cleaned
    assert "Software" in cleaned
    assert "Engineering" in cleaned
    assert "Al-Azhar University Gaza" in cleaned
    assert "2021-Present" in cleaned
    assert "B a c h e l o r" not in cleaned


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
