"""API v1 router."""

from fastapi import APIRouter

from app.api.v1 import agents, chat, sources, uploads, workspace_graph


router = APIRouter()
router.include_router(chat.router, tags=["chat"])
router.include_router(uploads.router, tags=["uploads"])
router.include_router(agents.router, tags=["agents"])
router.include_router(sources.router, tags=["sources"])
router.include_router(workspace_graph.router, tags=["workspace-graph"])
