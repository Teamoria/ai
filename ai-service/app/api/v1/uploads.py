"""Upload processing endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import validate_internal_api_key


router = APIRouter()


@router.post("/meetings/upload", dependencies=[Depends(validate_internal_api_key)])
def upload_meeting() -> dict[str, str]:
    return {"status": "not_implemented"}


@router.get("/uploads/{upload_id}/status", dependencies=[Depends(validate_internal_api_key)])
def get_upload_status(upload_id: str) -> dict[str, str]:
    return {"upload_id": upload_id, "status": "not_implemented"}
