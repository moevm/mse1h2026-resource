from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status

from app.models.agent import AgentInfo, AgentRegisterRequest, AgentRegisterResponse
from app.repositories import agent_repo, application_repo

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
    # Validate app_token if provided
    app_id = None
    if body.app_token:
        app = application_repo.get_by_token(body.app_token)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid app_token. Register application first at POST /api/v1/apps/register"
            )
        app_id = app["app_id"]

    data = agent_repo.register_agent(
        name=body.name,
        source_type=body.source_type,
        description=body.description,
        app_id=app_id,
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
                app_id=a.get("app_id"),
                app_name=a.get("app_name"),
            )
        )
    return result