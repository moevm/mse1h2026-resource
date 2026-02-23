"""
FastAPI auth dependency — validates X-Agent-Token header.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import Header, HTTPException, status

from app.repositories import agent_repo


async def require_agent(
    x_agent_token: str = Header(
        ...,
        description="Token issued during agent registration (POST /api/v1/agents/register)",
        alias="X-Agent-Token",
    ),
) -> Dict[str, Any]:
    """
    Dependency that validates the agent token and returns the agent dict.
    Usage:
        @router.post("/topology")
        async def endpoint(agent: dict = Depends(require_agent)):
            ...
    """
    agent = agent_repo.get_by_token(x_agent_token)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked agent token. Register at POST /api/v1/agents/register",
            headers={"WWW-Authenticate": "X-Agent-Token"},
        )
    # Fire-and-forget last_seen update (non-blocking best effort)
    try:
        agent_repo.update_last_seen(x_agent_token)
    except Exception:
        pass
    return agent
