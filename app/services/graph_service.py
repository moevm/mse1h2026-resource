from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import networkx as nx

from app.repositories import neo4j_repo, application_repo, agent_repo
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

    connected_ids = set()
    for edge in edges:
        connected_ids.add(edge.source_id)
        connected_ids.add(edge.target_id)

    # Hide infra config blobs that are not part of topology relationships.
    nodes = [
        node for node in nodes
        if not (node.type == "SecretConfig" and node.id not in connected_ids)
    ]
    node_ids = {node.id for node in nodes}
    edges = [
        edge for edge in edges
        if edge.source_id in node_ids and edge.target_id in node_ids
    ]

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
    )


def get_full_graph(
    limit: int = 500,
    app_id: Optional[str] = None,
    user_id: Optional[str] = None,
    exclude_node_types: Optional[List[str]] = None,
    exclude_edge_types: Optional[List[str]] = None,
    filter_mode: str = "ghost",
    as_of: Optional[str] = None,
    window_start: Optional[str] = None,
    window_end: Optional[str] = None,
) -> GraphResponse:
    ex_nodes = exclude_node_types if filter_mode == "exclude" else None
    ex_edges = exclude_edge_types if filter_mode == "exclude" else None

    if app_id:
        agent_names = application_repo.get_agent_names_for_application(app_id)
        if not agent_names:
            return GraphResponse(nodes=[], edges=[], node_count=0, edge_count=0)
        raw_nodes, raw_edges = neo4j_repo.get_graph_by_sources(
            agent_names, limit, exclude_node_types=ex_nodes, exclude_edge_types=ex_edges,
            as_of=as_of,
        )
    elif user_id:
        agent_names = agent_repo.get_agent_names_for_user(user_id)
        if not agent_names:
            return GraphResponse(nodes=[], edges=[], node_count=0, edge_count=0)
        raw_nodes, raw_edges = neo4j_repo.get_graph_by_sources(
            agent_names, limit, exclude_node_types=ex_nodes, exclude_edge_types=ex_edges,
            as_of=as_of,
        )
    else:
        raw_nodes, raw_edges = neo4j_repo.get_full_graph(
            limit, exclude_node_types=ex_nodes, exclude_edge_types=ex_edges, as_of=as_of,
        )

    endpoint_activity = _load_endpoint_activity(raw_nodes, window_start, window_end) if raw_nodes else {}

    if window_start or window_end:
        _enrich_edges_with_window(raw_edges, window_start, window_end)
        _enrich_endpoints_with_window(raw_nodes, endpoint_activity)
    if endpoint_activity:
        _enrich_ownedby_edges_with_endpoint_load(raw_edges, endpoint_activity)

    return _build_response(raw_nodes, raw_edges)


def _enrich_edges_with_window(
    raw_edges: List[Dict[str, Any]],
    window_start: Optional[str],
    window_end: Optional[str],
) -> None:
    if not raw_edges:
        return
    sigs = []
    sig_by_edge: Dict[int, str] = {}
    for i, e in enumerate(raw_edges):
        src = e.get("source_id")
        tgt = e.get("target_id")
        typ = e.get("type")
        if not (src and tgt and typ):
            continue
        sig = f"{src}|{tgt}|{typ.upper()}"
        sigs.append(sig)
        sig_by_edge[i] = sig

    if not sigs:
        return

    activity = neo4j_repo.get_edge_activity_window(sigs, window_start, window_end)

    for i, e in enumerate(raw_edges):
        sig = sig_by_edge.get(i)
        if not sig:
            continue
        cell = activity.get(sig)
        if cell is None:
            e["call_count_window"] = 0
            e["error_count_window"] = 0
            e["avg_latency_ms_window"] = 0.0
            continue
        spans = cell["span_count"]
        e["call_count_window"] = spans
        e["error_count_window"] = cell["error_count"]
        e["avg_latency_ms_window"] = (
            (cell["total_duration_ns"] / spans / 1_000_000.0) if spans > 0 else 0.0
        )


def _load_endpoint_activity(
    raw_nodes: List[Dict[str, Any]],
    window_start: Optional[str],
    window_end: Optional[str],
) -> Dict[str, Dict[str, float]]:
    endpoint_specs = []
    for node in raw_nodes:
        if node.get("type") != "Endpoint":
            continue
        endpoint_id = node.get("id")
        service_name = node.get("service_name")
        span_name = node.get("name")
        if not (endpoint_id and service_name and span_name):
            continue
        endpoint_specs.append(
            {
                "id": endpoint_id,
                "service_name": str(service_name),
                "endpoint_name": str(span_name),
                "path": str(node.get("path") or ""),
                "method": str(node.get("method") or ""),
            }
        )

    if not endpoint_specs:
        return {}

    return neo4j_repo.get_endpoint_activity_window(endpoint_specs, window_start, window_end)


def _enrich_ownedby_edges_with_endpoint_load(
    raw_edges: List[Dict[str, Any]],
    endpoint_activity: Dict[str, Dict[str, float]],
) -> None:
    if not raw_edges or not endpoint_activity:
        return

    for edge in raw_edges:
        if str(edge.get("type", "")).lower() != "ownedby":
            continue
        endpoint_id = str(edge.get("source_id") or "")
        cell = endpoint_activity.get(endpoint_id)
        if not cell:
            continue
        edge["call_count_window"] = int(cell["call_count"])
        edge["error_count_window"] = int(cell["error_count"])
        edge["avg_latency_ms_window"] = float(cell["latency_p99_ms"])


def _enrich_endpoints_with_window(
    raw_nodes: List[Dict[str, Any]],
    endpoint_activity: Dict[str, Dict[str, float]],
) -> None:
    if not endpoint_activity:
        return

    for node in raw_nodes:
        if node.get("type") != "Endpoint":
            continue
        cell = endpoint_activity.get(str(node.get("id")))
        if not cell:
            node["current_rps"] = 0
            node["error_count_1h"] = 0
            node["latency_p99_ms"] = 0.0
            continue
        node["current_rps"] = cell["call_count"]
        node["error_count_1h"] = int(cell["error_count"])
        node["latency_p99_ms"] = cell["latency_p99_ms"]


def get_subgraph(
    center_id: str,
    depth: int = 2,
    node_types: Optional[List[str]] = None,
    edge_types: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> GraphResponse:
    raw_nodes, raw_edges = neo4j_repo.get_subgraph(
        center_id, depth, node_types, edge_types,
    )
    return _build_response(raw_nodes, raw_edges)


def find_path(source_id: str, target_id: str, max_depth: int = 5,
              user_id: Optional[str] = None) -> GraphResponse:
    raw_nodes, raw_edges = neo4j_repo.find_shortest_path(source_id, target_id, max_depth)
    return _build_response(raw_nodes, raw_edges)


def get_impact(node_id: str, depth: int = 3, direction: str = "downstream",
               user_id: Optional[str] = None) -> GraphResponse:
    raw_nodes, raw_edges = neo4j_repo.get_impact(node_id, depth, direction)
    return _build_response(raw_nodes, raw_edges)


def get_stats(user_id: Optional[str] = None) -> GraphStatsResponse:
    if user_id:
        graph = get_full_graph(limit=5000, user_id=user_id)
        node_types: Dict[str, int] = {}
        edge_types: Dict[str, int] = {}
        for n in graph.nodes:
            node_types[n.type] = node_types.get(n.type, 0) + 1
        for e in graph.edges:
            edge_types[e.type.lower()] = edge_types.get(e.type.lower(), 0) + 1
        return GraphStatsResponse(
            total_nodes=graph.node_count,
            total_edges=graph.edge_count,
            nodes_by_type=node_types,
            edges_by_type=edge_types,
        )
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


def compute_analytics(limit: int = 1000,
                       user_id: Optional[str] = None) -> Dict[str, Any]:
    graph_resp = get_full_graph(limit, user_id=user_id)
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


def get_graph_with_layout(
    limit: int = 500,
    layout: str = "spring",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    graph_resp = get_full_graph(limit, user_id=user_id)
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
