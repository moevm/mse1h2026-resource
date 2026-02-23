from __future__ import annotations

from fastapi import APIRouter

from app.models.topology import GraphResponse
from app.models.traversal import TraversalRule
from app.services import traversal_service

router = APIRouter()


@router.get(
    "/presets",
    summary="List preset traversal rules",
    description=(
        "Returns all built-in traversal rules. "
        "Use these as templates or execute them directly via POST /execute."
    ),
)
async def list_presets() -> list[dict]:
    return traversal_service.list_presets()


@router.post(
    "/execute",
    response_model=GraphResponse,
    summary="Execute a traversal rule",
    description=(
        "Execute a custom or preset traversal rule against the graph. "
        "A rule consists of ordered steps, each specifying edge types, "
        "direction, target node types, and depth. "
        "Steps execute sequentially: the output of step N becomes "
        "the starting set for step N+1."
    ),
)
async def execute_traversal(body: TraversalRule) -> GraphResponse:
    return traversal_service.execute_traversal(body)
