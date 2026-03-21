from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status

from app.models.application import (
    ApplicationInfo,
    ApplicationDetail,
    ApplicationRegisterRequest,
    ApplicationRegisterResponse,
)
from app.models.agent import AgentInfo
from app.repositories import application_repo

router = APIRouter()


@router.post(
    "/register",
    response_model=ApplicationRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new application",
    description=(
        "Register an application to group agents together. "
        "Returns an app_token that agents can use to bind to this application."
    ),
)
async def register_application(body: ApplicationRegisterRequest) -> ApplicationRegisterResponse:
    data = application_repo.register_application(
        name=body.name,
        description=body.description,
        owner=body.owner,
    )
    return ApplicationRegisterResponse(
        app_id=data["app_id"],
        app_token=data["app_token"],
        name=data["name"],
        description=data.get("description"),
        owner=data.get("owner"),
        created_at=datetime.fromisoformat(data["created_at"]),
    )


@router.get(
    "/",
    response_model=List[ApplicationInfo],
    summary="List all applications",
)
async def list_applications() -> List[ApplicationInfo]:
    apps = application_repo.list_applications()
    result = []
    for app in apps:
        result.append(
            ApplicationInfo(
                app_id=app["app_id"],
                name=app["name"],
                description=app.get("description"),
                owner=app.get("owner"),
                created_at=datetime.fromisoformat(app["created_at"]) if app.get("created_at") else None,
                agent_count=app.get("agent_count", 0),
            )
        )
    return result


@router.get(
    "/{app_id}",
    response_model=ApplicationDetail,
    summary="Get application details with agents",
)
async def get_application(app_id: str) -> ApplicationDetail:
    data = application_repo.get_application_detail(app_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {app_id} not found"
        )

    agents = [
        AgentInfo(
            agent_id=a["agent_id"],
            name=a["name"],
            source_type=a["source_type"],
            description=a.get("description"),
            registered_at=datetime.fromisoformat(a["registered_at"]) if a.get("registered_at") else None,
            last_seen_at=datetime.fromisoformat(a["last_seen_at"]) if a.get("last_seen_at") else None,
            app_id=app_id,
            app_name=data["name"],
        )
        for a in data.get("agents", [])
    ]

    return ApplicationDetail(
        app_id=data["app_id"],
        name=data["name"],
        description=data.get("description"),
        owner=data.get("owner"),
        created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        agent_count=len(agents),
        agents=agents,
    )