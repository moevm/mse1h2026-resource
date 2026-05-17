from __future__ import annotations

import base64
import os
from typing import Annotated, Any, Dict, List, Optional

import requests
from fastapi import APIRouter, HTTPException, Query

from app.api.auth import CurrentUser
from app.models.topology import (
    TimelineEventsResponse,
    TimelineRangeResponse,
    SnapshotStatsResponse,
    TraceActivityResponse,
)
from app.repositories import neo4j_repo

router = APIRouter()

TEMPO_URL = os.environ.get("TEMPO_URL", "").rstrip("/")


def _extract_attr(attrs: List[Dict[str, Any]], key: str) -> Optional[str]:
    for a in attrs or []:
        if a.get("key") == key:
            v = a.get("value") or {}
            if "stringValue" in v:
                return v["stringValue"]
            if "intValue" in v:
                return str(v["intValue"])
    return None


def _b64_to_hex(s: Optional[str]) -> str:
    if not s:
        return ""
    try:
        return base64.b64decode(s).hex()
    except Exception:
        return ""


def _build_hops_from_trace(trace: Dict[str, Any]) -> Dict[str, Any]:
    spans: Dict[str, Dict[str, Any]] = {}
    trace_id_hex = ""
    for batch in trace.get("batches", []):
        r_attrs = batch.get("resource", {}).get("attributes", [])
        svc = _extract_attr(r_attrs, "service.name")
        for ss in batch.get("scopeSpans", []):
            for sp in ss.get("spans", []):
                sid = _b64_to_hex(sp.get("spanId"))
                if not sid:
                    continue
                if not trace_id_hex:
                    trace_id_hex = _b64_to_hex(sp.get("traceId"))
                try:
                    start = int(sp.get("startTimeUnixNano") or 0)
                    end = int(sp.get("endTimeUnixNano") or 0)
                except (TypeError, ValueError):
                    start = end = 0
                attrs = sp.get("attributes", [])
                status_code = _extract_attr(attrs, "http.status_code")
                is_error = False
                try:
                    if status_code is not None and int(status_code) >= 500:
                        is_error = True
                except (TypeError, ValueError):
                    pass
                spans[sid] = {
                    "span_id": sid,
                    "parent_span_id": _b64_to_hex(sp.get("parentSpanId")),
                    "service_name": svc,
                    "span_name": sp.get("name", ""),
                    "kind": sp.get("kind"),
                    "start": start,
                    "end": end,
                    "is_error": is_error,
                    "attrs": attrs,
                }

    hops: List[Dict[str, Any]] = []
    base = None
    seen_keys: set = set()

    def _add_hop(
        caller: str,
        callee: str,
        callee_kind: str,
        span_name: str,
        start_ns: int,
        end_ns: int,
        is_error: bool,
    ) -> None:
        nonlocal base
        if not caller or not callee or caller == callee:
            return
        key = (caller, callee, callee_kind, start_ns, span_name)
        if key in seen_keys:
            return
        seen_keys.add(key)
        if base is None or start_ns < base:
            base = start_ns
        hops.append({
            "caller_service": caller,
            "callee_service": callee,
            "callee_kind": callee_kind,
            "span_name": span_name,
            "start_offset_ms": start_ns // 1_000_000,
            "duration_ms": (end_ns - start_ns) // 1_000_000 if end_ns > start_ns else 0,
            "is_error": is_error,
        })

    for s in spans.values():
        psid = s["parent_span_id"]
        seen_chain: set = set()
        caller_service = None
        while psid and psid in spans and psid not in seen_chain:
            seen_chain.add(psid)
            p = spans[psid]
            if p["service_name"] and p["service_name"] != s["service_name"]:
                caller_service = p["service_name"]
                break
            psid = p["parent_span_id"]
        if caller_service:
            _add_hop(
                caller_service, s["service_name"], "Service",
                s["span_name"], s["start"], s["end"], s["is_error"],
            )

        attrs = s["attrs"]
        svc = s["service_name"]
        if not svc:
            continue

        db_system = _extract_attr(attrs, "db.system")
        if db_system:
            db_name = _extract_attr(attrs, "db.name") or _extract_attr(attrs, "peer.service") or _extract_attr(attrs, "net.peer.name")
            if db_name:
                _add_hop(svc, db_name, "Database", s["span_name"], s["start"], s["end"], s["is_error"])
            db_table = _extract_attr(attrs, "db.table")
            if db_table:
                _add_hop(svc, db_table, "Table", s["span_name"], s["start"], s["end"], s["is_error"])

        cache_name = _extract_attr(attrs, "cache.name")
        if cache_name:
            _add_hop(svc, cache_name, "Cache", s["span_name"], s["start"], s["end"], s["is_error"])

        msg_dest = _extract_attr(attrs, "messaging.destination")
        if msg_dest:
            _add_hop(svc, msg_dest, "QueueTopic", s["span_name"], s["start"], s["end"], s["is_error"])

        external_api = _extract_attr(attrs, "external_api")
        if external_api:
            _add_hop(svc, external_api, "ExternalAPI", s["span_name"], s["start"], s["end"], s["is_error"])

    if base is not None:
        for h in hops:
            h["start_offset_ms"] = max(0, h["start_offset_ms"] - base // 1_000_000)

    hops.sort(key=lambda h: h["start_offset_ms"])
    return {"trace_id": trace_id_hex, "hops": hops}


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
    "/trace-activity",
    response_model=TraceActivityResponse,
    summary="Get trace activity bucketed by time",
    description="Returns span/error counts per bucket aggregated from :TraceBucket nodes.",
)
async def trace_activity(
    user: CurrentUser,
    bucket_seconds: Annotated[int, Query(ge=5, le=3600)] = 30,
    from_time: Optional[str] = Query(None, description="ISO datetime lower bound"),
    to_time: Optional[str] = Query(None, description="ISO datetime upper bound"),
):
    buckets = neo4j_repo.get_trace_activity(from_time, to_time, bucket_seconds)
    return {"buckets": buckets, "bucket_seconds": bucket_seconds}


@router.get(
    "/traces",
    summary="List trace metadata for the given time window",
    description="Returns Tempo trace summaries enriched with hop_count / service_count by fetching each candidate trace. Optionally filters by visible services and multi-hop only.",
)
async def list_traces(
    user: CurrentUser,
    window_start: Optional[str] = Query(None, description="ISO datetime — start of search window"),
    window_end: Optional[str] = Query(None, description="ISO datetime — end of search window"),
    lookback_seconds: Annotated[int, Query(ge=10, le=86400)] = 600,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    services: Optional[str] = Query(None, description="Comma-separated allow-list of service names; only traces whose hops stay inside this set are returned"),
    visible_nodes: Optional[str] = Query(None, description="Comma-separated allow-list of any visible node names (Service, Database, Cache, etc.). A trace is kept only if every hop's callee is in this set."),
    multi_hop: bool = Query(True, description="If true, drop traces with no cross-service hops"),
):
    if not TEMPO_URL:
        raise HTTPException(503, "Tempo backend not configured (TEMPO_URL env)")

    import concurrent.futures
    import time as _time
    from datetime import datetime as _dt

    def _iso_to_unix(s: Optional[str]) -> Optional[int]:
        if not s:
            return None
        try:
            return int(_dt.fromisoformat(s.replace("Z", "+00:00")).timestamp())
        except Exception:
            return None

    now = int(_time.time())
    end = _iso_to_unix(window_end) or now
    start = _iso_to_unix(window_start) or (end - lookback_seconds)

    try:
        resp = requests.get(
            f"{TEMPO_URL}/api/search",
            params={"start": start, "end": end, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        candidates = resp.json().get("traces", []) or []
    except Exception as e:
        raise HTTPException(502, f"Tempo search failed: {e}")

    candidates = [
        c for c in candidates
        if c.get("traceID")
        and c.get("rootServiceName")
        and not c["rootServiceName"].startswith("<")
    ]

    allowed_services: Optional[set] = None
    if services:
        allowed_services = {s.strip() for s in services.split(",") if s.strip()}
        candidates = [c for c in candidates if c.get("rootServiceName") in allowed_services]

    allowed_nodes: Optional[set] = None
    if visible_nodes:
        allowed_nodes = {s.strip() for s in visible_nodes.split(",") if s.strip()}

    def _fetch_and_hops(c: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        tid = c["traceID"]
        try:
            r = requests.get(f"{TEMPO_URL}/api/traces/{tid}", timeout=15)
            r.raise_for_status()
            trace = r.json()
        except Exception:
            return None
        hops = _build_hops_from_trace(trace).get("hops", [])
        services_involved: set = set()
        callees_by_kind: Dict[str, set] = {}
        for h in hops:
            services_involved.add(h["caller_service"])
            services_involved.add(h["callee_service"])
            callees_by_kind.setdefault(h.get("callee_kind") or "Service", set()).add(h["callee_service"])
        if multi_hop and not hops:
            return None
        only_services = callees_by_kind.get("Service", set())
        only_services |= {h["caller_service"] for h in hops}
        if allowed_services is not None and only_services and not only_services.issubset(allowed_services):
            return None
        if allowed_nodes is not None and services_involved and not services_involved.issubset(allowed_nodes):
            return None
        has_errors = any(h.get("is_error") for h in hops)
        try:
            start_ns = int(c.get("startTimeUnixNano") or 0)
        except (TypeError, ValueError):
            start_ns = 0
        return {
            "trace_id": tid,
            "root_service": c.get("rootServiceName") or "",
            "root_name": c.get("rootTraceName") or "",
            "start_time": _dt.utcfromtimestamp(start_ns / 1_000_000_000).isoformat() + "+00:00" if start_ns > 0 else None,
            "duration_ms": int(c.get("durationMs") or 0),
            "hop_count": len(hops),
            "service_count": len(services_involved),
            "services_involved": sorted(services_involved),
            "has_errors": has_errors,
        }

    out: List[Dict[str, Any]] = []
    if candidates:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            for res in pool.map(_fetch_and_hops, candidates):
                if res is not None:
                    out.append(res)

    out.sort(key=lambda x: x.get("start_time") or "", reverse=True)
    return {"traces": out, "window_start": start, "window_end": end}


@router.get(
    "/trace-replay/{trace_id}",
    summary="Replay a specific trace as ordered caller→callee hops",
)
async def trace_replay_by_id(user: CurrentUser, trace_id: str):
    if not TEMPO_URL:
        raise HTTPException(503, "Tempo backend not configured (TEMPO_URL env)")
    try:
        resp = requests.get(f"{TEMPO_URL}/api/traces/{trace_id}", timeout=15)
        if resp.status_code == 404:
            raise HTTPException(404, "Trace not found in Tempo")
        resp.raise_for_status()
        trace = resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Tempo fetch failed: {e}")
    return _build_hops_from_trace(trace)


@router.get(
    "/trace-replay/latest",
    summary="Fetch the most recent trace as a sequence of caller→callee hops",
    description="Convenience helper for one-click replay; picks any trace with cross-service hops.",
)
async def trace_replay_latest(
    user: CurrentUser,
    lookback_seconds: Annotated[int, Query(ge=10, le=3600)] = 300,
    exclude_trace_id: Optional[str] = Query(None, description="Skip this trace_id"),
):
    if not TEMPO_URL:
        raise HTTPException(503, "Tempo backend not configured (TEMPO_URL env)")
    import time as _time
    now = int(_time.time())
    try:
        resp = requests.get(
            f"{TEMPO_URL}/api/search",
            params={"start": now - lookback_seconds, "end": now, "limit": 30},
            timeout=10,
        )
        resp.raise_for_status()
        traces = resp.json().get("traces", [])
    except Exception as e:
        raise HTTPException(502, f"Tempo search failed: {e}")

    traces = [
        t for t in traces
        if t.get("rootServiceName")
        and not t["rootServiceName"].startswith("<")
        and t.get("traceID") != exclude_trace_id
    ]
    if not traces:
        return {"trace_id": None, "hops": []}
    import random
    random.shuffle(traces)
    for t in traces[:20]:
        tid = t["traceID"]
        try:
            resp = requests.get(f"{TEMPO_URL}/api/traces/{tid}", timeout=15)
            resp.raise_for_status()
            trace = resp.json()
        except Exception:
            continue
        result = _build_hops_from_trace(trace)
        if result["hops"]:
            return result
    return {"trace_id": None, "hops": []}


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
