from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class TraversalStep(BaseModel):
    edge_types: list[str] = Field(
        ...,
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
        "name": "Service → Downstream → Data Stores",
        "description": "Follow calls/dependson from a service to its downstream services, then to databases and caches",
        "start_node_types": ["Service"],
        "steps": [
            {
                "edge_types": ["calls", "dependson"],
                "direction": "outgoing",
                "target_node_types": ["Service", "ExternalAPI"],
                "min_depth": 1,
                "max_depth": 3,
            },
            {
                "edge_types": ["reads", "writes"],
                "direction": "outgoing",
                "target_node_types": ["Database", "Cache", "Table"],
                "min_depth": 1,
                "max_depth": 1,
            },
        ],
        "limit": 200,
    },
    {
        "name": "Topic → Consumers → Downstream",
        "description": "From a Kafka topic, find consumers and their downstream dependencies",
        "start_node_types": ["QueueTopic"],
        "steps": [
            {
                "edge_types": ["consumesfrom"],
                "direction": "incoming",
                "target_node_types": ["Service"],
                "min_depth": 1,
                "max_depth": 1,
            },
            {
                "edge_types": ["calls", "dependson", "writes", "reads"],
                "direction": "outgoing",
                "min_depth": 1,
                "max_depth": 2,
            },
        ],
        "limit": 200,
    },
    {
        "name": "Critical Path: Payments",
        "description": "All resources owned by the Payments team and their dependencies",
        "start_node_types": ["TeamOwner"],
        "steps": [
            {
                "edge_types": ["ownedby"],
                "direction": "incoming",
                "target_node_types": ["Service", "Database"],
                "min_depth": 1,
                "max_depth": 1,
            },
            {
                "edge_types": ["calls", "dependson", "reads", "writes", "publishesto"],
                "direction": "outgoing",
                "min_depth": 1,
                "max_depth": 2,
            },
        ],
        "limit": 300,
    },
    {
        "name": "Infrastructure: Service → Deploy → Cluster",
        "description": "Trace from services through deployments and pods to infrastructure nodes",
        "start_node_types": ["Service"],
        "steps": [
            {
                "edge_types": ["deployedon"],
                "direction": "incoming",
                "target_node_types": ["Deployment"],
                "min_depth": 1,
                "max_depth": 1,
            },
            {
                "edge_types": ["deployedon"],
                "direction": "outgoing",
                "target_node_types": ["RegionCluster", "Node"],
                "min_depth": 1,
                "max_depth": 2,
            },
        ],
        "limit": 200,
    },
    {
        "name": "Security: Auth Chain",
        "description": "Show how services authenticate — secrets, configs, and auth dependencies",
        "start_node_types": ["Service"],
        "steps": [
            {
                "edge_types": ["authenticatesvia"],
                "direction": "outgoing",
                "target_node_types": ["SecretConfig"],
                "min_depth": 1,
                "max_depth": 1,
            },
        ],
        "limit": 100,
    },
    {
        "name": "Full Dependency Tree",
        "description": "Recursive downstream dependency tree from a service, including all resource types",
        "steps": [
            {
                "edge_types": [
                    "calls",
                    "dependson",
                    "reads",
                    "writes",
                    "publishesto",
                    "consumesfrom",
                ],
                "direction": "outgoing",
                "min_depth": 1,
                "max_depth": 5,
            },
        ],
        "limit": 500,
    },
]
