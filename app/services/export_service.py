from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Any, Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

import networkx as nx

from app.models.export import ExportFormat, ExportRequest
from app.models.topology import GraphEdge, GraphNode, GraphResponse
from app.services.graph_service import get_full_graph


log = logging.getLogger(__name__)

def export_graph(request: ExportRequest) -> tuple[bytes, str, str]:
    graph = get_full_graph(request.limit)

    # Apply type filters
    if request.node_types:
        allowed = set(request.node_types)
        graph = _filter_by_node_types(graph, allowed)
    if request.edge_types:
        allowed = set(request.edge_types)
        graph = _filter_by_edge_types(graph, allowed)

    fmt = request.format
    include_props = request.include_properties

    match fmt:
        case ExportFormat.JSON:
            content = _to_json(graph, include_props)
            return content, "application/json", "topology.json"

        case ExportFormat.GRAPHML:
            content = _to_graphml(graph, include_props)
            return content, "application/xml", "topology.graphml"

        case ExportFormat.GEXF:
            content = _to_gexf(graph, include_props)
            return content, "application/xml", "topology.gexf"

        case ExportFormat.DOT:
            content = _to_dot(graph, include_props)
            return content, "text/vnd.graphviz", "topology.dot"

        case ExportFormat.CYTOSCAPE_JSON:
            content = _to_cytoscape_json(graph, include_props, request.layout)
            return content, "application/json", "topology.cyjs"

        case ExportFormat.CSV:
            content = _to_csv_zip(graph, include_props)
            return content, "application/zip", "topology.csv.zip"

        case _:
            raise ValueError(f"Unsupported export format: {fmt}")


def _filter_by_node_types(graph: GraphResponse, types: set[str]) -> GraphResponse:
    nodes = [n for n in graph.nodes if n.type in types]
    node_ids = {n.id for n in nodes}
    edges = [e for e in graph.edges if e.source_id in node_ids and e.target_id in node_ids]
    return GraphResponse(nodes=nodes, edges=edges, node_count=len(nodes), edge_count=len(edges))


def _filter_by_edge_types(graph: GraphResponse, types: set[str]) -> GraphResponse:
    edges = [e for e in graph.edges if e.type in types]
    return GraphResponse(nodes=graph.nodes, edges=edges, node_count=graph.node_count, edge_count=len(edges))


def _to_json(graph: GraphResponse, include_props: bool) -> bytes:
    data = {
        "metadata": {
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "format_version": "1.0",
        },
        "nodes": [_node_dict(n, include_props) for n in graph.nodes],
        "edges": [_edge_dict(e, include_props) for e in graph.edges],
    }
    return json.dumps(data, indent=2, ensure_ascii=False, default=str).encode("utf-8")


def _to_graphml(graph: GraphResponse, include_props: bool) -> bytes:
    G = _to_nx(graph, include_props)
    buf = io.BytesIO()
    nx.write_graphml(G, buf, encoding="utf-8")
    return buf.getvalue()


def _to_gexf(graph: GraphResponse, include_props: bool) -> bytes:
    G = _to_nx(graph, include_props)
    buf = io.BytesIO()
    nx.write_gexf(G, buf, encoding="utf-8")
    return buf.getvalue()



def _to_dot(graph: GraphResponse, include_props: bool) -> bytes:
    lines = ["digraph Topology {", '  rankdir=LR;', '  node [shape=box, style=filled, fontsize=10];', ""]

    colors = {
        "Service": "#3b82f6", "Endpoint": "#8b5cf6", "Deployment": "#06b6d4",
        "Pod": "#14b8a6", "Node": "#64748b", "Database": "#f59e0b",
        "Table": "#d97706", "QueueTopic": "#ec4899", "Cache": "#ef4444",
        "ExternalAPI": "#a855f7", "SecretConfig": "#6366f1", "Library": "#84cc16",
        "TeamOwner": "#22c55e", "SLASLO": "#f97316", "RegionCluster": "#0ea5e9",
    }

    for n in graph.nodes:
        color = colors.get(n.type, "#64748b")
        label = f"{n.name}\\n({n.type})"
        attrs = f'label="{label}", fillcolor="{color}", fontcolor="white"'
        lines.append(f'  "{n.id}" [{attrs}];')

    lines.append("")

    edge_colors = {
        "calls": "#60a5fa", "publishesto": "#f472b6", "consumesfrom": "#e879f9",
        "reads": "#fbbf24", "writes": "#fb923c", "dependson": "#94a3b8",
        "deployedon": "#22d3ee", "ownedby": "#4ade80", "authenticatesvia": "#818cf8",
        "ratelimitedby": "#f87171", "fails_over_to": "#ef4444",
    }

    for e in graph.edges:
        color = edge_colors.get(e.type, "#475569")
        attrs = f'label="{e.type}", color="{color}", fontsize=8'
        lines.append(f'  "{e.source_id}" -> "{e.target_id}" [{attrs}];')

    lines.append("}")
    return "\n".join(lines).encode("utf-8")


def _to_cytoscape_json(graph: GraphResponse, include_props: bool, layout: Optional[str]) -> bytes:
    positions: dict[str, tuple[float, float]] = {}
    if layout:
        G = _to_nx(graph, include_props)
        layout_fns = {
            "spring": nx.spring_layout,
            "circular": nx.circular_layout,
            "shell": nx.shell_layout,
            "kamada_kawai": nx.kamada_kawai_layout,
        }
        fn = layout_fns.get(layout, nx.spring_layout)
        if G.number_of_nodes() > 0:
            positions = {k: (float(v[0]) * 1000, float(v[1]) * 1000) for k, v in fn(G).items()}

    elements: list[dict] = []

    for n in graph.nodes:
        data: dict[str, Any] = {"id": n.id, "label": n.name, "type": n.type, "status": n.status or "active"}
        if include_props:
            data.update(n.properties)
        entry: dict[str, Any] = {"group": "nodes", "data": data}
        if n.id in positions:
            entry["position"] = {"x": positions[n.id][0], "y": positions[n.id][1]}
        elements.append(entry)

    for i, e in enumerate(graph.edges):
        data = {
            "id": f"e-{e.source_id}-{e.target_id}-{e.type}-{i}",
            "source": e.source_id,
            "target": e.target_id,
            "type": e.type,
        }
        if include_props:
            data.update(e.properties)
        elements.append({"group": "edges", "data": data})

    result = {
        "format_version": "1.0",
        "generated_by": "resource-graph-service",
        "elements": elements,
    }
    return json.dumps(result, indent=2, ensure_ascii=False, default=str).encode("utf-8")


def _to_csv_zip(graph: GraphResponse, include_props: bool) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        node_lines = ["id,type,name,status,environment"]
        for n in graph.nodes:
            row = [
                _csv_escape(n.id),
                _csv_escape(n.type),
                _csv_escape(n.name),
                _csv_escape(n.status or ""),
                _csv_escape(n.environment or ""),
            ]
            if include_props:
                row.append(_csv_escape(json.dumps(n.properties, default=str)))
            node_lines.append(",".join(row))
        if include_props:
            node_lines[0] += ",properties"
        zf.writestr("nodes.csv", "\n".join(node_lines))

        edge_lines = ["source_id,target_id,type,status"]
        for e in graph.edges:
            row = [
                _csv_escape(e.source_id),
                _csv_escape(e.target_id),
                _csv_escape(e.type),
                _csv_escape(e.status or ""),
            ]
            if include_props:
                row.append(_csv_escape(json.dumps(e.properties, default=str)))
            edge_lines.append(",".join(row))
        if include_props:
            edge_lines[0] += ",properties"
        zf.writestr("edges.csv", "\n".join(edge_lines))

    return buf.getvalue()


def _to_nx(graph: GraphResponse, include_props: bool) -> nx.DiGraph:
    G = nx.DiGraph()
    for n in graph.nodes:
        attrs: dict[str, Any] = {"type": n.type, "name": n.name, "status": n.status or "active"}
        if include_props:
            for k, v in n.properties.items():
                attrs[k] = str(v) if not isinstance(v, (int, float, bool, str)) else v
        G.add_node(n.id, **attrs)
    for e in graph.edges:
        attrs = {"type": e.type}
        if include_props:
            for k, v in e.properties.items():
                attrs[k] = str(v) if not isinstance(v, (int, float, bool, str)) else v
        G.add_edge(e.source_id, e.target_id, **attrs)
    return G


def _node_dict(n: GraphNode, include_props: bool) -> dict:
    d: dict[str, Any] = {"id": n.id, "type": n.type, "name": n.name, "status": n.status, "environment": n.environment}
    if include_props:
        d["properties"] = n.properties
    return d


def _edge_dict(e: GraphEdge, include_props: bool) -> dict:
    d: dict[str, Any] = {"source_id": e.source_id, "target_id": e.target_id, "type": e.type, "status": e.status}
    if include_props:
        d["properties"] = e.properties
    return d


def _csv_escape(value: str) -> str:
    if "," in value or '"' in value or "\n" in value:
        return '"' + value.replace('"', '""') + '"'
    return value
