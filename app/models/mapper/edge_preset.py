from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.mapper.mapping import AutoEdgeRule


class EdgePreset(BaseModel):

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(default=None)
    rules: List[AutoEdgeRule] = Field(
        default_factory=list,
        description="List of automatic edge creation rules",
    )
    is_builtin: bool = Field(default=False, description="Whether this is a built-in preset")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system")


class EdgePresetCreate(BaseModel):

    name: str = Field(..., description="Preset name")
    description: Optional[str] = Field(default=None)
    rules: List[AutoEdgeRule] = Field(default_factory=list)


class EdgePresetUpdate(BaseModel):

    name: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[List[AutoEdgeRule]] = None


class EdgePresetListResponse(BaseModel):

    presets: List[EdgePreset]
    total: int