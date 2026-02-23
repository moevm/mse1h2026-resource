from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from app.repositories import neo4j_repo
from app.models.topology import (
    GraphEdge,
    GraphNode,
    GraphResponse,
    GraphStatsResponse,
)

log = logging.getLogger(__name__)


def _to_graph_node(raw: Dict[str, Any]) -> GraphNode:
    reserved = {
        "id", "type", "name", "status", "environment",
        "source", "created_at", "updated_at", "last_seen_at",
    }
    props = {k: v for k, v in raw.items() if k not in reserved}
    return GraphNode(
        id=raw["id"],
        type=raw.get("type", "unknown"),
        name=raw.get("name", raw["id"]),
        status=raw.get("status"),
        environment=raw.get("environment"),
        properties=props,
    )


def _to_graph_edge(raw: Dict[str, Any]) -> GraphEdge:
    reserved = {
        "source_id", "target_id", "type", "status",
        # internal metadata
        "source", "first_seen", "last_seen", "weight",
    }
    props = {k: v for k, v in raw.items() if k not in reserved}
    edge_type = raw.get("type", "unknown")
    return GraphEdge(
        source_id=raw["source_id"],
        target_id=raw["target_id"],
        type=edge_type.lower(),
        status=raw.get("status"),
        properties=props,
    )


def _build_response(raw_nodes: List[Dict], raw_edges: List[Dict]) -> GraphResponse:
    nodes = [_to_graph_node(n) for n in raw_nodes]
    edges = [_to_graph_edge(e) for e in raw_edges]
    return GraphResponse(
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
    )


def get_full_graph(limit: int = 500) -> GraphResponse:
    raw_nodes, raw_edges = neo4j_repo.get_full_graph(limit)
    return _build_response(raw_nodes, raw_edges)


def get_subgraph(
    center_id: str,
    depth: int = 2,
    node_types: Optional[List[str]] = None,
    edge_types: Optional[List[str]] = None,
) -> GraphResponse:
    raw_nodes, raw_edges = neo4j_repo.get_subgraph(
        center_id, depth, node_types, edge_types,
    )
    return _build_response(raw_nodes, raw_edges)


def find_path(source_id: str, target_id: str, max_depth: int = 5) -> GraphResponse:
    raw_nodes, raw_edges = neo4j_repo.find_shortest_path(source_id, target_id, max_depth)
    return _build_response(raw_nodes, raw_edges)


def get_impact(node_id: str, depth: int = 3, direction: str = "downstream") -> GraphResponse:
    raw_nodes, raw_edges = neo4j_repo.get_impact(node_id, depth, direction)
    return _build_response(raw_nodes, raw_edges)


def get_stats() -> GraphStatsResponse:
    data = neo4j_repo.get_graph_stats()
    if "edges_by_type" in data:
        data["edges_by_type"] = {k.lower(): v for k, v in data["edges_by_type"].items()}
    return GraphStatsResponse(**data)


def _build_nx_graph(response: GraphResponse) -> nx.DiGraph:
    _PRIMITIVE = (str, int, float, bool)
    G = nx.DiGraph()
    for n in response.nodes:
        safe = {k: v for k, v in n.properties.items() if isinstance(v, _PRIMITIVE)}
        G.add_node(n.id, type=n.type, name=n.name, status=n.status or "active", **safe)
    for e in response.edges:
        safe = {k: v for k, v in e.properties.items() if isinstance(v, _PRIMITIVE)}
        G.add_edge(e.source_id, e.target_id, type=e.type, **safe)
    return G


def compute_analytics(limit: int = 1000) -> Dict[str, Any]:
    graph_resp = get_full_graph(limit)
    G = _build_nx_graph(graph_resp)

    if G.number_of_nodes() == 0:
        return {
            "pagerank": {},
            "betweenness": {},
            "in_degree": {},
            "out_degree": {},
            "communities": [],
        }

    analytics: Dict[str, Any] = {}

    try:
        analytics["pagerank"] = nx.pagerank(G, max_iter=200, tol=1e-5)
    except nx.PowerIterationFailedConvergence:
        analytics["pagerank"] = dict.fromkeys(G.nodes, 1.0 / G.number_of_nodes())

    k_sample = min(300, G.number_of_nodes())
    try:
        analytics["betweenness"] = nx.betweenness_centrality(
            G,
            k=k_sample if G.number_of_nodes() > k_sample else None,
            normalized=True,
        )
    except Exception:
        analytics["betweenness"] = dict.fromkeys(G.nodes, 0.0)

    analytics["in_degree"]  = dict(G.in_degree())
    analytics["out_degree"] = dict(G.out_degree())

    undirected = G.to_undirected()
    analytics["communities"] = [
        list(c) for c in nx.connected_components(undirected)
    ]

    return analytics


def get_graph_with_layout(limit: int = 500, layout: str = "spring") -> Dict[str, Any]:
    graph_resp = get_full_graph(limit)
    G = _build_nx_graph(graph_resp)

    layout_funcs = {
        "spring": nx.spring_layout,
        "kamada_kawai": nx.kamada_kawai_layout,
        "circular": nx.circular_layout,
        "shell": nx.shell_layout,
    }
    layout_fn = layout_funcs.get(layout, nx.spring_layout)
    positions = layout_fn(G) if G.number_of_nodes() > 0 else {}

    nodes_out = []
    for n in graph_resp.nodes:
        pos = positions.get(n.id, (0.0, 0.0))
        node_dict = n.model_dump()
        node_dict["x"] = float(pos[0])
        node_dict["y"] = float(pos[1])
        nodes_out.append(node_dict)

    edges_out = [e.model_dump() for e in graph_resp.edges]

    return {
        "nodes": nodes_out,
        "edges": edges_out,
        "node_count": len(nodes_out),
        "edge_count": len(edges_out),
        "layout": layout,
    }
