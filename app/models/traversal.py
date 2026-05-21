from __future__ import annotations
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


VALID_TRAVERSAL_EDGE_TYPES = {
    "calls",
    "publishesto",
    "consumesfrom",
    "reads",
    "writes",
    "dependson",
    "deployedon",
    "ownedby",
    "authenticatesvia",
    "ratelimitedby",
    "fails_over_to",
}


class TraversalStep(BaseModel):
    label: Optional[str] = Field(
        None,
        description="Optional display label for this traversal step",
    )
    source_node_types: Optional[list[str]] = Field(
        None,
        description="Filter: only start this step from nodes of these types",
    )
    edge_types: list[str] = Field(
        ...,
        min_length=1,
        description="Edge types to traverse (e.g. ['calls', 'dependson'])",
    )
    direction: str = Field(
        "outgoing",
        pattern="^(outgoing|incoming|any)$",
        description="Traversal direction: outgoing, incoming, or any",
    )
    target_node_types: Optional[list[str]] = Field(
        None,
        description="Filter: only include nodes of these types at this step",
    )
    min_depth: int = Field(1, ge=1, description="Minimum hops for this step")
    max_depth: int = Field(1, ge=1, le=10, description="Maximum hops for this step")

    @field_validator("edge_types")
    @classmethod
    def validate_edge_types(cls, value: list[str]) -> list[str]:
        normalized = [edge_type.lower() for edge_type in value]
        unknown = sorted(set(normalized) - VALID_TRAVERSAL_EDGE_TYPES)
        if unknown:
            raise ValueError(f"Unsupported traversal edge types: {', '.join(unknown)}")
        return normalized

    @model_validator(mode="after")
    def validate_depth_range(self) -> "TraversalStep":
        if self.max_depth < self.min_depth:
            raise ValueError("max_depth must be greater than or equal to min_depth")
        return self


class TraversalRule(BaseModel):
    name: str = Field(..., description="Human-readable rule name")
    description: Optional[str] = Field(None, description="What this rule does")
    start_node_id: Optional[str] = Field(
        None,
        description="Specific starting node ID (URN). If None, uses start_node_types.",
    )
    start_node_types: Optional[list[str]] = Field(
        None,
        description="Start from all nodes of these types (used if start_node_id is None)",
    )
    steps: list[TraversalStep] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Ordered traversal steps",
    )
    limit: int = Field(200, ge=1, le=5000, description="Max nodes in result")


PRESET_RULES: list[dict] = [
    {
        "name": "Service Downstream Calls",
        "description": "Follow direct service calls, external calls, endpoints, and failover targets.",
        "start_node_types": ["Service"],
        "steps": [
            {
                "label": "Runtime calls",
                "source_node_types": ["Service"],
                "edge_types": ["calls", "fails_over_to"],
                "direction": "outgoing",
                "target_node_types": ["Service", "Endpoint", "ExternalAPI"],
                "min_depth": 1,
                "max_depth": 2,
            },
        ],
        "limit": 200,
    },
    {
        "name": "Service Data Access",
        "description": "Show databases, tables, and caches read or written by services.",
        "start_node_types": ["Service"],
        "steps": [
            {
                "label": "Data resources",
                "source_node_types": ["Service"],
                "edge_types": ["reads", "writes", "dependson"],
                "direction": "outgoing",
                "target_node_types": ["Database", "Cache", "Table"],
                "min_depth": 1,
                "max_depth": 1,
            },
        ],
        "limit": 200,
    },
    {
        "name": "Topic Producers And Consumers",
        "description": "Find services and deployments that publish to or consume from topics.",
        "start_node_types": ["QueueTopic"],
        "steps": [
            {
                "label": "Topic participants",
                "source_node_types": ["QueueTopic"],
                "edge_types": ["publishesto", "consumesfrom"],
                "direction": "incoming",
                "target_node_types": ["Service", "Deployment"],
                "min_depth": 1,
                "max_depth": 1,
            },
        ],
        "limit": 200,
    },
    {
        "name": "Topic Consumer Downstream",
        "description": "Start from topics, find consumers, then follow their immediate downstream dependencies.",
        "start_node_types": ["QueueTopic"],
        "steps": [
            {
                "label": "Consumers",
                "source_node_types": ["QueueTopic"],
                "edge_types": ["consumesfrom"],
                "direction": "incoming",
                "target_node_types": ["Service", "Deployment"],
                "min_depth": 1,
                "max_depth": 1,
            },
            {
                "label": "Consumer dependencies",
                "source_node_types": ["Service", "Deployment"],
                "edge_types": ["calls", "reads", "writes", "dependson"],
                "direction": "outgoing",
                "target_node_types": ["Service", "Endpoint", "ExternalAPI", "Database", "Cache", "Table", "Library"],
                "min_depth": 1,
                "max_depth": 1,
            },
        ],
        "limit": 250,
    },
    {
        "name": "Service Runtime Footprint",
        "description": "Trace services to deployments, pods, nodes, and clusters.",
        "start_node_types": ["Service"],
        "steps": [
            {
                "label": "Deployments",
                "source_node_types": ["Service"],
                "edge_types": ["deployedon"],
                "direction": "outgoing",
                "target_node_types": ["Deployment"],
                "min_depth": 1,
                "max_depth": 1,
            },
            {
                "label": "Runtime infrastructure",
                "source_node_types": ["Deployment"],
                "edge_types": ["deployedon"],
                "direction": "any",
                "target_node_types": ["Pod", "Node", "RegionCluster"],
                "min_depth": 1,
                "max_depth": 2,
            },
        ],
        "limit": 250,
    },
    {
        "name": "Ownership Team Assets",
        "description": "Find resources owned by teams.",
        "start_node_types": ["TeamOwner"],
        "steps": [
            {
                "label": "Owned resources",
                "source_node_types": ["TeamOwner"],
                "edge_types": ["ownedby"],
                "direction": "incoming",
                "target_node_types": ["Service", "Deployment", "Database", "Cache", "QueueTopic", "Endpoint", "Table"],
                "min_depth": 1,
                "max_depth": 1,
            },
        ],
        "limit": 300,
    },
    {
        "name": "Security Controls",
        "description": "Show authentication and rate-limit configuration used by runtime resources.",
        "start_node_types": ["Service"],
        "steps": [
            {
                "label": "Security configuration",
                "source_node_types": ["Service", "Deployment", "Pod", "Endpoint"],
                "edge_types": ["authenticatesvia", "ratelimitedby"],
                "direction": "outgoing",
                "target_node_types": ["SecretConfig"],
                "min_depth": 1,
                "max_depth": 1,
            },
        ],
        "limit": 200,
    },
    {
        "name": "Failover Chain",
        "description": "Follow service and deployment failover targets.",
        "start_node_types": ["Service", "Deployment"],
        "steps": [
            {
                "label": "Failover targets",
                "source_node_types": ["Service", "Deployment"],
                "edge_types": ["fails_over_to"],
                "direction": "outgoing",
                "target_node_types": ["Service"],
                "min_depth": 1,
                "max_depth": 2,
            },
        ],
        "limit": 150,
    },
]
