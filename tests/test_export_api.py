from __future__ import annotations

import sys
from types import ModuleType

import pytest
from fastapi.responses import Response

from app.models.export import ExportFormat, ExportRequest
from app.models.topology import GraphEdge, GraphNode, GraphResponse


def _load_export_api_with_stubbed_auth(monkeypatch):
    auth_stub = ModuleType("app.api.auth")
    auth_stub.CurrentUser = dict
    monkeypatch.setitem(sys.modules, "app.api.auth", auth_stub)
    sys.modules.pop("app.api.export", None)

    import app.api.export as export_api

    return export_api


SUPPORTED_FORMATS = [
    {
        "id": ExportFormat.JSON.value,
        "name": "JSON",
        "description": "Native topology format with full metadata",
        "extension": ".json",
    },
    {
        "id": ExportFormat.GRAPHML.value,
        "name": "GraphML",
        "description": "XML format compatible with Gephi, yEd, NetworkX",
        "extension": ".graphml",
    },
    {
        "id": ExportFormat.GEXF.value,
        "name": "GEXF",
        "description": "Graph Exchange XML Format — native Gephi format",
        "extension": ".gexf",
    },
    {
        "id": ExportFormat.DOT.value,
        "name": "DOT (Graphviz)",
        "description": "Graphviz DOT language — render with dot/neato/fdp",
        "extension": ".dot",
    },
    {
        "id": ExportFormat.CYTOSCAPE_JSON.value,
        "name": "Cytoscape JSON",
        "description": "Cytoscape.js / Cytoscape Desktop compatible format",
        "extension": ".cyjs",
    },
    {
        "id": ExportFormat.CSV.value,
        "name": "CSV (zipped)",
        "description": "nodes.csv + edges.csv in a ZIP archive",
        "extension": ".csv.zip",
    },
]


def _sample_graph() -> GraphResponse:
    return GraphResponse(
        nodes=[
            GraphNode(id="svc-a", type="service", name="Service A", properties={"region": "eu"}),
            GraphNode(id="db-a", type="database", name="Database A", properties={"engine": "postgres"}),
        ],
        edges=[
            GraphEdge(source_id="svc-a", target_id="db-a", type="reads", properties={"mode": "ro"}),
        ],
        node_count=2,
        edge_count=1,
    )


@pytest.mark.anyio
async def test_list_formats_returns_supported_uc5_formats(monkeypatch):
    export_api = _load_export_api_with_stubbed_auth(monkeypatch)

    formats = await export_api.list_formats(user={"user_id": "user-1"})

    assert formats == SUPPORTED_FORMATS


@pytest.mark.anyio
async def test_export_download_returns_response_with_attachment_headers(monkeypatch):
    export_api = _load_export_api_with_stubbed_auth(monkeypatch)
    captured = {}

    def fake_export_graph(body, user_id=None):
        captured["body"] = body
        captured["user_id"] = user_id
        return b'{"nodes": [], "edges": []}', "application/json", "topology.json"

    monkeypatch.setattr(export_api.export_service, "export_graph", fake_export_graph)

    response = await export_api.export_download(
        user={"user_id": "user-1"},
        body=ExportRequest(format=ExportFormat.JSON, limit=10),
    )

    assert isinstance(response, Response)
    assert response.body == b'{"nodes": [], "edges": []}'
    assert response.media_type == "application/json"
    assert response.headers["content-disposition"] == 'attachment; filename="topology.json"'
    assert captured["body"].format == ExportFormat.JSON
    assert captured["body"].limit == 10
    assert captured["user_id"] == "user-1"


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
@pytest.mark.anyio
async def test_export_download_contract_for_each_supported_format(
    monkeypatch,
    fmt,
    content_type,
    filename,
    marker,
):
    export_api = _load_export_api_with_stubbed_auth(monkeypatch)
    monkeypatch.setattr(export_api.export_service, "get_full_graph", lambda *args, **kwargs: _sample_graph())

    response = await export_api.export_download(
        user={"user_id": "user-1"},
        body=ExportRequest(format=fmt, include_properties=True),
    )

    assert response.status_code == 200
    assert response.media_type == content_type
    assert response.headers["content-disposition"] == f'attachment; filename="{filename}"'
    assert marker in response.body
