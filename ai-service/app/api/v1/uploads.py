"""Stateless upload extraction endpoints.

Laravel owns upload storage, authorization, status, and database persistence.
This service only extracts/analyzes content and returns a JSON payload.
"""

from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import validate_internal_api_key
from app.schemas.upload import ProcessUploadRequest, ProcessUploadResponse
from app.services.upload_processor import UploadProcessor


router = APIRouter()


@router.post(
    "/uploads/process",
    response_model=ProcessUploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def process_upload(request: ProcessUploadRequest) -> ProcessUploadResponse:
    return UploadProcessor().process(request)


@router.post(
    "/uploads/process-file",
    response_model=ProcessUploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def process_uploaded_file(
    upload_id: str = Form(...),
    file: UploadFile = File(...),
) -> ProcessUploadResponse:
    suffix = Path(file.filename or "").suffix or ".upload"

    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = Path(temp_file.name)

    try:
        request = ProcessUploadRequest(
            upload_id=upload_id,
            file_path=str(temp_path),
        )
        return UploadProcessor().process(request)
    finally:
        temp_path.unlink(missing_ok=True)
        file.file.close()


@router.post(
    "/extractions/process",
    response_model=ProcessUploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def process_extraction(request: ProcessUploadRequest) -> ProcessUploadResponse:
    return process_upload(request)


@router.post("/meetings/upload", dependencies=[Depends(validate_internal_api_key)])
def upload_meeting() -> dict[str, str]:
    return {"status": "deprecated", "replacement": "/api/v1/extractions/process"}
