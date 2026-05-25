from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.api.auth import CurrentUser
from app.models.topology import (
    GraphResponse,
    GraphStatsResponse,
    ImpactRequest,
    PathRequest,
    SubgraphRequest,
)
from app.repositories import neo4j_repo
from app.services import graph_service

router = APIRouter()


@router.get(
    "/full",
    response_model=GraphResponse,
    summary="Get the full topology graph",
    description="Returns all nodes and edges (with a default limit of 500 to protect the browser).",
)
async def full_graph(
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
    app_id: Optional[str] = Query(None, description="Filter by application ID"),
    exclude_node_types: Optional[str] = Query(None, description="Comma-separated node types to exclude"),
    exclude_edge_types: Optional[str] = Query(None, description="Comma-separated edge types to exclude"),
    filter_mode: str = Query("ghost", description="Filter mode: ghost or exclude"),
    as_of: Optional[str] = Query(None, description="ISO datetime — show graph state at this time"),
    window_start: Optional[str] = Query(None, description="ISO datetime — start of activity window for per-edge metrics"),
    window_end: Optional[str] = Query(None, description="ISO datetime — end of activity window for per-edge metrics"),
):
    ex_nodes = exclude_node_types.split(",") if exclude_node_types else None
    ex_edges = exclude_edge_types.split(",") if exclude_edge_types else None
    return graph_service.get_full_graph(
        limit,
        app_id=app_id,
        user_id=user["user_id"],
        exclude_node_types=ex_nodes,
        exclude_edge_types=ex_edges,
        filter_mode=filter_mode,
        as_of=as_of,
        window_start=window_start,
        window_end=window_end,
    )


@router.post(
    "/subgraph",
    response_model=GraphResponse,
    summary="Get a subgraph around a specific node",
    description="BFS from center_node_id up to *depth* hops. Optionally filter by node/edge types.",
)
async def subgraph(user: CurrentUser, body: SubgraphRequest):
    return graph_service.get_subgraph(
        center_id=body.center_node_id,
        depth=body.depth,
        node_types=body.node_types,
        edge_types=body.edge_types,
        user_id=user["user_id"],
    )


@router.post(
    "/path",
    response_model=GraphResponse,
    summary="Find the shortest path between two nodes",
)
async def shortest_path(user: CurrentUser, body: PathRequest):
    return graph_service.find_path(
        source_id=body.source_id,
        target_id=body.target_id,
        max_depth=body.max_depth,
        user_id=user["user_id"],
    )


@router.post(
    "/impact",
    response_model=GraphResponse,
    summary="Impact / blast-radius analysis",
    description=(
        "Starting from a node, traverse downstream (or upstream / both) "
        "to find all affected resources."
    ),
)
async def impact_analysis(user: CurrentUser, body: ImpactRequest):
    return graph_service.get_impact(
        node_id=body.node_id,
        depth=body.depth,
        direction=body.direction,
        user_id=user["user_id"],
    )


@router.get(
    "/stats",
    response_model=GraphStatsResponse,
    summary="Aggregated graph statistics",
)
async def graph_stats(user: CurrentUser):
    return graph_service.get_stats(user_id=user["user_id"])


@router.get(
    "/analytics",
    summary="NetworkX analytics (PageRank, betweenness, communities)",
)
async def analytics(
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=10000)] = 1000,
):
    return graph_service.compute_analytics(limit, user_id=user["user_id"])


@router.get(
    "/layout",
    summary="Graph data with pre-computed (x, y) layout positions",
    description="Useful for rendering the graph immediately on the frontend.",
)
async def graph_layout(
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
    layout: Annotated[str, Query(pattern="^(spring|kamada_kawai|circular|shell)$")] = "spring",
):
    return graph_service.get_graph_with_layout(limit, layout, user_id=user["user_id"])


class DeleteNodeResponse(BaseModel):
    deleted: bool
    node_id: str
    deleted_edges: int


class ClearStaleRequest(BaseModel):
    ttl_seconds: int = 300


class ClearStaleResponse(BaseModel):
    deleted_nodes: int
    deleted_edges: int
    cutoff_iso: str


@router.delete(
    "/node/{node_id:path}",
    response_model=DeleteNodeResponse,
    summary="Delete a single node (and its edges) by external_id",
)
async def delete_node(user: CurrentUser, node_id: str):
    result = neo4j_repo.delete_node_by_external_id(node_id)
    if not result["deleted"]:
        raise HTTPException(status_code=404, detail="Node not found")
    return DeleteNodeResponse(
        deleted=True, node_id=node_id, deleted_edges=result["deleted_edges"],
    )


@router.post(
    "/clear-stale",
    response_model=ClearStaleResponse,
    summary="Delete all nodes whose last_seen_at is older than ttl_seconds",
)
async def clear_stale_nodes(user: CurrentUser, body: ClearStaleRequest):
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=body.ttl_seconds)
    cutoff_iso = cutoff.isoformat()
    result = neo4j_repo.delete_nodes_older_than(cutoff_iso)
    return ClearStaleResponse(
        deleted_nodes=result["deleted_nodes"],
        deleted_edges=result["deleted_edges"],
        cutoff_iso=cutoff_iso,
    )
