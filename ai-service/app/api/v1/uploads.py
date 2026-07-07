"""Stateless upload extraction endpoints.

Laravel owns upload storage, authorization, status, and database persistence.
This service only extracts/analyzes content and returns a JSON payload.
"""

from fastapi import APIRouter, Depends

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
    "/extractions/process",
    response_model=ProcessUploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def process_extraction(request: ProcessUploadRequest) -> ProcessUploadResponse:
    return process_upload(request)


@router.post("/meetings/upload", dependencies=[Depends(validate_internal_api_key)])
def upload_meeting() -> dict[str, str]:
    return {"status": "deprecated", "replacement": "/api/v1/extractions/process"}
