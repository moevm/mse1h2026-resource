from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import require_agent
from app.models.mapper.raw_data import RawDataSource, RawDataListResponse
from app.repositories.raw_data_repo import raw_data_repo
from app.repositories.mapping_repo import mapping_repo
from app.repositories.neo4j_repo import upsert_nodes, upsert_edges
from app.services.mapper_service import mapper_service

router = APIRouter()
log = logging.getLogger(__name__)


@router.post(
    "/raw",
    summary="Receive raw telemetry data",
    description="Accept any JSON format from telemetry sources for later mapping",
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_raw_data(
    payload: Dict[str, Any],
    source_type: RawDataSource = Query(
        ...,
        description="Type of data source (opentelemetry-traces, kubernetes-api, etc.)",
    ),
    agent: Dict[str, Any] = Depends(require_agent),
):
    """Receive raw telemetry data from an agent.

    Data is stored temporarily (24h TTL) in Redis for history/timeline.
    If an active mapping exists for this source_type, it is automatically
    applied and the resulting nodes/edges are saved to Neo4j.
    """
    agent_name = agent.get("name", "unknown")

    # 1. Always store raw data in Redis (for history/timeline)
    chunk_id = await raw_data_repo.store_chunk(
        agent_id=agent["agent_id"],
        source_type=source_type,
        data=payload,
        metadata={
            "agent_name": agent_name,
            "agent_source_type": agent.get("source_type"),
        },
    )

    # 2. Check for active mapping for this source_type
    active_mapping = mapping_repo.get_active_for_source(source_type.value)

    # 3. If active mapping exists, auto-apply
    nodes_created = 0
    edges_created = 0
    mapping_applied = False

    if active_mapping:
        try:
            # Create a temporary chunk object for mapping
            from app.models.mapper.raw_data import RawDataChunk
            from datetime import datetime, timezone
            temp_chunk = RawDataChunk(
                id=chunk_id,
                agent_id=agent["agent_id"],
                source_type=source_type,
                timestamp=datetime.now(timezone.utc),
                data=payload,
            )

            nodes, edges, unresolved = mapper_service.map_chunk(temp_chunk, active_mapping)

            if nodes:
                upsert_nodes(nodes, source=agent_name)
                nodes_created = len(nodes)

            if edges:
                upsert_edges(edges, source=agent_name)
                edges_created = len(edges)

            mapping_applied = True

            log.info(
                f"Auto-applied mapping '{active_mapping.name}' to chunk {chunk_id[:8]}: "
                f"{nodes_created} nodes, {edges_created} edges"
            )

        except Exception as e:
            log.error(f"Error auto-applying mapping: {e}")
            # Don't fail the request - data is still stored

    return {
        "chunk_id": chunk_id,
        "status": "stored",
        "mapped": mapping_applied,
        "mapping_name": active_mapping.name if active_mapping else None,
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "message": (
            f"Data stored and mapped with '{active_mapping.name}'."
            if mapping_applied
            else "Data stored. No active mapping for this source type."
        ),
    }


@router.get(
    "/raw",
    response_model=RawDataListResponse,
    summary="List stored raw data chunks",
)
async def list_raw_data(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    source_type: Optional[RawDataSource] = Query(None, description="Filter by source type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of chunks to return"),
):
    """List stored raw data chunks with optional filters."""
    return await raw_data_repo.list_chunks(
        agent_id=agent_id,
        source_type=source_type,
        limit=limit,
    )


@router.get(
    "/raw/{chunk_id}",
    summary="Get specific raw data chunk",
)
async def get_raw_data(chunk_id: str):
    """Retrieve a specific raw data chunk by ID."""
    chunk = await raw_data_repo.get_chunk(chunk_id)
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found or expired",
        )
    return chunk


@router.delete(
    "/raw/{chunk_id}",
    summary="Delete a raw data chunk",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_raw_data(chunk_id: str):
    """Delete a specific raw data chunk."""
    deleted = await raw_data_repo.delete_chunk(chunk_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found",
        )
