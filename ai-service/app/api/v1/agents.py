"""Agent workflow endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import validate_internal_api_key


router = APIRouter()


@router.post("/agents/{agent_id}/runs", dependencies=[Depends(validate_internal_api_key)])
def run_agent(agent_id: str) -> dict[str, str]:
    return {"agent_id": agent_id, "status": "not_implemented"}


@router.get("/agents/runs/{run_id}/steps", dependencies=[Depends(validate_internal_api_key)])
def get_agent_run_steps(run_id: str) -> dict[str, str]:
    return {"run_id": run_id, "status": "not_implemented"}
