"""Validation and serialization tests for graph/topology pydantic models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.topology import (
    GraphEdge,
    GraphNode,
    GraphResponse,
    GraphStatsResponse,
    PathRequest,
    SubgraphRequest,
)


def test_graph_node_minimal():
    n = GraphNode(id="x", type="service", name="X")
    assert n.id == "x"
    assert n.properties == {} or n.properties is not None


def test_graph_node_serializable():
    n = GraphNode(id="x", type="db", name="X", properties={"k": 1})
    dumped = n.model_dump()
    assert dumped["id"] == "x"
    assert dumped["properties"]["k"] == 1


def test_graph_edge_minimal():
    e = GraphEdge(source_id="a", target_id="b", type="calls")
    assert e.source_id == "a"
    assert e.target_id == "b"


def test_graph_response_counts():
    g = GraphResponse(
        nodes=[GraphNode(id="x", type="t", name="X")],
        edges=[],
        node_count=1,
        edge_count=0,
    )
    assert g.node_count == 1


def test_graph_stats_response_valid():
    s = GraphStatsResponse(
        total_nodes=10,
        total_edges=5,
        nodes_by_type={"a": 3, "b": 7},
        edges_by_type={"calls": 5},
    )
    assert s.total_nodes == 10
    assert sum(s.nodes_by_type.values()) == s.total_nodes


def test_subgraph_request_defaults():
    r = SubgraphRequest(center_node_id="x")
    assert r.center_node_id == "x"
    assert r.depth >= 1


def test_subgraph_request_rejects_negative_depth():
    with pytest.raises(ValidationError):
        SubgraphRequest(center_node_id="x", depth=-1)


def test_path_request_requires_both_endpoints():
    with pytest.raises(ValidationError):
        PathRequest(source_id="x")  # type: ignore[call-arg]
