from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status

from app.models.agent import AgentInfo, AgentRegisterRequest, AgentRegisterResponse
from app.repositories import agent_repo

router = APIRouter()


@router.post(
    "/register",
    response_model=AgentRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new agent and get an auth token",
    description=(
        "Agents (OTel Collector, K8s agent, Terraform agent, mock generators, etc.) "
        "must register here before they can push topology data. "
        "Re-registering with the same name returns the existing token."
    ),
)
async def register_agent(body: AgentRegisterRequest) -> AgentRegisterResponse:
    data = agent_repo.register_agent(
        name=body.name,
        source_type=body.source_type,
        description=body.description,
    )
    return AgentRegisterResponse(
        agent_id=data["agent_id"],
        token=data["token"],
        name=data["name"],
        source_type=data["source_type"],
        registered_at=datetime.fromisoformat(data["registered_at"]),
    )


@router.get(
    "/",
    response_model=List[AgentInfo],
    summary="List all registered agents",
)
async def list_agents() -> List[AgentInfo]:
    agents = agent_repo.list_agents()
    result = []
    for a in agents:
        result.append(
            AgentInfo(
                agent_id=a["agent_id"],
                name=a["name"],
                source_type=a["source_type"],
                description=a.get("description"),
                registered_at=datetime.fromisoformat(a["registered_at"]) if a.get("registered_at") else None,
                last_seen_at=datetime.fromisoformat(a["last_seen_at"]) if a.get("last_seen_at") else None,
            )
        )
    return result
