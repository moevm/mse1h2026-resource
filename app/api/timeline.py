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

    if not spans:
        return {"trace_id": trace_id_hex, "hops": []}

    children: Dict[str, List[str]] = {}
    roots: List[str] = []
    for sid, sp in spans.items():
        pid = sp["parent_span_id"]
        if pid and pid in spans:
            children.setdefault(pid, []).append(sid)
        else:
            roots.append(sid)
    for pid in children:
        children[pid].sort(key=lambda s: spans[s]["start"])
    roots.sort(key=lambda s: spans[s]["start"])

    base = min(sp["start"] for sp in spans.values() if sp["start"] > 0) if any(sp["start"] > 0 for sp in spans.values()) else 0
    hops: List[Dict[str, Any]] = []

    def _emit(caller: str, callee: str, kind: str, ts_ns: int, sp: Dict[str, Any]) -> None:
        if not caller or not callee or caller == callee:
            return
        start_ms = max(0, (ts_ns - base) // 1_000_000)
        dur = sp["end"] - sp["start"]
        hops.append({
            "caller_service": caller,
            "callee_service": callee,
            "callee_kind": kind,
            "span_name": sp["span_name"] or "",
            "start_offset_ms": start_ms,
            "duration_ms": dur // 1_000_000 if dur > 0 else 0,
            "is_error": sp["is_error"],
        })

    def visit(sid: str, ancestor_service: Optional[str]) -> None:
        sp = spans[sid]
        svc = sp["service_name"]
        attrs = sp["attrs"]
        has_children = bool(children.get(sid))

        if svc and ancestor_service and svc != ancestor_service:
            _emit(ancestor_service, svc, "Service", sp["start"], sp)

        if sp["kind"] == "SPAN_KIND_SERVER" and svc and sp["span_name"]:
            _emit(svc, sp["span_name"], "Endpoint", sp["end"], sp)

        if sp["kind"] == "SPAN_KIND_CLIENT" and not has_children and svc:
            peer = _extract_attr(attrs, "peer.service")
            if peer and peer != svc:
                _emit(svc, peer, "Service", sp["start"], sp)

        if svc:
            db_system = _extract_attr(attrs, "db.system")
            if db_system:
                db_name = (
                    _extract_attr(attrs, "db.name")
                    or _extract_attr(attrs, "peer.service")
                    or _extract_attr(attrs, "net.peer.name")
                )
                if db_name:
                    _emit(svc, db_name, "Database", sp["start"], sp)
                db_table = _extract_attr(attrs, "db.table")
                if db_table:
                    _emit(svc, db_table, "Table", sp["start"], sp)
            cache_name = _extract_attr(attrs, "cache.name")
            if cache_name:
                _emit(svc, cache_name, "Cache", sp["start"], sp)
            msg_dest = _extract_attr(attrs, "messaging.destination")
            if msg_dest:
                _emit(svc, msg_dest, "QueueTopic", sp["start"], sp)
            external_api = _extract_attr(attrs, "external_api")
            if external_api:
                _emit(svc, external_api, "ExternalAPI", sp["start"], sp)

        new_ancestor = svc if svc else ancestor_service
        for child_id in children.get(sid, []):
            visit(child_id, new_ancestor)

    for root_id in roots:
        visit(root_id, None)

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
    has_errors: Optional[bool] = Query(None, description="If set, filter traces by strict error status"),
    min_duration_ms: Optional[int] = Query(None, ge=0, description="Minimum trace duration in milliseconds"),
    max_duration_ms: Optional[int] = Query(None, ge=0, description="Maximum trace duration in milliseconds"),
):
    import concurrent.futures
    import time as _time
    from datetime import datetime as _dt, timezone as _timezone

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
    allowed_service_list = [s.strip() for s in services.split(",") if s.strip()] if services else None
    allowed_node_list = [s.strip() for s in visible_nodes.split(",") if s.strip()] if visible_nodes else None
    has_errors_filter = has_errors

    neo4j_traces = neo4j_repo.list_trace_summaries(
        window_start or _dt.fromtimestamp(start, tz=_timezone.utc).isoformat(),
        window_end or _dt.fromtimestamp(end, tz=_timezone.utc).isoformat(),
        limit,
        services=allowed_service_list,
        visible_nodes=allowed_node_list,
        multi_hop=multi_hop,
        has_errors=has_errors_filter,
        min_duration_ms=min_duration_ms,
        max_duration_ms=max_duration_ms,
    )
    if neo4j_traces or not TEMPO_URL:
        return {"traces": neo4j_traces, "window_start": start, "window_end": end, "source": "neo4j"}

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
    if allowed_service_list:
        allowed_services = set(allowed_service_list)
        candidates = [c for c in candidates if c.get("rootServiceName") in allowed_services]

    allowed_nodes: Optional[set] = None
    if allowed_node_list:
        allowed_nodes = set(allowed_node_list)

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
        all_callees: set = set()
        for h in hops:
            services_involved.add(h["caller_service"])
            if h.get("callee_kind") == "Service":
                services_involved.add(h["callee_service"])
            all_callees.add(h["callee_service"])
        if multi_hop and len(services_involved) < 2:
            return None
        if allowed_services is not None and services_involved and not services_involved.issubset(allowed_services):
            return None
        if allowed_nodes is not None and all_callees and not all_callees.issubset(allowed_nodes | services_involved):
            return None
        trace_has_errors = any(h.get("is_error") for h in hops)
        if has_errors_filter is not None and has_errors_filter != trace_has_errors:
            return None
        try:
            start_ns = int(c.get("startTimeUnixNano") or 0)
        except (TypeError, ValueError):
            start_ns = 0
        duration_ms = int(c.get("durationMs") or 0)
        if min_duration_ms is not None and duration_ms < min_duration_ms:
            return None
        if max_duration_ms is not None and duration_ms > max_duration_ms:
            return None
        return {
            "trace_id": tid,
            "root_service": c.get("rootServiceName") or "",
            "root_name": c.get("rootTraceName") or "",
            "start_time": _dt.fromtimestamp(start_ns / 1_000_000_000, tz=_timezone.utc).isoformat() if start_ns > 0 else None,
            "duration_ms": duration_ms,
            "span_count": 0,
            "error_count": 1 if trace_has_errors else 0,
            "hop_count": len(hops),
            "service_count": len(services_involved),
            "services_involved": sorted(services_involved),
            "has_errors": trace_has_errors,
        }

    out: List[Dict[str, Any]] = []
    if candidates:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            for res in pool.map(_fetch_and_hops, candidates):
                if res is not None:
                    out.append(res)

    out.sort(key=lambda x: x.get("start_time") or "", reverse=True)
    return {"traces": out, "window_start": start, "window_end": end, "source": "tempo"}


@router.get(
    "/traces/{trace_id}",
    summary="Get a full saved trace with spans and replay hops",
)
async def trace_detail(user: CurrentUser, trace_id: str):
    detail = neo4j_repo.get_trace_detail(trace_id)
    if detail:
        return {**detail, "source": "neo4j"}
    if not TEMPO_URL:
        raise HTTPException(404, "Trace not found")
    try:
        resp = requests.get(f"{TEMPO_URL}/api/traces/{trace_id}", timeout=15)
        if resp.status_code == 404:
            raise HTTPException(404, "Trace not found")
        resp.raise_for_status()
        result = _build_hops_from_trace(resp.json())
        hops = result.get("hops", [])
        services_involved = sorted({
            service
            for hop in hops
            for service in (hop.get("caller_service"), hop.get("callee_service") if hop.get("callee_kind") == "Service" else None)
            if service
        })
        return {
            "trace_id": result.get("trace_id") or trace_id,
            "root_service": services_involved[0] if services_involved else "",
            "root_name": hops[0].get("span_name", "") if hops else "",
            "start_time": None,
            "duration_ms": sum(int(hop.get("duration_ms") or 0) for hop in hops),
            "span_count": 0,
            "error_count": sum(1 for hop in hops if hop.get("is_error")),
            "hop_count": len(hops),
            "service_count": len(services_involved),
            "services_involved": services_involved,
            "has_errors": any(hop.get("is_error") for hop in hops),
            "spans": [],
            "hops": hops,
            "source": "tempo",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Tempo fetch failed: {e}")


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
    import time as _time
    from datetime import datetime as _dt, timezone as _timezone

    now = int(_time.time())
    saved = neo4j_repo.list_trace_summaries(
        _dt.fromtimestamp(now - lookback_seconds, tz=_timezone.utc).isoformat(),
        _dt.fromtimestamp(now, tz=_timezone.utc).isoformat(),
        30,
        multi_hop=True,
    )
    for trace in saved:
        if trace.get("trace_id") == exclude_trace_id:
            continue
        detail = neo4j_repo.get_trace_detail(trace["trace_id"])
        if detail and detail.get("hops"):
            return {"trace_id": detail["trace_id"], "hops": detail["hops"], "source": "neo4j"}

    if not TEMPO_URL:
        return {"trace_id": None, "hops": []}

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
    traces.sort(key=lambda x: int(x.get("startTimeUnixNano") or 0), reverse=True)
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
    "/trace-replay/{trace_id}",
    summary="Replay a specific trace as ordered caller→callee hops",
)
async def trace_replay_by_id(user: CurrentUser, trace_id: str):
    detail = neo4j_repo.get_trace_detail(trace_id)
    if detail:
        return {"trace_id": detail["trace_id"], "hops": detail.get("hops", []), "spans": detail.get("spans", []), "source": "neo4j"}
    if not TEMPO_URL:
        raise HTTPException(404, "Trace not found")
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
