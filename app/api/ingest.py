
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import require_agent
from app.models.topology import TopologyUpdate
from app.services import ingest_service

router = APIRouter()


@router.post(
    "/topology",
    summary="Ingest a topology update batch",
    description=(
        "Accepts a batch of nodes and edges from an external agent "
        "(e.g. OTel Collector, K8s agent). "
        "All nodes are upserted (MERGE) by their URN id; "
        "edges are upserted by (source_id, target_id, type)."
    ),
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_topology(
    payload: TopologyUpdate,
    agent: Dict[str, Any] = Depends(require_agent),
):

    if not payload.nodes and not payload.edges:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one node or edge must be provided",
        )

    # Override source with the registered agent name for trustworthy attribution
    payload.source = agent["name"]

    result = ingest_service.process_topology_update(payload)

    if not result.to_dict()["success"]:
        raise HTTPException(
            status_code=status.HTTP_207_MULTI_STATUS,
            detail=result.to_dict(),
        )

    return result.to_dict()
