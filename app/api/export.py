from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.models.export import ExportFormat, ExportRequest
from app.services import export_service

router = APIRouter()


@router.post(
    "/download",
    summary="Export graph data",
    description=(
        "Export the current topology graph in one of the supported formats: "
        "JSON, GraphML, GEXF, DOT (Graphviz), Cytoscape JSON, or CSV (zipped). "
        "Supports filtering by node/edge types and optional layout pre-computation."
    ),
    responses={
        200: {
            "description": "The exported file",
            "content": {
                "application/json": {},
                "application/xml": {},
                "text/vnd.graphviz": {},
                "application/zip": {},
            },
        },
    },
)
async def export_download(body: ExportRequest) -> Response:
    content_bytes, content_type, filename = export_service.export_graph(body)
    return Response(
        content=content_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/formats",
    summary="List available export formats",
    description="Returns all supported export formats with their descriptions.",
)
async def list_formats() -> list[dict]:
    return [
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
