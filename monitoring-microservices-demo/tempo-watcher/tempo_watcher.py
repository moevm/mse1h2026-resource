"""tempo-watcher: pulls assembled traces from Tempo and pushes per-span chunks
to the mse1h2026-resource API.

Unlike otel-watcher (push, per-span, no parent context), this agent waits for
traces to be assembled by Tempo, walks the full parent chain, and writes
``caller_service`` on every span — the receiver uses it to derive authoritative
caller→callee edges from the actual trace topology.
"""
import base64
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tempo-watcher")

RESOURCE_API_URL = os.environ.get("RESOURCE_API_URL", "http://resource-backend:8000")
TEMPO_URL = os.environ.get("TEMPO_URL", "http://tempo:3200")
AGENT_NAME = os.environ.get("AGENT_NAME", "tempo-watcher")
# Source type must match a mapping template; reusing the existing OTel one.
AGENT_SOURCE_TYPE = os.environ.get("AGENT_SOURCE_TYPE", "watcher-otel-traces")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "15"))
# Tempo needs a moment for indexing — start the window LAG_SECONDS in the past.
LAG_SECONDS = int(os.environ.get("LAG_SECONDS", "15"))
MAX_TRACES = int(os.environ.get("MAX_TRACES", "200"))
AGENT_TOKEN = os.environ.get("AGENT_TOKEN")
AGENT_TOKEN_FILE = os.environ.get("AGENT_TOKEN_FILE", "/data/agent.token")
LAST_END_FILE = os.environ.get("LAST_END_FILE", "/data/last_end")

app = FastAPI()


def _load_cached_token() -> Optional[str]:
    try:
        with open(AGENT_TOKEN_FILE, "r", encoding="utf-8") as f:
            t = f.read().strip()
            return t or None
    except OSError:
        return None


def _save_cached_token(tok: str) -> None:
    try:
        d = os.path.dirname(AGENT_TOKEN_FILE)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(AGENT_TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(tok)
    except OSError as e:
        log.warning("token cache write failed: %s", e)


def _load_last_end_ns() -> Optional[int]:
    try:
        with open(LAST_END_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _save_last_end_ns(ts_ns: int) -> None:
    try:
        d = os.path.dirname(LAST_END_FILE)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(LAST_END_FILE, "w", encoding="utf-8") as f:
            f.write(str(int(ts_ns)))
    except OSError:
        pass


def _extract_attr(attrs: List[Dict[str, Any]], key: str) -> Optional[str]:
    """OTLP attribute extraction — same shape as otel-watcher."""
    for a in attrs or []:
        if a.get("key") == key:
            v = a.get("value") or {}
            if "stringValue" in v:
                return v["stringValue"]
            if "intValue" in v:
                return str(v["intValue"])
            if "boolValue" in v:
                return str(v["boolValue"]).lower()
    return None


def _b64_to_hex(s: Optional[str]) -> str:
    if not s:
        return ""
    try:
        return base64.b64decode(s).hex()
    except Exception:
        return ""


def _build_span_chunks(trace: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse a Tempo ``/api/traces/{id}`` response into enriched per-span chunks.

    For each span, walks up the parent chain until the first ancestor in a
    *different* service. That ancestor's service becomes ``caller_service`` —
    the authoritative upstream caller of this span. Internal CLIENT/INTERNAL
    spans of the same service are skipped, so we get clean service→service
    edges regardless of how many in-process spans sit between them.

    Spans whose ancestor chain stays in their own service (or who are roots)
    get ``caller_service=None`` — they're entry points and rely on the
    existing peer.service mapping rules as a fallback.
    """
    spans: Dict[str, Dict[str, Any]] = {}
    for batch in trace.get("batches", []):
        r_attrs = batch.get("resource", {}).get("attributes", [])
        svc = _extract_attr(r_attrs, "service.name")
        meta = {
            "service_name": svc,
            "service_version": _extract_attr(r_attrs, "service.version"),
            "service_environment": _extract_attr(r_attrs, "deployment.environment"),
            "sdk_language": _extract_attr(r_attrs, "telemetry.sdk.language"),
            "sdk_name": _extract_attr(r_attrs, "telemetry.sdk.name"),
        }
        for ss in batch.get("scopeSpans", []):
            for sp in ss.get("spans", []):
                sid = _b64_to_hex(sp.get("spanId"))
                if not sid:
                    continue
                spans[sid] = {
                    "raw": sp,
                    "parent_span_id": _b64_to_hex(sp.get("parentSpanId")),
                    **meta,
                }

    chunks: List[Dict[str, Any]] = []
    for sid, info in spans.items():
        sp = info["raw"]
        attrs = sp.get("attributes", [])

        caller_service: Optional[str] = None
        caller_kind: Optional[str] = None
        psid = info["parent_span_id"]
        seen: set = set()
        while psid and psid in spans and psid not in seen:
            seen.add(psid)
            p = spans[psid]
            if p["service_name"] and p["service_name"] != info["service_name"]:
                caller_service = p["service_name"]
                caller_kind = p["raw"].get("kind")
                break
            psid = p["parent_span_id"]

        chunk = {
            "kind": "span",
            "service_name": info["service_name"],
            "span_name": sp.get("name", ""),
            "span_kind": sp.get("kind"),
            "service_version": info["service_version"],
            "service_environment": info["service_environment"],
            "sdk_language": info["sdk_language"],
            "sdk_name": info["sdk_name"],
            "peer_service": _extract_attr(attrs, "peer.service"),
            "db_system": _extract_attr(attrs, "db.system"),
            "db_name": _extract_attr(attrs, "db.name"),
            "db_table": _extract_attr(attrs, "db.table"),
            "db_statement": _extract_attr(attrs, "db.statement"),
            "http_method": _extract_attr(attrs, "http.method"),
            "http_route": _extract_attr(attrs, "http.route"),
            "http_target": _extract_attr(attrs, "http.target"),
            "http_status_code": _extract_attr(attrs, "http.status_code"),
            "messaging_destination": _extract_attr(attrs, "messaging.destination"),
            "messaging_operation": _extract_attr(attrs, "messaging.operation"),
            "cache_name": _extract_attr(attrs, "cache.name"),
            "external_api": _extract_attr(attrs, "external_api"),
            "auth_secret": _extract_attr(attrs, "auth_secret"),
            "rate_limit_config": _extract_attr(attrs, "rate_limit_config"),
            "failover_service": _extract_attr(attrs, "failover_service"),
            "rpc_service": _extract_attr(attrs, "rpc.service"),
            "rpc_method": _extract_attr(attrs, "rpc.method"),
            "trace_id": _b64_to_hex(sp.get("traceId")),
            "span_id": sid,
            "parent_span_id": info["parent_span_id"] or None,
            "start_time": sp.get("startTimeUnixNano"),
            "end_time": sp.get("endTimeUnixNano"),
            "caller_service": caller_service,
            "caller_span_kind": caller_kind,
        }
        chunks.append(chunk)
    return chunks


def _push_chunk(chunk: Dict[str, Any]) -> None:
    if not AGENT_TOKEN:
        return
    try:
        resp = requests.post(
            f"{RESOURCE_API_URL}/api/v1/receiver/raw",
            data=json.dumps(chunk),
            headers={"X-Agent-Token": AGENT_TOKEN, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 401:
            log.error("AGENT_TOKEN rejected (401)")
            return
        resp.raise_for_status()
    except Exception as e:
        log.warning("push failed: %s", e)


def _search_traces(start_ns: int, end_ns: int) -> List[str]:
    params = {
        "start": int(start_ns // 1_000_000_000),
        "end": int(end_ns // 1_000_000_000),
        "limit": MAX_TRACES,
    }
    resp = requests.get(f"{TEMPO_URL}/api/search", params=params, timeout=15)
    resp.raise_for_status()
    return [t.get("traceID") for t in resp.json().get("traces", []) if t.get("traceID")]


def _fetch_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    resp = requests.get(f"{TEMPO_URL}/api/traces/{trace_id}", timeout=20)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def _poll_once(window_end_ns: int) -> None:
    last = _load_last_end_ns()
    # Bootstrap: scan last 2 minutes on first run so the graph isn't empty
    # while the user waits for fresh traffic.
    window_start_ns = last if last is not None else (window_end_ns - 120 * 1_000_000_000)
    if window_start_ns >= window_end_ns:
        return

    try:
        ids = _search_traces(window_start_ns, window_end_ns)
    except Exception as e:
        log.warning("Tempo search failed: %s", e)
        return

    spans_pushed = 0
    for tid in ids:
        try:
            trace = _fetch_trace(tid)
            if not trace:
                continue
            for chunk in _build_span_chunks(trace):
                _push_chunk(chunk)
                spans_pushed += 1
        except Exception as e:
            log.warning("Trace %s failed: %s", tid, e)

    log.info(
        "Tempo poll window=[%d..%d]: %d traces, %d spans pushed",
        window_start_ns, window_end_ns, len(ids), spans_pushed,
    )
    _save_last_end_ns(window_end_ns)


def _poll_loop() -> None:
    while True:
        try:
            end_ns = int(time.time() * 1_000_000_000) - LAG_SECONDS * 1_000_000_000
            _poll_once(end_ns)
        except Exception as e:
            log.error("poll cycle error: %s", e)
        time.sleep(POLL_INTERVAL)


def _registration_loop() -> None:
    global AGENT_TOKEN

    cached = _load_cached_token()
    if cached:
        AGENT_TOKEN = cached
        log.info("Loaded AGENT_TOKEN from cache file %s", AGENT_TOKEN_FILE)

    while not AGENT_TOKEN:
        try:
            from register import register_agent
            tok = register_agent(AGENT_NAME, AGENT_SOURCE_TYPE)
            AGENT_TOKEN = tok
            _save_cached_token(tok)
            log.info("Auto-registered, token: %s...%s", tok[:8], tok[-4:])
        except Exception as e:
            log.warning("registration failed, retry in 15s: %s", e)
            time.sleep(15)

    # Activate default mappings (idempotent — otel-watcher may have done it).
    try:
        from register import setup_default_mappings
        setup_default_mappings()
    except Exception as e:
        log.warning("setup_default_mappings: %s", e)

    threading.Thread(target=_poll_loop, daemon=True).start()


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "token_set": bool(AGENT_TOKEN)}


@app.on_event("startup")
async def startup() -> None:
    if AGENT_TOKEN:
        log.info("Using pre-set AGENT_TOKEN")
    threading.Thread(target=_registration_loop, daemon=True).start()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8091)
11