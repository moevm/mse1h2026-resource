from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ApplicationRegisterRequest(BaseModel):
    name: str = Field(..., description="Unique application name (e.g. 'e-commerce-platform')")
    description: Optional[str] = None
    owner: Optional[str] = Field(None, description="Team or person responsible for this application")


class ApplicationRegisterResponse(BaseModel):
    app_id: str
    app_token: str
    name: str
    description: Optional[str]
    owner: Optional[str]
    created_at: datetime


class ApplicationInfo(BaseModel):
    app_id: str
    name: str
    description: Optional[str] = None
    owner: Optional[str] = None
    created_at: Optional[datetime] = None
    agent_count: int = 0


class ApplicationDetail(ApplicationInfo):
    agents: List["AgentInfo"] = []


from app.models.agent import AgentInfo
ApplicationDetail.model_rebuild()
