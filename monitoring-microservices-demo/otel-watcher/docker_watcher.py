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
from datetime import datetime, date, timezone
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
AGENT_TOKEN_FILE = os.environ.get("AGENT_TOKEN_FILE", "/data/agent.token")

app = FastAPI()


def _load_cached_token() -> Optional[str]:
    try:
        with open(AGENT_TOKEN_FILE, "r", encoding="utf-8") as f:
            tok = f.read().strip()
            return tok or None
    except (FileNotFoundError, PermissionError, OSError):
        return None


def _save_cached_token(tok: str) -> None:
    try:
        d = os.path.dirname(AGENT_TOKEN_FILE)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(AGENT_TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(tok)
    except (PermissionError, OSError) as e:
        log.warning("Could not persist AGENT_TOKEN to %s: %s", AGENT_TOKEN_FILE, e)


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
    time.sleep(15)

    targets = [
        ("flask-app", 8001, "/api/v1/users"),
        ("flask-app", 8001, "/api/v1/products"),
        ("flask-app", 8001, "/api/v1/orders"),
        ("flask-app", 8001, "/api/v1/analytics"),
        ("flask-app", 8001, "/api/v1/recommendations"),
        ("flask-app", 8001, "/api/v1/notifications"),
    ]

    for host, port, path in targets:
        url = f"http://{host}:{port}{path}"
        try:
            method = "POST" if "orders" in path or "notifications" in path else "GET"
            resp = requests.request(method, url, timeout=5)
            log.info("Initial trace trigger: %s %s → %d", method, url, resp.status_code)
        except Exception as e:
            log.warning("Initial trace trigger failed for %s: %s", url, e)


def push_infra_topology():
    """Push full infrastructure topology via /api/v1/ingest/topology on startup."""
    time.sleep(5)
    if not AGENT_TOKEN:
        return

    topology = {
        "source": "otel-watcher",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nodes": [
            {"id": "urn:service:flask-app", "type": "Service", "name": "API Gateway (Flask)", "status": "active",
             "properties": {"language": "python", "framework": "flask", "port": 8001, "team": "platform"}},
            {"id": "urn:service:fastapi-app", "type": "Service", "name": "User Service (FastAPI)", "status": "active",
             "properties": {"language": "python", "framework": "fastapi", "port": 8000, "team": "backend"}},
            {"id": "urn:service:golang-app", "type": "Service", "name": "Product Service (Go)", "status": "active",
             "properties": {"language": "go", "framework": "net/http", "port": 8002, "team": "backend"}},
            {"id": "urn:service:otel-collector", "type": "Service", "name": "OTel Collector", "status": "active",
             "properties": {"language": "go", "framework": "otelcol", "version": "0.112.0", "team": "platform"}},
            {"id": "urn:service:otel-watcher", "type": "Service", "name": "Topology Agent (Watcher)", "status": "active",
             "properties": {"language": "python", "framework": "fastapi", "port": 8090, "team": "platform"}},
            {"id": "urn:service:prometheus", "type": "Service", "name": "Prometheus", "status": "active",
             "properties": {"framework": "prometheus", "version": "2.55.0", "port": 9090, "team": "platform"}},
            {"id": "urn:service:grafana", "type": "Service", "name": "Grafana", "status": "active",
             "properties": {"framework": "grafana", "version": "11.3.0", "port": 3000, "team": "platform"}},
            {"id": "urn:service:loki", "type": "Service", "name": "Loki (Logs)", "status": "active",
             "properties": {"framework": "loki", "version": "3.1.0", "port": 3100, "team": "platform"}},
            {"id": "urn:service:tempo", "type": "Service", "name": "Tempo (Traces)", "status": "active",
             "properties": {"framework": "tempo", "version": "2.6.1", "team": "platform"}},
            {"id": "urn:service:jaeger", "type": "Service", "name": "Jaeger (Traces UI)", "status": "active",
             "properties": {"framework": "jaeger", "version": "1.59.0", "port": 16686, "team": "platform"}},
            {"id": "urn:service:beyla", "type": "Service", "name": "Beyla (eBPF Agent)", "status": "active",
             "properties": {"framework": "beyla", "version": "2.5.8", "port": 8999, "team": "platform"}},
            {"id": "urn:service:pyroscope", "type": "Service", "name": "Pyroscope (Profiling)", "status": "active",
             "properties": {"framework": "pyroscope", "version": "1.9.1", "port": 4040, "team": "platform"}},
            {"id": "urn:service:alertmanager", "type": "Service", "name": "Alertmanager", "status": "active",
             "properties": {"framework": "alertmanager", "version": "0.27.0", "port": 9093, "team": "platform"}},
            {"id": "urn:service:karma", "type": "Service", "name": "Karma (Alert UI)", "status": "active",
             "properties": {"framework": "karma", "version": "0.120", "port": 8081, "team": "platform"}},
            {"id": "urn:service:pyrra-api", "type": "Service", "name": "Pyrra SLO API", "status": "active",
             "properties": {"framework": "pyrra", "version": "0.7.7", "port": 9099, "team": "platform"}},
            {"id": "urn:service:pyrra-filesystem", "type": "Service", "name": "Pyrra SLO Rules", "status": "active",
             "properties": {"framework": "pyrra", "version": "0.7.7", "team": "platform"}},
            {"id": "urn:database:postgres-db", "type": "Database", "name": "PostgreSQL", "status": "active",
             "properties": {"engine": "postgresql", "version": "16", "port": 5432, "owner_service": "fastapi-app"}},
            {"id": "urn:cache:redis", "type": "Cache", "name": "Redis", "status": "active",
             "properties": {"engine": "redis", "version": "7", "port": 6379, "owner_service": "fastapi-app"}},
            {"id": "urn:externalapi:stripe.com", "type": "ExternalAPI", "name": "Stripe (Payments)", "status": "active",
             "properties": {"base_url": "https://api.stripe.com"}},
            {"id": "urn:externalapi:analytics.mixpanel.com", "type": "ExternalAPI", "name": "Mixpanel (Analytics)", "status": "active",
             "properties": {"base_url": "https://analytics.mixpanel.com"}},
            {"id": "urn:externalapi:ml.recommendations.internal", "type": "ExternalAPI", "name": "ML Recommendations", "status": "active",
             "properties": {"base_url": "http://ml.recommendations.internal"}},
            {"id": "urn:queuetopic:order-events", "type": "QueueTopic", "name": "order-events", "status": "active",
             "properties": {"protocol": "kafka", "team": "orders"}},
            {"id": "urn:queuetopic:notification-events", "type": "QueueTopic", "name": "notification-events", "status": "active",
             "properties": {"protocol": "kafka", "team": "notifications"}},
            {"id": "urn:slaslo:api-availability", "type": "SLASLO", "name": "API Availability SLO", "status": "active",
             "properties": {"slo_target": "99.9%", "window": "30d", "service_ref": "flask-app"}},
            {"id": "urn:slaslo:db-latency", "type": "SLASLO", "name": "DB Latency SLO", "status": "active",
             "properties": {"slo_target": "p99 < 100ms", "window": "30d", "service_ref": "fastapi-app"}},
        ],
        "edges": [
            # Application layer
            {"source_id": "urn:service:flask-app", "target_id": "urn:service:fastapi-app", "type": "calls",
             "properties": {"protocol": "http"}},
            {"source_id": "urn:service:flask-app", "target_id": "urn:service:golang-app", "type": "calls",
             "properties": {"protocol": "http"}},
            {"source_id": "urn:service:flask-app", "target_id": "urn:externalapi:stripe.com", "type": "calls",
             "properties": {"protocol": "https"}},
            {"source_id": "urn:service:flask-app", "target_id": "urn:externalapi:analytics.mixpanel.com", "type": "calls",
             "properties": {"protocol": "https"}},
            {"source_id": "urn:service:flask-app", "target_id": "urn:externalapi:ml.recommendations.internal", "type": "calls"},
            {"source_id": "urn:service:flask-app", "target_id": "urn:queuetopic:order-events", "type": "publishesto"},
            {"source_id": "urn:service:flask-app", "target_id": "urn:queuetopic:notification-events", "type": "publishesto"},
            {"source_id": "urn:service:fastapi-app", "target_id": "urn:database:postgres-db", "type": "reads"},
            {"source_id": "urn:service:fastapi-app", "target_id": "urn:database:postgres-db", "type": "writes"},
            {"source_id": "urn:service:fastapi-app", "target_id": "urn:cache:redis", "type": "dependson",
             "properties": {"purpose": "caching"}},
            {"source_id": "urn:service:fastapi-app", "target_id": "urn:service:pyroscope", "type": "calls"},

            # Telemetry pipeline
            {"source_id": "urn:service:fastapi-app", "target_id": "urn:service:otel-collector", "type": "calls",
             "properties": {"protocol": "grpc", "purpose": "telemetry"}},
            {"source_id": "urn:service:flask-app", "target_id": "urn:service:otel-collector", "type": "calls",
             "properties": {"protocol": "grpc", "purpose": "telemetry"}},
            {"source_id": "urn:service:beyla", "target_id": "urn:service:otel-collector", "type": "calls",
             "properties": {"protocol": "grpc", "purpose": "traces"}},
            {"source_id": "urn:service:golang-app", "target_id": "urn:service:beyla", "type": "dependson",
             "properties": {"instrumentation": "ebpf"}},
            {"source_id": "urn:service:otel-collector", "target_id": "urn:service:tempo", "type": "calls",
             "properties": {"protocol": "grpc", "purpose": "traces"}},
            {"source_id": "urn:service:otel-collector", "target_id": "urn:service:jaeger", "type": "calls",
             "properties": {"protocol": "grpc", "purpose": "traces"}},
            {"source_id": "urn:service:otel-collector", "target_id": "urn:service:loki", "type": "calls",
             "properties": {"protocol": "http", "purpose": "logs"}},
            {"source_id": "urn:service:otel-collector", "target_id": "urn:service:prometheus", "type": "calls",
             "properties": {"protocol": "http", "purpose": "metrics"}},
            {"source_id": "urn:service:otel-collector", "target_id": "urn:service:otel-watcher", "type": "calls",
             "properties": {"protocol": "http", "purpose": "traces+logs"}},

            # Monitoring layer
            {"source_id": "urn:service:prometheus", "target_id": "urn:service:alertmanager", "type": "calls"},
            {"source_id": "urn:service:alertmanager", "target_id": "urn:service:karma", "type": "calls"},
            {"source_id": "urn:service:prometheus", "target_id": "urn:service:pyrra-api", "type": "calls"},
            {"source_id": "urn:service:pyrra-api", "target_id": "urn:service:pyrra-filesystem", "type": "calls"},

            # Grafana data sources
            {"source_id": "urn:service:grafana", "target_id": "urn:service:prometheus", "type": "reads"},
            {"source_id": "urn:service:grafana", "target_id": "urn:service:loki", "type": "reads"},
            {"source_id": "urn:service:grafana", "target_id": "urn:service:tempo", "type": "reads"},
            {"source_id": "urn:service:grafana", "target_id": "urn:service:pyroscope", "type": "reads"},

            # SLO bindings
            {"source_id": "urn:slaslo:api-availability", "target_id": "urn:service:flask-app", "type": "dependson"},
            {"source_id": "urn:slaslo:db-latency", "target_id": "urn:service:fastapi-app", "type": "dependson"},
        ],
    }

    try:
        resp = requests.post(
            f"{RESOURCE_API_URL}/api/v1/ingest/topology",
            json=topology,
            headers={"X-Agent-Token": AGENT_TOKEN, "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        log.info("Pushed infra topology: %d nodes, %d edges, errors=%s",
                 result.get("nodes_processed", 0), result.get("edges_processed", 0), result.get("errors", []))
    except Exception as e:
        log.error("Failed to push infra topology: %s", e)


def _registration_loop():
    """Acquire AGENT_TOKEN with infinite retry, then bootstrap mappings and
    background workers. Runs in a daemon thread so the OTLP receiver is
    serving immediately and incoming traces are accepted (but dropped) until
    the main API comes up and registration completes.
    """
    global AGENT_TOKEN

    # 1) Try cache first — survives restarts and avoids spawning a new agent
    #    every time the container reboots.
    if not AGENT_TOKEN:
        cached = _load_cached_token()
        if cached:
            AGENT_TOKEN = cached
            log.info("Loaded AGENT_TOKEN from cache file %s", AGENT_TOKEN_FILE)

    # 2) Register against the API with infinite retry.
    while not AGENT_TOKEN:
        try:
            from register import register_agent
            tok = register_agent(AGENT_NAME, "watcher-otel-traces")
            AGENT_TOKEN = tok
            _save_cached_token(tok)
            log.info("Auto-registered agent, token: %s...%s", tok[:8], tok[-4:])
        except Exception as e:
            log.warning("Registration attempt failed, retrying in 15s: %s", e)
            time.sleep(15)

    # 3) Validate. If the cached token is stale (DB wipe etc.), purge and
    #    loop back to step 2 to get a fresh one.
    if not verify_agent_token():
        log.warning("Stored AGENT_TOKEN is invalid — purging cache and re-registering")
        try:
            os.remove(AGENT_TOKEN_FILE)
        except OSError:
            pass
        AGENT_TOKEN = None
        return _registration_loop()

    # 4) Activate default mappings + start background workers.
    try:
        from register import setup_default_mappings
        setup_default_mappings()
    except Exception as e:
        log.warning("Could not activate default mappings: %s", e)

    threading.Thread(target=metrics_loop, daemon=True).start()
    threading.Thread(target=trigger_initial_traces, daemon=True).start()
    threading.Thread(target=push_infra_topology, daemon=True).start()


@app.on_event("startup")
async def startup():
    if AGENT_TOKEN:
        log.info("Using pre-set AGENT_TOKEN=%s...%s", AGENT_TOKEN[:8], AGENT_TOKEN[-4:])
    threading.Thread(target=_registration_loop, daemon=True).start()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
