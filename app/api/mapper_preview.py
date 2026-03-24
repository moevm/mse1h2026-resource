from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models.mapper.raw_data import RawDataChunk
from app.models.mapper.mapping import UnresolvedReference
from app.repositories.mapping_repo import mapping_repo
from app.repositories.raw_data_repo import raw_data_repo
from app.services.mapper_service import mapper_service
from app.services.ingest_service import process_topology_update
from app.models.topology import TopologyUpdate
from app.models.nodes import (
    ServiceNode, EndpointNode, DeploymentNode, PodNode, ComputeNodeNode,
    DatabaseNode, TableNode, QueueTopicNode, CacheNode, ExternalAPINode,
    SecretConfigNode, LibraryNode, TeamOwnerNode, SLASLONode, RegionClusterNode,
)
from app.models.edges import (
    CallsEdge, PublishesToEdge, ConsumesFromEdge, ReadsEdge, WritesEdge,
    DependsOnEdge, DeployedOnEdge, OwnedByEdge, AuthenticatesViaEdge,
    RateLimitedByEdge, FailsOverToEdge,
)

router = APIRouter()

NODE_TYPE_MAP = {
    "Service": ServiceNode,
    "Endpoint": EndpointNode,
    "Deployment": DeploymentNode,
    "Pod": PodNode,
    "Node": ComputeNodeNode,
    "Database": DatabaseNode,
    "Table": TableNode,
    "QueueTopic": QueueTopicNode,
    "Cache": CacheNode,
    "ExternalAPI": ExternalAPINode,
    "SecretConfig": SecretConfigNode,
    "Library": LibraryNode,
    "TeamOwner": TeamOwnerNode,
    "SLASLO": SLASLONode,
    "RegionCluster": RegionClusterNode,
}

EDGE_TYPE_MAP = {
    "calls": CallsEdge,
    "publishesto": PublishesToEdge,
    "consumesfrom": ConsumesFromEdge,
    "reads": ReadsEdge,
    "writes": WritesEdge,
    "dependson": DependsOnEdge,
    "deployedon": DeployedOnEdge,
    "ownedby": OwnedByEdge,
    "authenticatesvia": AuthenticatesViaEdge,
    "ratelimitedby": RateLimitedByEdge,
    "fails_over_to": FailsOverToEdge,
}


class PreviewRequest(BaseModel):
    """Request for previewing or applying a mapping."""

    chunk_id: str = Field(..., description="ID of the raw data chunk")
    mapping_id: str = Field(..., description="ID of the mapping to apply")


class PreviewResponse(BaseModel):
    """Response for preview endpoint."""

    chunk_id: str
    mapping_id: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    warnings: List[str] = Field(default_factory=list)
    unresolved_references: List[UnresolvedReference] = Field(default_factory=list)


class ApplyResponse(BaseModel):
    """Response for apply endpoint."""

    chunk_id: str
    mapping_id: str
    nodes_processed: int
    edges_processed: int
    success: bool
    errors: List[str] = Field(default_factory=list)
    unresolved_references: List[UnresolvedReference] = Field(default_factory=list)


@router.post(
    "/preview",
    response_model=PreviewResponse,
    summary="Preview mapping result without persisting",
)
async def preview_mapping(request: PreviewRequest):
    """Preview how raw data would be transformed by a mapping.

    Returns the nodes and edges that would be created without
    actually persisting them to the graph.
    """
    # Get the chunk
    chunk_data = await raw_data_repo.get_chunk(request.chunk_id)
    if not chunk_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found or expired",
        )

    # Get the mapping
    mapping = mapping_repo.get(request.mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    chunk = RawDataChunk(**chunk_data)

    nodes, edges, unresolved = mapper_service.map_chunk(chunk, mapping)

    warnings = []
    if not nodes:
        warnings.append("No nodes generated from this mapping")
    for node in nodes:
        if not node.get("id"):
            warnings.append(f"Node missing id: {node.get('type', 'unknown')}")

    for ref in unresolved:
        warnings.append(
            f"{ref.source_node_type} '{ref.source_node_id.split(':')[-1]}' "
            f"has {ref.source_field}='{ref.expected_target_value}' "
            f"→ {ref.expected_target_type} not found"
        )

    return PreviewResponse(
        chunk_id=request.chunk_id,
        mapping_id=request.mapping_id,
        nodes=nodes,
        edges=edges,
        warnings=warnings,
        unresolved_references=unresolved,
    )


@router.post(
    "/apply",
    response_model=ApplyResponse,
    summary="Apply mapping and ingest into graph",
)
async def apply_mapping(request: PreviewRequest):
    """Apply a mapping to a chunk and persist the result to Neo4j.

    The mapped data is ingested into the graph database and the
    chunk is marked as processed.
    """
    # Get the chunk
    chunk_data = await raw_data_repo.get_chunk(request.chunk_id)
    if not chunk_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found or expired",
        )

    mapping = mapping_repo.get(request.mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    chunk = RawDataChunk(**chunk_data)

    nodes, edges, unresolved = mapper_service.map_chunk(chunk, mapping)

    if not nodes and not edges:
        return ApplyResponse(
            chunk_id=request.chunk_id,
            mapping_id=request.mapping_id,
            nodes_processed=0,
            edges_processed=0,
            success=True,
            errors=["No nodes or edges generated from mapping"],
            unresolved_references=unresolved,
        )

    try:
        node_models = []
        for n in nodes:
            # Determine the correct node type and instantiate
            node_type = n.get("type", "Service")
            node_class = NODE_TYPE_MAP.get(node_type, ServiceNode)
            node_models.append(node_class(**n))

        edge_models = []
        for e in edges:
            # Determine the correct edge type and instantiate
            edge_type = e.get("type", "dependson")
            edge_class = EDGE_TYPE_MAP.get(edge_type, DependsOnEdge)
            edge_models.append(edge_class(**e))

        # Create topology update
        update = TopologyUpdate(
            source=f"mapper:{mapping.name}",
            nodes=node_models,
            edges=edge_models,
        )

        result = process_topology_update(update)

        await raw_data_repo.mark_processed(request.chunk_id, request.mapping_id)

        return ApplyResponse(
            chunk_id=request.chunk_id,
            mapping_id=request.mapping_id,
            nodes_processed=result.nodes_processed,
            edges_processed=result.edges_processed,
            success=len(result.errors) == 0,
            errors=result.errors,
            unresolved_references=unresolved,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process mapped data: {str(e)}",
        )


@router.post(
    "/preview-raw",
    response_model=PreviewResponse,
    summary="Preview mapping with raw JSON data",
)
async def preview_raw_data(
    raw_data: Dict[str, Any],
    mapping_id: str,
):
    """Preview mapping with raw JSON data.

    """
    mapping = mapping_repo.get(mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    from app.models.mapper.raw_data import RawDataSource
    chunk = RawDataChunk(
        id="preview",
        agent_id="preview",
        source_type=RawDataSource.CUSTOM,
        data=raw_data,
    )

    nodes, edges, warnings, unresolved = mapper_service.preview(raw_data, mapping)

    return PreviewResponse(
        chunk_id="preview",
        mapping_id=mapping_id,
        nodes=nodes,
        edges=edges,
        warnings=warnings,
        unresolved_references=unresolved,
    )
