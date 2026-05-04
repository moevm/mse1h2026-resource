from __future__ import annotations

from unittest.mock import patch

import pytest

from app.models.topology import GraphEdge, GraphNode, GraphResponse
from app.services import graph_service


@pytest.fixture
def fake_user_graph():
    nodes = [
        GraphNode(id="a", type="service", name="A"),
        GraphNode(id="b", type="service", name="B"),
        GraphNode(id="c", type="database", name="C"),
    ]
    edges = [
        GraphEdge(source_id="a", target_id="b", type="calls"),
        GraphEdge(source_id="b", target_id="c", type="reads"),
    ]
    return GraphResponse(nodes=nodes, edges=edges, node_count=3, edge_count=2)


def test_stats_for_user_aggregates_counts(fake_user_graph):
    with patch.object(graph_service, "get_full_graph", return_value=fake_user_graph):
        stats = graph_service.get_stats(user_id="u1")
    assert stats.total_nodes == 3
    assert stats.total_edges == 2
    assert stats.nodes_by_type == {"service": 2, "database": 1}
    assert stats.edges_by_type == {"calls": 1, "reads": 1}


def test_stats_for_user_with_empty_graph_returns_zeros():
    empty = GraphResponse(nodes=[], edges=[], node_count=0, edge_count=0)
    with patch.object(graph_service, "get_full_graph", return_value=empty):
        stats = graph_service.get_stats(user_id="u1")
    assert stats.total_nodes == 0
    assert stats.total_edges == 0
    assert stats.nodes_by_type == {}
    assert stats.edges_by_type == {}


def test_full_graph_for_user_with_no_agents_returns_empty():
    with patch.object(graph_service.agent_repo, "get_agent_names_for_user", return_value=[]):
        result = graph_service.get_full_graph(limit=100, user_id="lonely-user")
    assert result.node_count == 0
    assert result.edge_count == 0


def test_full_graph_for_user_filters_by_agent_names():
    with patch.object(
        graph_service.agent_repo, "get_agent_names_for_user", return_value=["agent-1", "agent-2"]
    ), patch.object(
        graph_service.neo4j_repo,
        "get_graph_by_sources",
        return_value=([], []),
    ) as mock_repo:
        graph_service.get_full_graph(limit=100, user_id="u1")

    called_args = mock_repo.call_args
    assert called_args.args[0] == ["agent-1", "agent-2"]
