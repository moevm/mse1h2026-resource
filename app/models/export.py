from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    JSON = "json"
    GRAPHML = "graphml"
    GEXF = "gexf"
    DOT = "dot"
    CYTOSCAPE_JSON = "cytoscape_json"
    CSV = "csv"


class ExportRequest(BaseModel):
    format: ExportFormat = Field(ExportFormat.JSON, description="Target format")
    limit: int = Field(500, ge=1, le=10000, description="Max nodes to export")
    node_types: Optional[list[str]] = Field(None, description="Filter by node types")
    edge_types: Optional[list[str]] = Field(None, description="Filter by edge types")
    include_properties: bool = Field(True, description="Include node/edge properties")
    layout: Optional[str] = Field(
        None,
        description="Pre-compute layout positions (spring|circular|shell|kamada_kawai)",
    )


class ExportResponse(BaseModel):
    format: str
    node_count: int
    edge_count: int
    filename: str
    content_type: str
