from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.mapper.mapping import MappingConfig


class MappingTemplateSummary(BaseModel):
    id: str = Field(..., description="Stable built-in template identifier")
    name: str = Field(..., description="Human-readable template name")
    description: Optional[str] = Field(default=None)
    source_type: str = Field(..., description="Template family identifier")
    field_mappings_count: int = Field(default=0)
    conditional_rules_count: int = Field(default=0)
    auto_edge_rules_count: int = Field(default=0)


class MappingTemplateListResponse(BaseModel):
    templates: List[MappingTemplateSummary]
    total: int


class MappingTemplateInstantiateRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="Optional name override for the created mapping")
    sample_chunk_id: Optional[str] = Field(default=None, description="Optional chunk to bind as sample")
    activate: bool = Field(default=False, description="Activate mapping immediately after creation")


class MappingTemplateDetail(BaseModel):
    template: MappingConfig
    summary: MappingTemplateSummary
