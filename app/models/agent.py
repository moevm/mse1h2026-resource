from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AgentRegisterRequest(BaseModel):
    name: str = Field(..., description="Unique agent name (e.g. otel-collector-prod)")
    source_type: str = Field(
        ...,
        description="Type of agent: otel-collector | k8s-agent | aws-agent | mock | custom",
    )
    description: Optional[str] = None


class AgentRegisterResponse(BaseModel):
    agent_id: str
    token: str
    name: str
    source_type: str
    registered_at: datetime


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    source_type: str
    description: Optional[str] = None
    registered_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
