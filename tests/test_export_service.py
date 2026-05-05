from __future__ import annotations

import csv
import json
import zipfile
from io import BytesIO, StringIO
from xml.etree import ElementTree

import pytest

from app.models.export import ExportFormat, ExportRequest
from app.models.topology import GraphEdge, GraphNode, GraphResponse
from app.services import export_service
from app.services.export_service import (
    _filter_by_edge_types,
    _filter_by_node_types,
    _to_csv_zip,
    _to_cytoscape_json,
    _to_dot,
    _to_gexf,
    _to_graphml,
    _to_json,
)


@pytest.fixture
def sample_graph() -> GraphResponse:
    nodes = [
        GraphNode(id="a", type="service", name="A", properties={"region": "eu"}),
        GraphNode(id="b", type="service", name="B", properties={"owner": "team-b"}),
        GraphNode(id="c", type="database", name="C", properties={"tier": 1}),
    ]
    edges = [
        GraphEdge(source_id="a", target_id="b", type="calls", properties={"rps": 25}),
        GraphEdge(source_id="b", target_id="c", type="reads", properties={"mode": "readonly"}),
        GraphEdge(source_id="a", target_id="c", type="reads", properties={}),
    ]
    return GraphResponse(nodes=nodes, edges=edges, node_count=3, edge_count=3)


def test_filter_by_node_types_keeps_only_allowed(sample_graph):
    out = _filter_by_node_types(sample_graph, {"service"})
    assert {n.id for n in out.nodes} == {"a", "b"}
    assert [(e.source_id, e.target_id, e.type) for e in out.edges] == [("a", "b", "calls")]
    assert out.node_count == 2
    assert out.edge_count == 1


def test_filter_by_node_types_empty_set_drops_everything(sample_graph):
    out = _filter_by_node_types(sample_graph, set())
    assert out.node_count == 0
    assert out.edge_count == 0


def test_filter_by_edge_types_keeps_nodes_intact(sample_graph):
    out = _filter_by_edge_types(sample_graph, {"reads"})
    assert {(e.source_id, e.target_id) for e in out.edges} == {("b", "c"), ("a", "c")}
    assert out.node_count == 3
    assert out.edge_count == 2


def test_to_json_includes_all_nodes_edges_and_metadata(sample_graph):
    payload = json.loads(_to_json(sample_graph, include_props=True))
    assert payload["metadata"] == {
        "node_count": 3,
        "edge_count": 3,
        "format_version": "1.0",
    }
    assert {n["id"] for n in payload["nodes"]} == {"a", "b", "c"}
    assert len(payload["edges"]) == 3
    assert payload["nodes"][0]["properties"] == {"region": "eu"}


def test_to_json_strips_properties_when_disabled(sample_graph):
    payload = json.loads(_to_json(sample_graph, include_props=False))
    for node in payload["nodes"]:
        assert "properties" not in node
    for edge in payload["edges"]:
        assert "properties" not in edge


def test_to_dot_is_well_formed(sample_graph):
    dot = _to_dot(sample_graph, include_props=False).decode()
    assert dot.lstrip().startswith("digraph")
    assert dot.rstrip().endswith("}")
    assert "\"a\" -> \"b\"" in dot
    assert "label=\"calls\"" in dot


def test_to_graphml_is_parseable_and_contains_graphml_root(sample_graph):
    out = _to_graphml(sample_graph, include_props=True)
    root = ElementTree.fromstring(out)  # noqa: S314 - parsing trusted exporter output in a unit test
    assert root.tag.endswith("graphml")
    assert b"a" in out and b"b" in out and b"c" in out


def test_to_gexf_is_parseable_and_contains_gexf_root(sample_graph):
    out = _to_gexf(sample_graph, include_props=True)
    root = ElementTree.fromstring(out)  # noqa: S314 - parsing trusted exporter output in a unit test
    assert root.tag.endswith("gexf")
    assert b"a" in out and b"b" in out and b"c" in out


def test_to_cytoscape_json_contains_nodes_edges_and_layout(sample_graph):
    payload = json.loads(_to_cytoscape_json(sample_graph, include_props=True, layout="circular"))
    assert payload["format_version"] == "1.0"
    assert payload["generated_by"] == "resource-graph-service"

    nodes = [element for element in payload["elements"] if element["group"] == "nodes"]
    edges = [element for element in payload["elements"] if element["group"] == "edges"]

    assert {node["data"]["id"] for node in nodes} == {"a", "b", "c"}
    assert {(edge["data"]["source"], edge["data"]["target"]) for edge in edges} == {
        ("a", "b"),
        ("b", "c"),
        ("a", "c"),
    }
    assert all("position" in node for node in nodes)
    assert nodes[0]["data"]["region"] == "eu"


def test_to_cytoscape_json_strips_properties_when_disabled(sample_graph):
    payload = json.loads(_to_cytoscape_json(sample_graph, include_props=False, layout=None))
    nodes = [element for element in payload["elements"] if element["group"] == "nodes"]
    edges = [element for element in payload["elements"] if element["group"] == "edges"]

    assert all("region" not in node["data"] and "owner" not in node["data"] for node in nodes)
    assert all("rps" not in edge["data"] and "mode" not in edge["data"] for edge in edges)


def test_to_csv_zip_contains_nodes_and_edges_csv_with_properties(sample_graph):
    raw = _to_csv_zip(sample_graph, include_props=True)
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        assert set(archive.namelist()) == {"nodes.csv", "edges.csv"}
        node_rows = list(csv.DictReader(StringIO(archive.read("nodes.csv").decode())))
        edge_rows = list(csv.DictReader(StringIO(archive.read("edges.csv").decode())))

    assert node_rows[0]["properties"] == '{"region": "eu"}'
    assert edge_rows[0]["properties"] == '{"rps": 25}'


def test_to_csv_zip_omits_properties_columns_when_disabled(sample_graph):
    raw = _to_csv_zip(sample_graph, include_props=False)
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        node_rows = list(csv.DictReader(StringIO(archive.read("nodes.csv").decode())))
        edge_rows = list(csv.DictReader(StringIO(archive.read("edges.csv").decode())))

    assert "properties" not in node_rows[0]
    assert "properties" not in edge_rows[0]


@pytest.mark.parametrize(
    ("fmt", "content_type", "filename", "marker"),
    [
        (ExportFormat.JSON, "application/json", "topology.json", b'"nodes"'),
        (ExportFormat.GRAPHML, "application/xml", "topology.graphml", b"graphml"),
        (ExportFormat.GEXF, "application/xml", "topology.gexf", b"gexf"),
        (ExportFormat.DOT, "text/vnd.graphviz", "topology.dot", b"digraph"),
        (ExportFormat.CYTOSCAPE_JSON, "application/json", "topology.cyjs", b"elements"),
        (ExportFormat.CSV, "application/zip", "topology.csv.zip", b"PK"),
    ],
)
def test_export_graph_returns_expected_contract_for_supported_formats(
    monkeypatch,
    sample_graph,
    fmt,
    content_type,
    filename,
    marker,
):
    captured_calls = []

    def fake_get_full_graph(limit, user_id=None, exclude_node_types=None, exclude_edge_types=None, filter_mode="ghost"):
        captured_calls.append(
            {
                "limit": limit,
                "user_id": user_id,
                "exclude_node_types": exclude_node_types,
                "exclude_edge_types": exclude_edge_types,
                "filter_mode": filter_mode,
            }
        )
        return sample_graph

    monkeypatch.setattr(export_service, "get_full_graph", fake_get_full_graph)

    content, actual_content_type, actual_filename = export_service.export_graph(
        ExportRequest(
            format=fmt,
            limit=123,
            exclude_node_types=["cache"],
            exclude_edge_types=["writes"],
            filter_mode="exclude",
        ),
        user_id="user-1",
    )

    assert actual_content_type == content_type
    assert actual_filename == filename
    assert marker in content
    assert captured_calls == [
        {
            "limit": 123,
            "user_id": "user-1",
            "exclude_node_types": ["cache"],
            "exclude_edge_types": ["writes"],
            "filter_mode": "exclude",
        }
    ]


def test_export_graph_applies_node_and_edge_type_filters(monkeypatch, sample_graph):
    monkeypatch.setattr(export_service, "get_full_graph", lambda *args, **kwargs: sample_graph)

    content, content_type, filename = export_service.export_graph(
        ExportRequest(format=ExportFormat.JSON, node_types=["service"], edge_types=["calls"]),
    )

    payload = json.loads(content)
    assert content_type == "application/json"
    assert filename == "topology.json"
    assert {node["id"] for node in payload["nodes"]} == {"a", "b"}
    assert [(edge["source_id"], edge["target_id"], edge["type"]) for edge in payload["edges"]] == [
        ("a", "b", "calls"),
    ]
    assert payload["metadata"] == {"node_count": 2, "edge_count": 1, "format_version": "1.0"}
