from __future__ import annotations

import json
import zipfile
from io import BytesIO

import pytest

from app.models.topology import GraphEdge, GraphNode, GraphResponse
from app.services.export_service import (
    _filter_by_edge_types,
    _filter_by_node_types,
    _to_csv_zip,
    _to_dot,
    _to_gexf,
    _to_graphml,
    _to_json,
)


@pytest.fixture
def sample_graph() -> GraphResponse:
    nodes = [
        GraphNode(id="a", type="service", name="A", properties={"region": "eu"}),
        GraphNode(id="b", type="service", name="B", properties={}),
        GraphNode(id="c", type="database", name="C", properties={}),
    ]
    edges = [
        GraphEdge(source_id="a", target_id="b", type="calls", properties={}),
        GraphEdge(source_id="b", target_id="c", type="reads", properties={}),
        GraphEdge(source_id="a", target_id="c", type="reads", properties={}),
    ]
    return GraphResponse(nodes=nodes, edges=edges, node_count=3, edge_count=3)


def test_filter_by_node_types_keeps_only_allowed(sample_graph):
    out = _filter_by_node_types(sample_graph, {"service"})
    assert {n.id for n in out.nodes} == {"a", "b"}
    assert all(e.source_id in {"a", "b"} and e.target_id in {"a", "b"} for e in out.edges)


def test_filter_by_node_types_empty_set_drops_everything(sample_graph):
    out = _filter_by_node_types(sample_graph, set())
    assert out.node_count == 0
    assert out.edge_count == 0


def test_filter_by_edge_types_keeps_nodes_intact(sample_graph):
    out = _filter_by_edge_types(sample_graph, {"reads"})
    assert {(e.source_id, e.target_id) for e in out.edges} == {("b", "c"), ("a", "c")}
    assert out.node_count == 3  # nodes are unchanged


def test_to_json_includes_all_nodes_and_edges(sample_graph):
    payload = json.loads(_to_json(sample_graph, include_props=True))
    assert {n["id"] for n in payload["nodes"]} == {"a", "b", "c"}
    assert len(payload["edges"]) == 3


def test_to_json_strips_properties_when_disabled(sample_graph):
    payload = json.loads(_to_json(sample_graph, include_props=False))
    for n in payload["nodes"]:
        assert "properties" not in n or not n["properties"]


def test_to_dot_is_well_formed(sample_graph):
    dot = _to_dot(sample_graph, include_props=False).decode()
    assert dot.lstrip().startswith("digraph")
    assert "a" in dot and "b" in dot and "c" in dot


def test_to_graphml_contains_xml_header(sample_graph):
    out = _to_graphml(sample_graph, include_props=True)
    text = out.decode()
    assert "<?xml" in text
    assert "graphml" in text.lower()


def test_to_gexf_contains_xml_header(sample_graph):
    out = _to_gexf(sample_graph, include_props=True)
    text = out.decode()
    assert "<?xml" in text
    assert "gexf" in text.lower()


def test_to_csv_zip_contains_two_files(sample_graph):
    raw = _to_csv_zip(sample_graph, include_props=True)
    with zipfile.ZipFile(BytesIO(raw)) as z:
        names = set(z.namelist())
    assert any(n.endswith("nodes.csv") for n in names)
    assert any(n.endswith("edges.csv") for n in names)
