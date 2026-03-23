from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.mapper.transform import TransformType


class FieldMapping(BaseModel):

    id: str = Field(..., description="Unique identifier for this mapping")
    source_path: str = Field(
        ...,
        description="JMESPath expression to extract value from source data",
    )
    target_field: str = Field(
        ...,
        description="Field name in target node/edge",
    )
    target_node_type: str = Field(
        ...,
        description="Which node type this maps to (Service, Database, etc.)",
    )
    transform_type: TransformType = Field(
        default=TransformType.DIRECT,
        description="How to transform the extracted value",
    )
    transform_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Transform-specific configuration",
    )
    is_required: bool = Field(
        default=False,
        description="Whether this field is required for mapping to succeed",
    )
    default_value: Optional[Any] = Field(
        default=None,
        description="Default value if extraction returns None",
    )
    description: Optional[str] = Field(default=None)


class ConditionalRule(BaseModel):

    id: str = Field(..., description="Unique identifier for this rule")
    condition: str = Field(
        ...,
        description="JMESPath boolean expression to evaluate",
    )
    target_node_type: str = Field(
        ...,
        description="Create this node type if condition matches",
    )
    field_mappings: List[str] = Field(
        default_factory=list,
        description="List of FieldMapping IDs to apply when condition matches",
    )
    priority: int = Field(
        default=0,
        description="Higher priority rules are evaluated first",
    )


class AutoEdgeRule(BaseModel):

    id: str = Field(..., description="Unique identifier for this rule")
    source_type: str = Field(
        ...,
        description="Source node type (Pod, Service, etc.)",
    )
    source_field: str = Field(
        ...,
        description="Field in source node to look up for edge creation",
    )
    target_type: str = Field(
        ...,
        description="Target node type (Node, Database, etc.)",
    )
    target_field: str = Field(
        default="name",
        description="Field in target node to match against source_field value",
    )
    edge_type: str = Field(
        ...,
        description="Edge type to create (deployedon, calls, etc.)",
    )


class UnresolvedReference(BaseModel):

    source_node_id: str = Field(..., description="ID of the source node")
    source_node_type: str = Field(..., description="Type of the source node")
    source_field: str = Field(..., description="Field containing the reference")
    expected_target_type: str = Field(..., description="Expected target node type")
    expected_target_value: str = Field(..., description="Value that was not found")
    rule_id: str = Field(..., description="ID of the AutoEdgeRule that created this reference")


class MappingConfig(BaseModel):

    id: str = Field(..., description="Unique identifier (UUID)")
    name: str = Field(..., description="Human-readable name")
    source_type: str = Field(
        ...,
        description="Source type this mapping applies to (matches RawDataSource)",
    )
    version: str = Field(default="1.0.0", description="Semantic version")
    is_active: bool = Field(default=True, description="Whether this mapping is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", description="User or agent that created this")
    description: Optional[str] = Field(default=None)
    sample_chunk_id: Optional[str] = Field(
        default=None,
        description="ID of the raw data chunk used as sample for this mapping",
    )

    field_mappings: List[FieldMapping] = Field(
        default_factory=list,
        description="Field mapping rules",
    )
    conditional_rules: List[ConditionalRule] = Field(
        default_factory=list,
        description="Conditional rules for node type determination",
    )

    edge_source_path: Optional[str] = Field(
        default=None,
        description="JMESPath to find source node ID for edge (legacy)",
    )
    edge_target_path: Optional[str] = Field(
        default=None,
        description="JMESPath to find target node ID for edge (legacy)",
    )
    edge_type_path: Optional[str] = Field(
        default=None,
        description="JMESPath to determine edge type (legacy)",
    )
    edge_type_default: Optional[str] = Field(
        default="dependson",
        description="Default edge type if not found (legacy)",
    )

    auto_edge_rules: List[AutoEdgeRule] = Field(
        default_factory=list,
        description="Rules for automatic edge creation based on node field values",
    )
    edge_preset_id: Optional[str] = Field(
        default="default",
        description="ID of the edge preset to use for automatic edge creation",
    )


class MappingListResponse(BaseModel):

    mappings: List[MappingConfig]
    total: int