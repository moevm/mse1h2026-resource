from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Query

from app.models.topology import (
    GraphResponse,
    GraphStatsResponse,
    ImpactRequest,
    PathRequest,
    SubgraphRequest,
)
from app.services import graph_service

router = APIRouter()

@router.get(
    "/full",
    response_model=GraphResponse,
    summary="Get the full topology graph",
    description="Returns all nodes and edges (with a default limit of 500 to protect the browser).",
)
async def full_graph(limit: Annotated[int, Query(ge=1, le=5000)] = 500):
    return graph_service.get_full_graph(limit)


@router.post(
    "/subgraph",
    response_model=GraphResponse,
    summary="Get a subgraph around a specific node",
    description="BFS from center_node_id up to *depth* hops. Optionally filter by node/edge types.",
)
async def subgraph(body: SubgraphRequest):
    return graph_service.get_subgraph(
        center_id=body.center_node_id,
        depth=body.depth,
        node_types=body.node_types,
        edge_types=body.edge_types,
    )

@router.post(
    "/path",
    response_model=GraphResponse,
    summary="Find the shortest path between two nodes",
)
async def shortest_path(body: PathRequest):
    return graph_service.find_path(
        source_id=body.source_id,
        target_id=body.target_id,
        max_depth=body.max_depth,
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
async def impact_analysis(body: ImpactRequest):
    return graph_service.get_impact(
        node_id=body.node_id,
        depth=body.depth,
        direction=body.direction,
    )


@router.get(
    "/stats",
    response_model=GraphStatsResponse,
    summary="Aggregated graph statistics",
)
async def graph_stats():
    return graph_service.get_stats()


@router.get(
    "/analytics",
    summary="NetworkX analytics (PageRank, betweenness, communities)",
)
async def analytics(limit: Annotated[int, Query(ge=1, le=10000)] = 1000):
    return graph_service.compute_analytics(limit)


@router.get(
    "/layout",
    summary="Graph data with pre-computed (x, y) layout positions",
    description="Useful for rendering the graph immediately on the frontend.",
)
async def graph_layout(
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
    layout: Annotated[str, Query(pattern="^(spring|kamada_kawai|circular|shell)$")] = "spring",
):
    return graph_service.get_graph_with_layout(limit, layout)
