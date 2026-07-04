"""Upload processing endpoints."""

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


@router.post("/meetings/upload", dependencies=[Depends(validate_internal_api_key)])
def upload_meeting() -> dict[str, str]:
    return {"status": "deprecated", "replacement": "/api/v1/uploads/process"}


@router.get("/uploads/{upload_id}/status", dependencies=[Depends(validate_internal_api_key)])
def get_upload_status(upload_id: str) -> dict[str, str]:
    return {"upload_id": upload_id, "status": "stateless"}
