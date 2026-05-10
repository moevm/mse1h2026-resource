from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel

from app.api.auth import CurrentUser
from app.models.mapper.mapping import (
    AutoEdgeRule,
    ConditionalRule,
    FieldMapping,
    MappingConfig,
    MappingListResponse,
)
from app.models.mapper.template import (
    MappingTemplateDetail,
    MappingTemplateInstantiateRequest,
    MappingTemplateListResponse,
)
from app.repositories import agent_repo
from app.repositories.mapping_repo import mapping_repo
from app.repositories.mapping_template_repo import mapping_template_repo
from app.repositories.raw_data_repo import raw_data_repo
from app.repositories.neo4j_repo import upsert_nodes, upsert_edges, delete_graph_by_sources
from app.services.mapper_service import mapper_service

router = APIRouter()
log = logging.getLogger(__name__)


class MappingUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sample_chunk_id: Optional[str] = None
    field_mappings: Optional[List[FieldMapping]] = None
    conditional_rules: Optional[List[ConditionalRule]] = None
    auto_edge_rules: Optional[List[AutoEdgeRule]] = None
    edge_preset_id: Optional[str] = None
    edge_source_path: Optional[str] = None
    edge_target_path: Optional[str] = None
    edge_type_path: Optional[str] = None
    edge_type_default: Optional[str] = None
    is_active: Optional[bool] = None


class ReplayRequest(BaseModel):
    agent_id: Optional[str] = None
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None


class ReplayResponse(BaseModel):
    chunks_processed: int
    nodes_created: int
    edges_created: int
    errors: List[str] = []


class RecreateEdgesRequest(BaseModel):
    source_types: Optional[List[str]] = None
    edge_preset_id: Optional[str] = "default"


class RecreateEdgesResponse(BaseModel):
    nodes_processed: int
    edges_created: int
    unresolved_count: int

class DeactivateAndClearResponse(BaseModel):
    mapping_id: str
    source_type: str
    deactivated: bool
    sources: List[str] = []
    deleted_nodes: int = 0
    deleted_edges: int = 0


async def replay_mapping_background(mapping_id: str) -> None:
    """Background task to replay mapping on all historical data."""

    log.info(f"Starting background replay for mapping {mapping_id}")

    mapping = mapping_repo.get(mapping_id)
    if not mapping:
        log.error(f"Mapping {mapping_id} not found for replay")
        return

    try:
        chunks_response = await raw_data_repo.list_chunks(
            limit=10000,
        )

        chunks = chunks_response.chunks
        total_processed = 0
        total_nodes = 0
        total_edges = 0

        all_created_nodes: List[Dict[str, Any]] = []

        for chunk in chunks:
            try:
                nodes, edges, unresolved = mapper_service.map_chunk(chunk, mapping)
                agent_name = chunk.metadata.get("agent_name", "replay") if chunk.metadata else "replay"

                if nodes:
                    upsert_nodes(nodes, source=agent_name)
                    total_nodes += len(nodes)
                    all_created_nodes.extend(nodes)

                if edges:
                    upsert_edges(edges, source=agent_name)
                    total_edges += len(edges)

                total_processed += 1

            except Exception as e:
                log.error(f"Error processing chunk {chunk.id}: {e}")

        if all_created_nodes:
            log.info(f"Recreating edges for {len(all_created_nodes)} created nodes...")
            new_edges, new_unresolved = mapper_service.recreate_edges_for_nodes(
                all_created_nodes, mapping
            )
            if new_edges:
                agent_name = chunks[0].metadata.get("agent_name", "replay") if chunks and chunks[0].metadata else "replay"
                upsert_edges(new_edges, source=agent_name)
                total_edges += len(new_edges)
                log.info(f"Created {len(new_edges)} additional edges after all nodes were inserted")
            if new_unresolved:
                log.info(f"Still unresolved: {len(new_unresolved)} references")

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
async def create_mapping(user: CurrentUser, config: MappingConfig):
    existing = mapping_repo.get_by_name(config.name, user_id=user["user_id"])
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Mapping with name '{config.name}' already exists",
        )

    # Auto-pin sample chunk so it doesn't expire
    if config.sample_chunk_id:
        await raw_data_repo.pin_chunk(config.sample_chunk_id)

    created = mapping_repo.create(config, user_id=user["user_id"])
    return created


@router.get(
    "/",
    response_model=MappingListResponse,
    summary="List all mapping configurations",
)
async def list_mappings(
    user: CurrentUser,
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000),
):
    return mapping_repo.list(
        source_type=source_type,
        is_active=is_active,
        limit=limit,
        user_id=user["user_id"],
    )


@router.get(
    "/templates",
    response_model=MappingTemplateListResponse,
    summary="List built-in mapping templates",
)
async def list_mapping_templates(user: CurrentUser):
    templates = mapping_template_repo.list()
    return MappingTemplateListResponse(templates=templates, total=len(templates))


@router.get(
    "/templates/{template_id}",
    response_model=MappingTemplateDetail,
    summary="Get a built-in mapping template",
)
async def get_mapping_template(user: CurrentUser, template_id: str):
    template = mapping_template_repo.get(template_id)
    summary = mapping_template_repo.get_summary(template_id)
    if template is None or summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping template not found",
        )
    return MappingTemplateDetail(template=template, summary=summary)


@router.post(
    "/templates/{template_id}/instantiate",
    response_model=MappingConfig,
    summary="Create a user mapping from a built-in template",
    status_code=status.HTTP_201_CREATED,
)
async def instantiate_mapping_template(
    user: CurrentUser,
    template_id: str,
    request: MappingTemplateInstantiateRequest = MappingTemplateInstantiateRequest(),
):
    import uuid

    template = mapping_template_repo.get(template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping template not found",
        )

    mapping_name = (request.name or template.name).strip()
    if not mapping_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mapping name cannot be empty",
        )

    existing = mapping_repo.get_by_name(mapping_name, user_id=user["user_id"])
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Mapping with name '{mapping_name}' already exists",
        )

    # Auto-resolve sample_chunk_id if not provided:
    # find the first chunk from an agent matching the template's source_type
    sample_chunk_id = request.sample_chunk_id
    if not sample_chunk_id and template.source_type:
        agents = agent_repo.list_agents(user_id=user["user_id"])
        matching_agents = [
            a for a in agents if a.get("source_type") == template.source_type
        ]
        for agent in matching_agents:
            chunks_resp = await raw_data_repo.list_chunks(
                agent_id=agent["agent_id"], limit=1
            )
            if chunks_resp.chunks:
                sample_chunk_id = chunks_resp.chunks[0].id
                break

    created = template.model_copy(deep=True)
    created.id = str(uuid.uuid4())
    created.name = mapping_name
    created.is_active = request.activate
    created.sample_chunk_id = sample_chunk_id
    created.created_by = user["username"]

    # Auto-pin the sample chunk so it doesn't expire
    if sample_chunk_id:
        await raw_data_repo.pin_chunk(sample_chunk_id)

    if request.activate:
        mapping_repo.deactivate_all_for_source(created.source_type)

    return mapping_repo.create(created, user_id=user["user_id"])


@router.post(
    "/recreate-edges",
    response_model=RecreateEdgesResponse,
    summary="Recreate all edges based on auto-edge rules",
)
async def recreate_all_edges(user: CurrentUser, request: RecreateEdgesRequest = None):
    from app.repositories.neo4j_repo import get_all_node_types, get_nodes_by_types

    request = request or RecreateEdgesRequest()

    if request.source_types:
        node_types = request.source_types
    else:
        node_types = get_all_node_types()

    if not node_types:
        return RecreateEdgesResponse(nodes_processed=0, edges_created=0, unresolved_count=0)

    all_nodes = get_nodes_by_types(node_types)
    log.info(f"Recreating edges for {len(all_nodes)} nodes of types: {node_types}")

    import uuid
    dummy_mapping = MappingConfig(
        id=f"edge-recreation-{uuid.uuid4().hex[:8]}",
        name="edge-recreation",
        source_type="custom",
        field_mappings=[],
        edge_preset_id=request.edge_preset_id or "default",
    )

    new_edges, unresolved = mapper_service.recreate_edges_for_nodes(all_nodes, dummy_mapping)

    if new_edges:
        upsert_edges(new_edges, source="edge-recreation")
        log.info(f"Created {len(new_edges)} edges from recreation")

    return RecreateEdgesResponse(
        nodes_processed=len(all_nodes),
        edges_created=len(new_edges),
        unresolved_count=len(unresolved),
    )


@router.get(
    "/active/{source_type}",
    response_model=Optional[MappingConfig],
    summary="Get active mapping for source type",
)
async def get_active_mapping(user: CurrentUser, source_type: str):
    mapping = mapping_repo.get_active_for_source(source_type)
    if mapping is None:
        return None
    raw = mapping_repo.get(mapping.id, user_id=user["user_id"])
    return raw


@router.get(
    "/{mapping_id}",
    response_model=MappingConfig,
    summary="Get a specific mapping configuration",
)
async def get_mapping(user: CurrentUser, mapping_id: str):
    mapping = mapping_repo.get(mapping_id, user_id=user["user_id"])
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
async def update_mapping(user: CurrentUser, mapping_id: str, updates: MappingUpdate):
    existing = mapping_repo.get(mapping_id, user_id=user["user_id"])
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing, key, value)

    # Auto-pin new sample chunk if changed
    new_sample_chunk_id = update_data.get("sample_chunk_id")
    if new_sample_chunk_id:
        await raw_data_repo.pin_chunk(new_sample_chunk_id)

    updated = mapping_repo.update(mapping_id, existing)
    return updated


@router.delete(
    "/{mapping_id}",
    summary="Delete a mapping configuration",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_mapping(user: CurrentUser, mapping_id: str):
    if mapping_repo.get(mapping_id, user_id=user["user_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
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
async def activate_mapping(user: CurrentUser, mapping_id: str, background_tasks: BackgroundTasks):
    if mapping_repo.get(mapping_id, user_id=user["user_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    updated = mapping_repo.activate_for_source(mapping_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )
    log.info(f"Activated mapping {mapping_id} for source_type={updated.source_type}")

    background_tasks.add_task(
        replay_mapping_background,
        mapping_id,
    )
    log.info(f"Scheduled background replay for mapping {mapping_id}")

    return updated


@router.post(
    "/{mapping_id}/deactivate",
    response_model=MappingConfig,
    summary="Deactivate a mapping",
)
async def deactivate_mapping(user: CurrentUser, mapping_id: str):
    if mapping_repo.get(mapping_id, user_id=user["user_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    updated = mapping_repo.set_active(mapping_id, False)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )
    return updated


@router.post(
    "/{mapping_id}/deactivate-and-clear",
    response_model=DeactivateAndClearResponse,
    summary="Deactivate mapping and clear graph data for its source type",
)
async def deactivate_and_clear_mapping(user: CurrentUser, mapping_id: str):
    mapping = mapping_repo.get(mapping_id, user_id=user["user_id"])
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    updated = mapping_repo.set_active(mapping_id, False)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    agents = agent_repo.list_agents()
    sources = [a["name"] for a in agents if a.get("source_type") == mapping.source_type]

    deleted_nodes = 0
    deleted_edges = 0
    if sources:
        deleted = delete_graph_by_sources(sources)
        deleted_nodes = deleted.get("deleted_nodes", 0)
        deleted_edges = deleted.get("deleted_edges", 0)

    return DeactivateAndClearResponse(
        mapping_id=mapping_id,
        source_type=mapping.source_type,
        deactivated=True,
        sources=sources,
        deleted_nodes=deleted_nodes,
        deleted_edges=deleted_edges,
    )


@router.post(
    "/{mapping_id}/replay",
    response_model=ReplayResponse,
    summary="Re-apply mapping to historical data",
)
async def replay_mapping(user: CurrentUser, mapping_id: str, request: ReplayRequest = None):
    """Re-apply mapping to historical raw data.

    Useful when mapping is changed and user wants to update the graph
    with historical data. Processes all chunks, applying only matching ones.
    """

    request = request or ReplayRequest()

    mapping = mapping_repo.get(mapping_id, user_id=user["user_id"])
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    chunks_response = await raw_data_repo.list_chunks(
        agent_id=request.agent_id,
        limit=10000,
    )

    chunks = chunks_response.chunks
    results = ReplayResponse(chunks_processed=0, nodes_created=0, edges_created=0)

    all_created_nodes: List[Dict[str, Any]] = []

    for chunk in chunks:
        try:
            nodes, edges, unresolved = mapper_service.map_chunk(chunk, mapping)
            agent_name = chunk.metadata.get("agent_name", "replay") if chunk.metadata else "replay"

            if nodes:
                upsert_nodes(nodes, source=agent_name)
                results.nodes_created += len(nodes)
                all_created_nodes.extend(nodes)

            if edges:
                upsert_edges(edges, source=agent_name)
                results.edges_created += len(edges)

            results.chunks_processed += 1

        except Exception as e:
            log.error(f"Error processing chunk {chunk.id}: {e}")
            results.errors.append(f"Chunk {chunk.id[:8]}: {str(e)}")

    if all_created_nodes:
        log.info(f"Recreating edges for {len(all_created_nodes)} created nodes...")
        new_edges, new_unresolved = mapper_service.recreate_edges_for_nodes(
            all_created_nodes, mapping
        )
        if new_edges:
            agent_name = chunks[0].metadata.get("agent_name", "replay") if chunks and chunks[0].metadata else "replay"
            upsert_edges(new_edges, source=agent_name)
            results.edges_created += len(new_edges)
            log.info(f"Created {len(new_edges)} additional edges after all nodes were inserted")

    log.info(
        f"Replay complete: {results.chunks_processed} chunks, "
        f"{results.nodes_created} nodes, {results.edges_created} edges"
    )
    return results
