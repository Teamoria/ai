"""Workspace graph endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import validate_internal_api_key


router = APIRouter()


@router.get("/workspace/graph", dependencies=[Depends(validate_internal_api_key)])
def get_workspace_graph() -> dict[str, str]:
    return {"status": "not_implemented"}
