from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Query

from app.api.auth import CurrentUser
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
async def list_presets(user: CurrentUser) -> list[dict]:
    return traversal_service.list_presets()


@router.post(
    "/execute",
    summary="Execute a traversal rule",
    description=(
        "Execute a custom or preset traversal rule against the graph. "
        "A rule consists of ordered steps, each specifying edge types, "
        "direction, target node types, and depth. "
        "Steps execute sequentially: the output of step N becomes "
        "the starting set for step N+1."
    ),
)
async def execute_traversal(
    user: CurrentUser,
    body: TraversalRule,
    app_id: Annotated[Optional[str], Query(description="Filter traversal to one application")] = None,
) -> GraphResponse:
    return traversal_service.execute_traversal(body, user_id=user["user_id"], app_id=app_id)
