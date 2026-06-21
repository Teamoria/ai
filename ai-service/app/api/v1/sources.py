"""Source detail endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import validate_internal_api_key


router = APIRouter()


@router.get("/chat/sources/{source_id}", dependencies=[Depends(validate_internal_api_key)])
def get_source_details(source_id: str) -> dict[str, str]:
    return {"source_id": source_id, "status": "not_implemented"}
