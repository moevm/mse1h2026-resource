from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Query

from app.api.auth import CurrentUser
from app.models.topology import (
    TimelineEventsResponse,
    TimelineRangeResponse,
    SnapshotStatsResponse,
)
from app.repositories import neo4j_repo

router = APIRouter()


@router.get(
    "/range",
    response_model=TimelineRangeResponse,
    summary="Get the time range of graph data",
    description="Returns earliest created_at, latest last_seen_at, and total counts.",
)
async def timeline_range(user: CurrentUser):
    return neo4j_repo.get_timeline_range()


@router.get(
    "/events",
    response_model=TimelineEventsResponse,
    summary="Get time-bucketed graph events",
    description="Returns node/edge appearance events bucketed by time intervals.",
)
async def timeline_events(
    user: CurrentUser,
    bucket_seconds: Annotated[int, Query(ge=5, le=3600)] = 30,
    from_time: Optional[str] = Query(None, description="ISO datetime lower bound"),
    to_time: Optional[str] = Query(None, description="ISO datetime upper bound"),
):
    range_data = neo4j_repo.get_timeline_range()
    events = neo4j_repo.get_timeline_events(bucket_seconds, from_time, to_time)
    return {
        "events": events,
        "min_time": range_data.get("min_time"),
        "max_time": range_data.get("max_time"),
    }


@router.get(
    "/snapshot-stats",
    response_model=SnapshotStatsResponse,
    summary="Get graph stats at a specific point in time",
    description="Returns lightweight node/edge counts at a given timestamp.",
)
async def snapshot_stats(
    user: CurrentUser,
    at_time: str = Query(..., description="ISO datetime — point in time"),
):
    return neo4j_repo.get_snapshot_stats(at_time)
