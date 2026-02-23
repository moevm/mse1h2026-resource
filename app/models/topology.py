from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.nodes import AnyNode
from app.models.edges import AnyEdge


class TopologyUpdate(BaseModel):
    source: str = Field(
        ..., description="Agent that produced this update (e.g. otel-collector)"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    nodes: List[AnyNode] = Field(default_factory=list)
    edges: List[AnyEdge] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    type: str
    name: str
    status: Optional[str] = "active"
    environment: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    type: str
    status: Optional[str] = "active"
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    node_count: int
    edge_count: int


class GraphStatsResponse(BaseModel):
    total_nodes: int
    total_edges: int
    nodes_by_type: Dict[str, int]
    edges_by_type: Dict[str, int]


class SubgraphRequest(BaseModel):
    center_node_id: str
    depth: int = Field(2, ge=1, le=5)
    node_types: Optional[List[str]] = None
    edge_types: Optional[List[str]] = None


class PathRequest(BaseModel):
    source_id: str
    target_id: str
    max_depth: int = Field(5, ge=1, le=10)


class ImpactRequest(BaseModel):
    node_id: str
    depth: int = Field(3, ge=1, le=6)
    direction: str = Field("downstream", pattern="^(upstream|downstream|both)$")
