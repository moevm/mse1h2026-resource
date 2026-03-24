from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel

from app.models.mapper.mapping import MappingConfig, MappingListResponse
from app.models.mapper.raw_data import RawDataSource
from app.repositories.mapping_repo import mapping_repo
from app.repositories.raw_data_repo import raw_data_repo
from app.repositories.neo4j_repo import upsert_nodes, upsert_edges
from app.services.mapper_service import mapper_service

router = APIRouter()
log = logging.getLogger(__name__)


class MappingUpdate(BaseModel):
    """Partial update for mapping configuration."""
    name: Optional[str] = None
    description: Optional[str] = None
    sample_chunk_id: Optional[str] = None
    field_mappings: Optional[list] = None
    conditional_rules: Optional[list] = None
    auto_edge_rules: Optional[list] = None
    edge_preset_id: Optional[str] = None
    edge_source_path: Optional[str] = None
    edge_target_path: Optional[str] = None
    edge_type_path: Optional[str] = None
    edge_type_default: Optional[str] = None
    is_active: Optional[bool] = None


class ReplayRequest(BaseModel):
    """Request for replaying mapping on historical data."""
    agent_id: Optional[str] = None
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None


class ReplayResponse(BaseModel):
    """Response for replay operation."""
    chunks_processed: int
    nodes_created: int
    edges_created: int
    errors: List[str] = []


async def replay_mapping_background(mapping_id: str, source_type: str) -> None:
    """Background task to replay mapping on all historical data."""
    log.info(f"Starting background replay for mapping {mapping_id} (source_type={source_type})")

    mapping = mapping_repo.get(mapping_id)
    if not mapping:
        log.error(f"Mapping {mapping_id} not found for replay")
        return

    # Convert source_type string to RawDataSource enum if valid
    source_type_enum = None
    try:
        source_type_enum = RawDataSource(source_type)
    except ValueError:
        pass  # Unknown source type, will list all

    try:
        chunks_response = await raw_data_repo.list_chunks(
            source_type=source_type_enum,
            limit=10000,  # Process up to 10k chunks
        )

        chunks = chunks_response.chunks
        total_processed = 0
        total_nodes = 0
        total_edges = 0

        for chunk in chunks:
            try:
                nodes, edges, unresolved = mapper_service.map_chunk(chunk, mapping)

                # Get agent name from metadata
                agent_name = chunk.metadata.get("agent_name", "replay") if chunk.metadata else "replay"

                if nodes:
                    upsert_nodes(nodes, source=agent_name)
                    total_nodes += len(nodes)

                if edges:
                    upsert_edges(edges, source=agent_name)
                    total_edges += len(edges)

                total_processed += 1

            except Exception as e:
                log.error(f"Error processing chunk {chunk.id}: {e}")

        log.info(
            f"Background replay complete for {mapping_id}: "
            f"{total_processed} chunks, {total_nodes} nodes, {total_edges} edges"
        )

    except Exception as e:
        log.error(f"Background replay failed for {mapping_id}: {e}")


@router.post(
    "/",
    response_model=MappingConfig,
    summary="Create a new mapping configuration",
    status_code=status.HTTP_201_CREATED,
)
async def create_mapping(config: MappingConfig):
    """Create a new mapping configuration.

    The mapping defines how to transform raw data from a specific
    source type into graph nodes and edges.
    """
    # Check for duplicate name
    existing = mapping_repo.get_by_name(config.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Mapping with name '{config.name}' already exists",
        )

    created = mapping_repo.create(config)
    return created


@router.get(
    "/",
    response_model=MappingListResponse,
    summary="List all mapping configurations",
)
async def list_mappings(
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000),
):
    """List mapping configurations with optional filters."""
    return mapping_repo.list(
        source_type=source_type,
        is_active=is_active,
        limit=limit,
    )


@router.get(
    "/{mapping_id}",
    response_model=MappingConfig,
    summary="Get a specific mapping configuration",
)
async def get_mapping(mapping_id: str):
    """Get a mapping configuration by ID."""
    mapping = mapping_repo.get(mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )
    return mapping


@router.put(
    "/{mapping_id}",
    response_model=MappingConfig,
    summary="Update a mapping configuration",
)
async def update_mapping(mapping_id: str, updates: MappingUpdate):
    """Update an existing mapping configuration (partial update)."""
    # Get existing mapping
    existing = mapping_repo.get(mapping_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    # Apply partial updates
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing, key, value)

    updated = mapping_repo.update(mapping_id, existing)
    return updated


@router.delete(
    "/{mapping_id}",
    summary="Delete a mapping configuration",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_mapping(mapping_id: str):
    """Delete a mapping configuration."""
    deleted = mapping_repo.delete(mapping_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )


@router.post(
    "/{mapping_id}/activate",
    response_model=MappingConfig,
    summary="Activate a mapping for auto-apply",
)
async def activate_mapping(mapping_id: str, background_tasks: BackgroundTasks):
    """Activate a mapping for auto-apply.

    Deactivates any other active mapping with the same source_type.
    Active mappings are automatically applied to incoming raw data.
    Also triggers a background replay on all historical data for this source type.
    """
    updated = mapping_repo.activate_for_source(mapping_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )
    log.info(f"Activated mapping {mapping_id} for source_type={updated.source_type}")

    # Trigger background replay on historical data
    background_tasks.add_task(
        replay_mapping_background,
        mapping_id,
        updated.source_type,
    )
    log.info(f"Scheduled background replay for mapping {mapping_id}")

    return updated


@router.post(
    "/{mapping_id}/deactivate",
    response_model=MappingConfig,
    summary="Deactivate a mapping",
)
async def deactivate_mapping(mapping_id: str):
    """Deactivate a mapping."""
    updated = mapping_repo.set_active(mapping_id, False)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )
    return updated


@router.get(
    "/active/{source_type}",
    response_model=Optional[MappingConfig],
    summary="Get active mapping for source type",
)
async def get_active_mapping(source_type: str):
    """Get the currently active mapping for a source type.

    Returns null if no mapping is active for this source type.
    """
    return mapping_repo.get_active_for_source(source_type)


@router.post(
    "/{mapping_id}/replay",
    response_model=ReplayResponse,
    summary="Re-apply mapping to historical data",
)
async def replay_mapping(mapping_id: str, request: ReplayRequest = None):
    """Re-apply mapping to historical raw data.

    Processes all chunks for the mapping's source_type.
    """
    request = request or ReplayRequest()

    mapping = mapping_repo.get(mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    # Get chunks from Redis
    # Convert source_type string to RawDataSource enum if valid
    source_type_enum = None
    try:
        source_type_enum = RawDataSource(mapping.source_type)
    except ValueError:
        pass  # Unknown source type, will list all

    chunks_response = await raw_data_repo.list_chunks(
        source_type=source_type_enum,
        agent_id=request.agent_id,
        limit=10000,  # Process up to 10k chunks
    )

    chunks = chunks_response.chunks
    results = ReplayResponse(chunks_processed=0, nodes_created=0, edges_created=0)

    for chunk in chunks:
        try:
            nodes, edges, unresolved = mapper_service.map_chunk(chunk, mapping)

            # Get agent name from metadata
            agent_name = chunk.metadata.get("agent_name", "replay") if chunk.metadata else "replay"

            if nodes:
                upsert_nodes(nodes, source=agent_name)
                results.nodes_created += len(nodes)

            if edges:
                upsert_edges(edges, source=agent_name)
                results.edges_created += len(edges)

            results.chunks_processed += 1

        except Exception as e:
            log.error(f"Error processing chunk {chunk.id}: {e}")
            results.errors.append(f"Chunk {chunk.id[:8]}: {str(e)}")

    log.info(
        f"Replay complete: {results.chunks_processed} chunks, "
        f"{results.nodes_created} nodes, {results.edges_created} edges"
    )
    return results
