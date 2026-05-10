"""otel-watcher (Docker): receives OTLP telemetry (traces + logs) and pushes to mse1h2026-resource API.
Accepts both JSON and protobuf OTLP formats.
Auto-registers as an agent on startup.
"""
import base64
import binascii
import gzip
import json
import os
import logging
import threading
import time
from datetime import datetime, date
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("otel-watcher")

RESOURCE_API_URL = os.environ.get("RESOURCE_API_URL", "http://localhost:8000")
AGENT_NAME = os.environ.get("AGENT_NAME", "otel-watcher")
SCRAPE_INTERVAL = int(os.environ.get("SCRAPE_INTERVAL", "30"))
SCRAPE_TARGETS = os.environ.get("SCRAPE_TARGETS", "fastapi-app:8000,flask-app:9464,otel-collector:8889")
AGENT_TOKEN = os.environ.get("AGENT_TOKEN")

app = FastAPI()


class OTLPEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        try:
            return str(obj)
        except Exception:
            return None


def verify_agent_token():
    if not AGENT_TOKEN:
        log.error("No AGENT_TOKEN set.")
        return False
    try:
        resp = requests.post(
            f"{RESOURCE_API_URL}/api/v1/receiver/raw",
            data=json.dumps({"_health_check": True}),
            headers={"X-Agent-Token": AGENT_TOKEN, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 401:
            log.error("AGENT_TOKEN is invalid or revoked.")
            return False
        log.info("AGENT_TOKEN verified successfully")
        return True
    except Exception as e:
        log.warning(f"Could not verify AGENT_TOKEN (API may be starting up): {e}")
        return True


def push_raw(data: dict):
    if not AGENT_TOKEN:
        log.error("No AGENT_TOKEN, cannot push data")
        return
    try:
        serialized = json.dumps(data, cls=OTLPEncoder)
        resp = requests.post(
            f"{RESOURCE_API_URL}/api/v1/receiver/raw",
            data=serialized,
            headers={"X-Agent-Token": AGENT_TOKEN, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 401:
            log.error("AGENT_TOKEN rejected (401).")
            return
        resp.raise_for_status()
        result = resp.json()
        log.info(
            "Pushed raw payload: nodes=%s, edges=%s",
            result.get("nodes_created", 0),
            result.get("edges_created", 0),
        )
    except Exception as e:
        log.error(f"Failed to push raw payload: {e}")


def extract_attr(attrs: List[dict], key: str) -> Optional[str]:
    for attr in attrs:
        if attr.get("key") == key:
            val = attr.get("value", {})
            return val.get("stringValue") or str(val.get("intValue", ""))
    return None


def split_traces_to_spans(body: dict) -> List[dict]:
    resource_spans = body.get("resourceSpans", [])
    if not resource_spans:
        return []

    chunks = []
    for rs in resource_spans:
        resource_attrs = rs.get("resource", {}).get("attributes", [])
        service_name = extract_attr(resource_attrs, "service.name")
        service_version = extract_attr(resource_attrs, "service.version")
        service_env = extract_attr(resource_attrs, "deployment.environment")
        sdk_language = extract_attr(resource_attrs, "telemetry.sdk.language")
        sdk_name = extract_attr(resource_attrs, "telemetry.sdk.name")

        for scope_span in rs.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                span_attrs = span.get("attributes", [])
                # Debug: dump raw attribute keys from every 20th span
                if len(chunks) % 20 == 0:
                    attr_keys = [a.get("key") for a in span_attrs]
                    log.info("RAW_ATTRS svc=%s keys=%s", service_name, attr_keys)
                span_name = span.get("name", "")
                span_kind = span.get("kind")
                peer_service = extract_attr(span_attrs, "peer.service")
                db_system = extract_attr(span_attrs, "db.system")
                db_name = extract_attr(span_attrs, "db.name")
                db_table = extract_attr(span_attrs, "db.table")
                db_statement = extract_attr(span_attrs, "db.statement")
                # HTTP: try both old (v1.24-) and new (v1.27+) semantic conventions
                http_method = extract_attr(span_attrs, "http.method") or extract_attr(span_attrs, "http.request.method")
                http_route = extract_attr(span_attrs, "http.route")
                http_target = extract_attr(span_attrs, "http.target") or extract_attr(span_attrs, "url.path") or extract_attr(span_attrs, "http.url")
                http_status_code = extract_attr(span_attrs, "http.status_code") or extract_attr(span_attrs, "http.response.status_code")
                messaging_dest = extract_attr(span_attrs, "messaging.destination")
                messaging_op = extract_attr(span_attrs, "messaging.operation")
                cache_name = extract_attr(span_attrs, "cache.name")
                external_api = extract_attr(span_attrs, "external_api")
                auth_secret = extract_attr(span_attrs, "auth_secret")
                rate_limit_config = extract_attr(span_attrs, "rate_limit_config")
                failover_service = extract_attr(span_attrs, "failover_service")
                rpc_service = extract_attr(span_attrs, "rpc.service")
                rpc_method = extract_attr(span_attrs, "rpc.method")
                # Network: try both old (net.peer.*) and new (server.*) conventions
                net_peer_name = extract_attr(span_attrs, "net.peer.name") or extract_attr(span_attrs, "server.address")
                net_peer_ip = extract_attr(span_attrs, "net.sock.peer.addr") or extract_attr(span_attrs, "server.socket.address")
                server_address = extract_attr(span_attrs, "server.address")
                db_operation = extract_attr(span_attrs, "db.operation")
                error_type = extract_attr(span_attrs, "error.type")
                http_flavor = extract_attr(span_attrs, "http.flavor") or extract_attr(span_attrs, "network.protocol.version")
                http_user_agent = extract_attr(span_attrs, "http.user_agent") or extract_attr(span_attrs, "user_agent.original")
                net_transport = extract_attr(span_attrs, "net.transport") or extract_attr(span_attrs, "network.transport")

                # Compute the best available peer target for service-to-service calls
                peer_target = peer_service or net_peer_name or server_address or None

                chunk = {
                    "kind": "span",
                    "service_name": service_name,
                    "span_name": span_name,
                    "span_kind": span_kind,
                    "service_version": service_version,
                    "service_environment": service_env,
                    "sdk_language": sdk_language,
                    "sdk_name": sdk_name,
                    "peer_service": peer_service,
                    "peer_target": peer_target,
                    "net_peer_name": net_peer_name,
                    "server_address": server_address,
                    "net_peer_ip": net_peer_ip,
                    "db_system": db_system,
                    "db_name": db_name,
                    "db_table": db_table,
                    "db_statement": db_statement,
                    "db_operation": db_operation,
                    "http_method": http_method,
                    "http_route": http_route,
                    "http_target": http_target,
                    "http_status_code": http_status_code,
                    "http_flavor": http_flavor,
                    "http_user_agent": http_user_agent,
                    "messaging_destination": messaging_dest,
                    "messaging_operation": messaging_op,
                    "cache_name": cache_name,
                    "external_api": external_api,
                    "auth_secret": auth_secret,
                    "rate_limit_config": rate_limit_config,
                    "failover_service": failover_service,
                    "rpc_service": rpc_service,
                    "rpc_method": rpc_method,
                    "error_type": error_type,
                    "net_transport": net_transport,
                    "trace_id": span.get("traceId"),
                    "span_id": span.get("spanId"),
                    "parent_span_id": span.get("parentSpanId"),
                    "start_time": span.get("startTimeUnixNano"),
                    "end_time": span.get("endTimeUnixNano"),
                }
                chunks.append(chunk)

    # Debug: log key fields from each chunk to diagnose missing edges
    for c in chunks:
        pt = c.get("peer_target")
        nm = c.get("http_method") or c.get("http_route") or c.get("http_target")
        if pt or nm:
            log.info("SPAN_DEBUG svc=%s span=%s peer_target=%s http_method=%s http_route=%s "
                     "http_target=%s db=%s kind=%s",
                     c.get("service_name"), c.get("span_name"), pt,
                     c.get("http_method"), c.get("http_route"), c.get("http_target"),
                     c.get("db_system"), c.get("span_kind"))
    return chunks


async def _read_raw_body(request: Request) -> bytes:
    raw_body = await request.body()
    content_encoding = request.headers.get("content-encoding", "")
    if content_encoding == "gzip" or (len(raw_body) >= 2 and raw_body[:2] == b'\x1f\x8b'):
        raw_body = gzip.decompress(raw_body)
    return raw_body


def _is_protobuf(request: Request) -> bool:
    ct = request.headers.get("content-type", "")
    return "protobuf" in ct or (ct and "json" not in ct)


def _fix_bytes_fields(d: dict, keys: list) -> dict:
    for key in keys:
        if key in d:
            try:
                d[key] = binascii.hexlify(base64.b64decode(d[key])).decode()
            except Exception:
                pass
    return d


def _protobuf_traces_to_dict(raw: bytes) -> dict:
    msg = ExportTraceServiceRequest()
    msg.ParseFromString(raw)
    d = MessageToDict(msg)
    for rs in d.get("resourceSpans", []):
        for ss in rs.get("scopeSpans", []):
            for span in ss.get("spans", []):
                _fix_bytes_fields(span, ["traceId", "spanId", "parentSpanId"])
    return d


def _protobuf_logs_to_dict(raw: bytes) -> dict:
    msg = ExportLogsServiceRequest()
    msg.ParseFromString(raw)
    d = MessageToDict(msg)
    for rl in d.get("resourceLogs", []):
        for sl in rl.get("scopeLogs", []):
            for lr in sl.get("logRecords", []):
                _fix_bytes_fields(lr, ["traceId", "spanId"])
    return d


@app.post("/v1/traces")
async def receive_traces(request: Request):
    try:
        raw = await _read_raw_body(request)
        if _is_protobuf(request):
            body = _protobuf_traces_to_dict(raw)
        else:
            body = json.loads(raw)
    except Exception as e:
        log.error(f"Failed to parse traces body: {e}")
        return JSONResponse({"status": "error", "message": f"parse error: {e}"}, status_code=400)

    chunks = split_traces_to_spans(body)
    if not chunks:
        log.warning("Received empty trace payload, skipping")
        return JSONResponse({"status": "ok"})

    log.info(f"Received traces: {len(chunks)} span chunks from {len(body.get('resourceSpans', []))} resources")
    for chunk in chunks:
        push_raw(chunk)

    return JSONResponse({"status": "ok", "chunks_pushed": len(chunks)})


@app.post("/v1/logs")
async def receive_logs(request: Request):
    try:
        raw = await _read_raw_body(request)
        if _is_protobuf(request):
            body = _protobuf_logs_to_dict(raw)
        else:
            body = json.loads(raw)
    except Exception as e:
        log.error(f"Failed to parse logs body: {e}")
        return JSONResponse({"status": "error", "message": f"parse error: {e}"}, status_code=400)

    resource_logs = body.get("resourceLogs", [])
    if not resource_logs:
        log.warning("Received empty logs payload, skipping")
        return JSONResponse({"status": "ok", "message": "empty"})

    total_records = 0
    for rl in resource_logs:
        resource_attrs = rl.get("resource", {}).get("attributes", [])
        service_name = extract_attr(resource_attrs, "service.name")

        for scope_log in rl.get("scopeLogs", []):
            for log_record in scope_log.get("logRecords", []):
                log_attrs = log_record.get("attributes", [])
                severity = log_record.get("severityText") or log_record.get("severityNumber")
                body_text = log_record.get("body", {})
                if isinstance(body_text, dict):
                    body_text = body_text.get("stringValue", str(body_text))
                elif not isinstance(body_text, str):
                    body_text = str(body_text)

                chunk = {
                    "kind": "log",
                    "service_name": service_name,
                    "severity": severity,
                    "body": body_text,
                    "trace_id": log_record.get("traceId"),
                    "span_id": log_record.get("spanId"),
                    "timestamp": log_record.get("timeUnixNano"),
                }
                for key in ("http.method", "http.route", "http.target", "http.status_code",
                            "db.statement", "db.system", "peer.service", "error.type"):
                    val = extract_attr(log_attrs, key)
                    if val:
                        chunk[key.replace(".", "_")] = val

                push_raw(chunk)
                total_records += 1

    log.info(f"Received logs: {total_records} log records from {len(resource_logs)} resources")
    return JSONResponse({"status": "ok", "chunks_pushed": total_records})


def scrape_prometheus_metrics():
    targets = [t.strip() for t in SCRAPE_TARGETS.split(",") if t.strip()]
    for target in targets:
        url = f"http://{target}/metrics"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            metrics = {}
            labels = {
                "job": target.split(":")[0],
                "instance": target,
                "namespace": "monitoring-demo",
                "service": target.split(":")[0],
            }

            for line in resp.text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "{" in line:
                    name_part = line.split("{")[0]
                    label_part = line.split("{")[1].split("}")[0]
                    for lbl in label_part.split(","):
                        if "=" in lbl:
                            k, v = lbl.split("=", 1)
                            v = v.strip('"')
                            if k == "team":
                                labels["team"] = v
                else:
                    name_part = line.split()[0]

                parts = line.split()
                if len(parts) >= 2:
                    try:
                        val = float(parts[-1])
                        metrics[name_part] = val
                    except ValueError:
                        continue

            if metrics:
                payload = {
                    "kind": "metric",
                    "service_name": labels.get("service"),
                    "namespace": labels.get("namespace"),
                    "team": labels.get("team"),
                    "job": labels.get("job"),
                    "instance": labels.get("instance"),
                    "metrics": metrics,
                    "labels": labels,
                    "timestamp": int(time.time()),
                }
                push_raw(payload)

        except Exception as e:
            log.debug(f"Failed to scrape {url}: {e}")


def metrics_loop():
    while True:
        try:
            scrape_prometheus_metrics()
        except Exception as e:
            log.error(f"Metrics scrape cycle failed: {e}")
        time.sleep(SCRAPE_INTERVAL)


def trigger_initial_traces():
    """Send initial requests to services to trigger trace generation for all paths."""
    time.sleep(15)  # wait for app services to be ready

    targets = [
        ("flask-app", 8001, "/users"),   # triggers Flask → FastAPI → DB
        ("flask-app", 8001, "/albums"),   # triggers Flask → Golang
    ]

    for host, port, path in targets:
        url = f"http://{host}:{port}{path}"
        try:
            resp = requests.get(url, timeout=5)
            log.info("Initial trace trigger: %s → %d", url, resp.status_code)
        except Exception as e:
            log.warning("Initial trace trigger failed for %s: %s", url, e)


@app.on_event("startup")
async def startup():
    global AGENT_TOKEN
    if not AGENT_TOKEN:
        from register import register_agent
        try:
            AGENT_TOKEN = register_agent(AGENT_NAME, "watcher-otel-traces")
            log.info("Auto-registered agent, token: %s...%s", AGENT_TOKEN[:8], AGENT_TOKEN[-4:])
        except Exception as e:
            log.error("Auto-registration failed: %s", e)
            return
    else:
        log.info("Using pre-set AGENT_TOKEN=%s...%s", AGENT_TOKEN[:8], AGENT_TOKEN[-4:])

    verify_agent_token()

    from register import setup_default_mappings
    try:
        setup_default_mappings()
    except Exception as e:
        log.warning("Could not activate default mappings: %s", e)

    thread = threading.Thread(target=metrics_loop, daemon=True)
    thread.start()

    trigger_thread = threading.Thread(target=trigger_initial_traces, daemon=True)
    trigger_thread.start()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
