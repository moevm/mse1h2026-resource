from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from neo4j import ManagedTransaction

from app.repositories.neo4j_connection import neo4j_driver

log = logging.getLogger(__name__)

_NODE_META_KEYS = {"id", "type", "name", "description", "tags",
                   "environment", "status", "created_at", "updated_at"}
_EDGE_META_KEYS = {"source_id", "target_id", "type",
                   "first_seen", "last_seen", "weight", "status"}

_EDGE_LOAD_PROPS = {"call_count", "error_count", "total_duration_ns", "last_call_at"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_none(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _flatten_values(d: Dict[str, Any]) -> Dict[str, Any]:
    """Neo4j only supports primitive property types — convert nested dicts/lists to JSON strings."""
    import json
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v, default=str)
        else:
            out[k] = v
    return out


def upsert_nodes(nodes: List[Dict[str, Any]], source: str) -> int:
    now = _now_iso()
    with neo4j_driver.session() as session:
        count = session.execute_write(_upsert_nodes_tx, nodes, source, now)
    return count


def _upsert_nodes_tx(tx: ManagedTransaction, nodes: List[Dict], source: str, now: str) -> int:
    count = 0
    for raw in nodes:
        data = _strip_none(raw)
        external_id = data["id"]
        node_type = data["type"]
        name = data.get("name", external_id)
        props = _flatten_values({k: v for k, v in data.items() if k not in _NODE_META_KEYS})

        query = (
            "MERGE (r:Resource {external_id: $external_id}) "
            "ON CREATE SET r.created_at = $now "
            "SET r.type = $type, "
            "    r.name = $name, "
            "    r.description = $description, "
            "    r.environment = $environment, "
            "    r.status = $status, "
            "    r.tags = $tags, "
            "    r.updated_at = $now, "
            "    r.last_seen_at = $now, "
            "    r.source = $source, "
            "    r += $props "
            "WITH r CALL apoc.create.addLabels(r, [$type]) YIELD node "
            "RETURN node"
        )

        params = {
            "external_id": external_id,
            "type": node_type,
            "name": name,
            "description": data.get("description"),
            "environment": data.get("environment"),
            "status": data.get("status", "active"),
            "tags": str(data.get("tags")) if data.get("tags") else None,
            "source": source,
            "now": now,
            "props": props,
        }

        try:
            tx.run(query, **params)
            count += 1
        except Exception:
            fallback = (
                "MERGE (r:Resource {external_id: $external_id}) "
                "ON CREATE SET r.created_at = $now "
                "SET r.type = $type, "
                "    r.name = $name, "
                "    r.description = $description, "
                "    r.environment = $environment, "
                "    r.status = $status, "
                "    r.tags = $tags, "
                "    r.updated_at = $now, "
                "    r.last_seen_at = $now, "
                "    r.source = $source, "
                "    r += $props "
                "WITH r SET r:Resource"
            )
            tx.run(fallback, **params)
            count += 1
    return count


TRACE_BUCKET_SECONDS = 10

CALL_LIKE_EDGE_TYPES = {
    "CALLS",
    "READS",
    "WRITES",
    "PUBLISHESTO",
    "CONSUMESFROM",
}


def _bucket_ts_from_iso(when_iso: str) -> Optional[int]:
    from datetime import datetime as _dt
    try:
        dt = _dt.fromisoformat(when_iso.replace("Z", "+00:00"))
        ts_ms = int(dt.timestamp() * 1000)
    except Exception:
        return None
    bucket_ms = TRACE_BUCKET_SECONDS * 1000
    return (ts_ms // bucket_ms) * bucket_ms


def _record_trace_bucket(
    tx: ManagedTransaction,
    when_iso: str,
    is_error: bool,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    now: Optional[str] = None,
) -> None:
    bucket_ts = _bucket_ts_from_iso(when_iso)
    if bucket_ts is None:
        return
    if trace_id and span_id:
        tx.run(
            "MERGE (m:TraceSpanActivity {trace_id: $trace_id, span_id: $span_id, bucket_ts: $bucket_ts}) "
            "ON CREATE SET m.counted = false, m.created_at = $now "
            "WITH m WHERE coalesce(m.counted, false) = false "
            "SET m.counted = true, m.is_error = $is_error, m.updated_at = $now "
            "MERGE (b:TraceBucket {bucket_ts: $bucket_ts}) "
            "ON CREATE SET b.span_count = 0, b.error_count = 0 "
            "SET b.span_count = b.span_count + 1, "
            "    b.error_count = b.error_count + $err_inc",
            trace_id=trace_id,
            span_id=span_id,
            bucket_ts=bucket_ts,
            is_error=is_error,
            err_inc=1 if is_error else 0,
            now=now or _now_iso(),
        )
        return

    tx.run(
        "MERGE (b:TraceBucket {bucket_ts: $bucket_ts}) "
        "ON CREATE SET b.span_count = 0, b.error_count = 0 "
        "SET b.span_count = b.span_count + 1, "
        "    b.error_count = b.error_count + $err_inc",
        bucket_ts=bucket_ts,
        err_inc=1 if is_error else 0,
    )


def _edge_sig(source_id: str, target_id: str, edge_type: str) -> str:
    return f"{source_id}|{target_id}|{edge_type.upper()}"


def _record_edge_activity(
    tx: ManagedTransaction,
    edge_sigs: List[str],
    when_iso: str,
    is_error: bool,
    duration_ns: int,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    now: Optional[str] = None,
) -> None:
    bucket_ts = _bucket_ts_from_iso(when_iso)
    if bucket_ts is None:
        return
    if trace_id and span_id:
        tx.run(
            "UNWIND $sigs AS sig "
            "MERGE (m:EdgeSpanActivity {edge_sig: sig, bucket_ts: $bucket_ts, trace_id: $trace_id, span_id: $span_id}) "
            "ON CREATE SET m.counted = false, m.created_at = $now "
            "WITH m, sig WHERE coalesce(m.counted, false) = false "
            "SET m.counted = true, "
            "    m.is_error = $is_error, "
            "    m.duration_ns = $dur_ns, "
            "    m.updated_at = $now "
            "MERGE (a:EdgeActivity {edge_sig: sig, bucket_ts: $bucket_ts}) "
            "ON CREATE SET a.span_count = 0, a.error_count = 0, a.total_duration_ns = 0 "
            "SET a.span_count = a.span_count + 1, "
            "    a.error_count = a.error_count + $err_inc, "
            "    a.total_duration_ns = a.total_duration_ns + $dur_ns",
            sigs=edge_sigs,
            bucket_ts=bucket_ts,
            trace_id=trace_id,
            span_id=span_id,
            is_error=is_error,
            err_inc=1 if is_error else 0,
            dur_ns=int(duration_ns),
            now=now or _now_iso(),
        )
        return

    tx.run(
        "UNWIND $sigs AS sig "
        "MERGE (a:EdgeActivity {edge_sig: sig, bucket_ts: $bucket_ts}) "
        "ON CREATE SET a.span_count = 0, a.error_count = 0, a.total_duration_ns = 0 "
        "SET a.span_count = a.span_count + 1, "
        "    a.error_count = a.error_count + $err_inc, "
        "    a.total_duration_ns = a.total_duration_ns + $dur_ns",
        sigs=edge_sigs,
        bucket_ts=bucket_ts,
        err_inc=1 if is_error else 0,
        dur_ns=int(duration_ns),
    )


def cleanup_deprecated_nodes() -> Dict[str, int]:
    with neo4j_driver.session() as session:
        return session.execute_write(_cleanup_deprecated_tx)


def _cleanup_deprecated_tx(tx: ManagedTransaction) -> Dict[str, int]:
    lib_rec = tx.run(
        "MATCH (n:Resource) WHERE n.type = 'Library' "
        "RETURN count(n) AS cnt"
    ).single()
    libs = int(lib_rec["cnt"]) if lib_rec else 0
    if libs > 0:
        tx.run("MATCH (n:Resource) WHERE n.type = 'Library' DETACH DELETE n")

    ip_rec = tx.run(
        "MATCH (n:Resource) "
        "WHERE n.name =~ '^[0-9]{1,3}\\\\.[0-9]{1,3}\\\\.[0-9]{1,3}\\\\.[0-9]{1,3}.*' "
        "  OR n.external_id =~ '^urn:[a-z]+:[0-9]{1,3}\\\\.[0-9]{1,3}\\\\.[0-9]{1,3}\\\\.[0-9]{1,3}.*' "
        "RETURN count(n) AS cnt"
    ).single()
    ips = int(ip_rec["cnt"]) if ip_rec else 0
    if ips > 0:
        tx.run(
            "MATCH (n:Resource) "
            "WHERE n.name =~ '^[0-9]{1,3}\\\\.[0-9]{1,3}\\\\.[0-9]{1,3}\\\\.[0-9]{1,3}.*' "
            "  OR n.external_id =~ '^urn:[a-z]+:[0-9]{1,3}\\\\.[0-9]{1,3}\\\\.[0-9]{1,3}\\\\.[0-9]{1,3}.*' "
            "DETACH DELETE n"
        )

    return {"deleted_libraries": libs, "deleted_ip_nodes": ips}


def ensure_activity_indexes() -> None:
    with neo4j_driver.session() as session:
        session.run(
            "CREATE CONSTRAINT trace_id_unique IF NOT EXISTS "
            "FOR (t:Trace) REQUIRE t.trace_id IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT span_trace_span_unique IF NOT EXISTS "
            "FOR (s:Span) REQUIRE (s.trace_id, s.span_id) IS UNIQUE"
        )
        session.run(
            "CREATE INDEX edge_activity_sig_ts IF NOT EXISTS "
            "FOR (a:EdgeActivity) ON (a.edge_sig, a.bucket_ts)"
        )
        session.run(
            "CREATE INDEX trace_bucket_ts IF NOT EXISTS "
            "FOR (b:TraceBucket) ON (b.bucket_ts)"
        )
        session.run(
            "CREATE INDEX span_trace_start_idx IF NOT EXISTS "
            "FOR (s:Span) ON (s.trace_id, s.start_time_ns)"
        )
        session.run(
            "CREATE INDEX span_service_start_idx IF NOT EXISTS "
            "FOR (s:Span) ON (s.service_name, s.start_time_ns)"
        )
        session.run(
            "CREATE INDEX trace_span_activity_ts IF NOT EXISTS "
            "FOR (m:TraceSpanActivity) ON (m.bucket_ts)"
        )
        session.run(
            "CREATE INDEX edge_span_activity_ts IF NOT EXISTS "
            "FOR (m:EdgeSpanActivity) ON (m.bucket_ts)"
        )


def prune_unproduced(
    sources: List[str],
    produced_node_ids: List[str],
    produced_edge_keys: List[str],
) -> Dict[str, int]:
    if not sources:
        return {"deleted_nodes": 0, "deleted_edges": 0}
    with neo4j_driver.session() as session:
        return session.execute_write(
            _prune_unproduced_tx, sources, produced_node_ids, produced_edge_keys,
        )


def _prune_unproduced_tx(
    tx: ManagedTransaction,
    sources: List[str],
    produced_node_ids: List[str],
    produced_edge_keys: List[str],
) -> Dict[str, int]:
    produced_node_set = list(set(produced_node_ids))
    produced_edge_set = list(set(produced_edge_keys))

    edge_count_rec = tx.run(
        "MATCH (a:Resource)-[rel]->(b:Resource) "
        "WHERE rel.source IN $sources "
        "  AND NOT (a.external_id + '|' + b.external_id + '|' + type(rel)) IN $produced "
        "RETURN count(rel) AS cnt",
        sources=sources,
        produced=produced_edge_set,
    ).single()
    deleted_edges = int(edge_count_rec["cnt"]) if edge_count_rec else 0

    if deleted_edges > 0:
        tx.run(
            "MATCH (a:Resource)-[rel]->(b:Resource) "
            "WHERE rel.source IN $sources "
            "  AND NOT (a.external_id + '|' + b.external_id + '|' + type(rel)) IN $produced "
            "DELETE rel",
            sources=sources,
            produced=produced_edge_set,
        )

    node_count_rec = tx.run(
        "MATCH (n:Resource) "
        "WHERE n.source IN $sources "
        "  AND NOT n.external_id IN $produced "
        "RETURN count(n) AS cnt",
        sources=sources,
        produced=produced_node_set,
    ).single()
    deleted_nodes = int(node_count_rec["cnt"]) if node_count_rec else 0

    if deleted_nodes > 0:
        tx.run(
            "MATCH (n:Resource) "
            "WHERE n.source IN $sources "
            "  AND NOT n.external_id IN $produced "
            "DETACH DELETE n",
            sources=sources,
            produced=produced_node_set,
        )

    return {"deleted_nodes": deleted_nodes, "deleted_edges": deleted_edges}


def cleanup_activity_older_than(cutoff_ms: int) -> Dict[str, int]:
    with neo4j_driver.session() as session:
        return session.execute_write(_cleanup_activity_tx, cutoff_ms)


def _cleanup_activity_tx(tx: ManagedTransaction, cutoff_ms: int) -> Dict[str, int]:
    r1 = tx.run(
        "MATCH (a:EdgeActivity) WHERE a.bucket_ts < $cutoff DETACH DELETE a RETURN count(*) AS c",
        cutoff=cutoff_ms,
    ).single()
    r2 = tx.run(
        "MATCH (b:TraceBucket) WHERE b.bucket_ts < $cutoff DETACH DELETE b RETURN count(*) AS c",
        cutoff=cutoff_ms,
    ).single()
    r3 = tx.run(
        "MATCH (m:TraceSpanActivity) WHERE m.bucket_ts < $cutoff DETACH DELETE m RETURN count(*) AS c",
        cutoff=cutoff_ms,
    ).single()
    r4 = tx.run(
        "MATCH (m:EdgeSpanActivity) WHERE m.bucket_ts < $cutoff DETACH DELETE m RETURN count(*) AS c",
        cutoff=cutoff_ms,
    ).single()
    return {
        "edge_activity_deleted": int(r1["c"]) if r1 else 0,
        "trace_buckets_deleted": int(r2["c"]) if r2 else 0,
        "trace_span_activity_deleted": int(r3["c"]) if r3 else 0,
        "edge_span_activity_deleted": int(r4["c"]) if r4 else 0,
    }


def delete_edge(source_id: str, target_id: str, edge_type: str) -> int:
    with neo4j_driver.session() as session:
        return session.execute_write(_delete_edge_tx, source_id, target_id, edge_type)


def _delete_edge_tx(
    tx: ManagedTransaction,
    source_id: str,
    target_id: str,
    edge_type: str,
) -> int:
    rec = tx.run(
        "MATCH (a:Resource {external_id: $source_id})-[rel]->(b:Resource {external_id: $target_id}) "
        "WHERE type(rel) = $edge_type "
        "WITH collect(rel) AS rels "
        "FOREACH (rel IN rels | DELETE rel) "
        "RETURN size(rels) AS deleted_count",
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type.upper(),
    ).single()
    return int(rec["deleted_count"] or 0) if rec else 0


def upsert_trace_span(span: Dict[str, Any], source: str) -> Dict[str, Any]:
    now = _now_iso()
    with neo4j_driver.session() as session:
        return session.execute_write(_upsert_trace_span_tx, span, source, now)


def _upsert_trace_span_tx(
    tx: ManagedTransaction,
    span: Dict[str, Any],
    source: str,
    now: str,
) -> Dict[str, Any]:
    trace_id = span.get("trace_id")
    span_id = span.get("span_id")
    if not trace_id or not span_id:
        return {"stored": False, "reason": "missing trace_id/span_id"}

    error = span.get("error") or {}
    attributes = _flatten_values({"attributes": span.get("attributes") or {}})["attributes"]
    service_name = span.get("service_name")
    service_id = f"urn:service:{service_name}" if service_name else None

    params = {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": span.get("parent_span_id"),
        "service_name": service_name,
        "span_name": span.get("span_name") or "",
        "operation_name": span.get("operation_name") or span.get("span_name") or "",
        "span_kind": span.get("span_kind"),
        "caller_service": span.get("caller_service"),
        "caller_span_kind": span.get("caller_span_kind"),
        "start_time_ns": int(span.get("start_time_ns") or 0),
        "end_time_ns": int(span.get("end_time_ns") or 0),
        "duration_ns": int(span.get("duration_ns") or 0),
        "timestamp": span.get("timestamp"),
        "http_method": span.get("http_method"),
        "http_route": span.get("http_route"),
        "http_target": span.get("http_target"),
        "http_status_code": span.get("http_status_code"),
        "db_system": span.get("db_system"),
        "db_name": span.get("db_name"),
        "db_table": span.get("db_table"),
        "db_operation": span.get("db_operation"),
        "messaging_destination": span.get("messaging_destination"),
        "messaging_operation": span.get("messaging_operation"),
        "rpc_service": span.get("rpc_service"),
        "rpc_method": span.get("rpc_method"),
        "peer_service": span.get("peer_service"),
        "is_error": bool(error.get("is_error")),
        "error_kind": error.get("kind"),
        "error_message": error.get("message"),
        "attributes": attributes,
        "service_id": service_id,
        "source": source,
        "now": now,
    }

    rec = tx.run(
        "MERGE (t:Trace {trace_id: $trace_id}) "
        "ON CREATE SET t.created_at = $now, t.first_seen_at = coalesce($timestamp, $now) "
        "SET t.updated_at = $now, t.last_seen_at = coalesce($timestamp, $now), t.source = $source "
        "MERGE (s:Span {trace_id: $trace_id, span_id: $span_id}) "
        "ON CREATE SET s.created_at = $now "
        "SET s.parent_span_id = $parent_span_id, "
        "    s.service_name = $service_name, "
        "    s.span_name = $span_name, "
        "    s.operation_name = $operation_name, "
        "    s.span_kind = $span_kind, "
        "    s.caller_service = $caller_service, "
        "    s.caller_span_kind = $caller_span_kind, "
        "    s.start_time_ns = $start_time_ns, "
        "    s.end_time_ns = $end_time_ns, "
        "    s.duration_ns = $duration_ns, "
        "    s.timestamp = $timestamp, "
        "    s.http_method = $http_method, "
        "    s.http_route = $http_route, "
        "    s.http_target = $http_target, "
        "    s.http_status_code = $http_status_code, "
        "    s.db_system = $db_system, "
        "    s.db_name = $db_name, "
        "    s.db_table = $db_table, "
        "    s.db_operation = $db_operation, "
        "    s.messaging_destination = $messaging_destination, "
        "    s.messaging_operation = $messaging_operation, "
        "    s.rpc_service = $rpc_service, "
        "    s.rpc_method = $rpc_method, "
        "    s.peer_service = $peer_service, "
        "    s.is_error = $is_error, "
        "    s.error_kind = $error_kind, "
        "    s.error_message = $error_message, "
        "    s.attributes = $attributes, "
        "    s.source = $source, "
        "    s.updated_at = $now "
        "MERGE (t)-[:TRACE_HAS_SPAN]->(s) "
        "WITH t, s "
        "OPTIONAL MATCH (p:Span {trace_id: $trace_id, span_id: $parent_span_id}) "
        "FOREACH (_ IN CASE WHEN p IS NULL THEN [] ELSE [1] END | MERGE (p)-[:SPAN_PARENT]->(s)) "
        "WITH t, s "
        "OPTIONAL MATCH (child:Span {trace_id: $trace_id, parent_span_id: $span_id}) "
        "FOREACH (_ IN CASE WHEN child IS NULL THEN [] ELSE [1] END | MERGE (s)-[:SPAN_PARENT]->(child)) "
        "WITH t, s "
        "OPTIONAL MATCH (svc:Resource {external_id: $service_id}) "
        "FOREACH (_ IN CASE WHEN svc IS NULL THEN [] ELSE [1] END | MERGE (s)-[:SPAN_OF_SERVICE]->(svc)) "
        "WITH t "
        "MATCH (t)-[:TRACE_HAS_SPAN]->(all_spans:Span) "
        "WITH t, count(all_spans) AS span_count, "
        "     sum(CASE WHEN coalesce(all_spans.is_error, false) THEN 1 ELSE 0 END) AS error_count, "
        "     min(all_spans.start_time_ns) AS min_start, "
        "     max(all_spans.end_time_ns) AS max_end, "
        "     collect(DISTINCT all_spans.service_name) AS services "
        "SET t.span_count = span_count, "
        "    t.error_count = error_count, "
        "    t.duration_ns = CASE WHEN max_end > min_start THEN max_end - min_start ELSE 0 END, "
        "    t.services = [svc IN services WHERE svc IS NOT NULL] "
        "RETURN span_count, error_count",
        **params,
    ).single()

    return {
        "stored": True,
        "trace_id": trace_id,
        "span_id": span_id,
        "trace_span_count": int(rec["span_count"] or 0) if rec else 0,
        "trace_error_count": int(rec["error_count"] or 0) if rec else 0,
    }


def get_trace_detail(trace_id: str) -> Optional[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(_read_trace_detail_tx, trace_id)


def list_trace_summaries(
    window_start: Optional[str],
    window_end: Optional[str],
    limit: int,
    services: Optional[List[str]] = None,
    visible_nodes: Optional[List[str]] = None,
    multi_hop: bool = True,
    has_errors: Optional[bool] = None,
    min_duration_ms: Optional[int] = None,
    max_duration_ms: Optional[int] = None,
) -> List[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(
            _read_trace_summaries_tx,
            window_start,
            window_end,
            limit,
            services,
            visible_nodes,
            multi_hop,
            has_errors,
            min_duration_ms,
            max_duration_ms,
        )


def _read_trace_detail_tx(tx: ManagedTransaction, trace_id: str) -> Optional[Dict[str, Any]]:
    from app.services.trace_service import build_hops_from_spans, summarize_trace

    result = tx.run(
        "MATCH (t:Trace {trace_id: $trace_id})-[:TRACE_HAS_SPAN]->(s:Span) "
        "RETURN t.trace_id AS trace_id, collect(properties(s)) AS spans",
        trace_id=trace_id,
    ).single()
    if not result:
        return None

    spans = [_span_props_to_dict(props) for props in result["spans"]]
    spans.sort(key=lambda sp: int(sp.get("start_time_ns") or 0))
    summary = summarize_trace(result["trace_id"], spans)
    return {
        **summary,
        "spans": spans,
        "hops": build_hops_from_spans(spans),
    }


def _read_trace_summaries_tx(
    tx: ManagedTransaction,
    window_start: Optional[str],
    window_end: Optional[str],
    limit: int,
    services: Optional[List[str]],
    visible_nodes: Optional[List[str]],
    multi_hop: bool,
    has_errors: Optional[bool],
    min_duration_ms: Optional[int],
    max_duration_ms: Optional[int],
) -> List[Dict[str, Any]]:
    from app.services.trace_service import build_hops_from_spans, summarize_trace

    from_ns = _iso_to_ns(window_start)
    to_ns = _iso_to_ns(window_end)
    conditions = ["s.start_time_ns > 0"]
    params: Dict[str, Any] = {"limit": max(1, min(limit * 8, 1000))}
    if from_ns is not None:
        conditions.append("s.start_time_ns >= $from_ns")
        params["from_ns"] = from_ns
    if to_ns is not None:
        conditions.append("s.start_time_ns < $to_ns")
        params["to_ns"] = to_ns

    where = " WHERE " + " AND ".join(conditions)
    records = tx.run(
        "MATCH (t:Trace)-[:TRACE_HAS_SPAN]->(s:Span) "
        f"{where} "
        "WITH t, collect(properties(s)) AS spans, max(s.start_time_ns) AS newest_span "
        "RETURN t.trace_id AS trace_id, spans "
        "ORDER BY newest_span DESC LIMIT $limit",
        **params,
    )

    allowed_services = set(services or []) or None
    allowed_nodes = set(visible_nodes or []) or None
    out: List[Dict[str, Any]] = []
    for record in records:
        spans = [_span_props_to_dict(props) for props in record["spans"]]
        spans.sort(key=lambda sp: int(sp.get("start_time_ns") or 0))
        summary = summarize_trace(record["trace_id"], spans)
        hops = build_hops_from_spans(spans)
        services_involved = set(summary.get("services_involved") or [])
        all_callees = {h.get("callee_service") for h in hops if h.get("callee_service")}

        if multi_hop and summary.get("service_count", 0) < 2:
            continue
        if allowed_services is not None and services_involved and not services_involved.issubset(allowed_services):
            continue
        if allowed_nodes is not None and all_callees and not all_callees.issubset(allowed_nodes | services_involved):
            continue
        if has_errors is not None and bool(summary.get("has_errors")) != has_errors:
            continue
        if min_duration_ms is not None and int(summary.get("duration_ms") or 0) < min_duration_ms:
            continue
        if max_duration_ms is not None and int(summary.get("duration_ms") or 0) > max_duration_ms:
            continue

        out.append(summary)
        if len(out) >= limit:
            break
    return out


def _span_props_to_dict(props: Dict[str, Any]) -> Dict[str, Any]:
    import json

    out = dict(props)
    attrs = out.get("attributes")
    if isinstance(attrs, str):
        try:
            out["attributes"] = json.loads(attrs)
        except json.JSONDecodeError:
            out["attributes"] = {}
    elif attrs is None:
        out["attributes"] = {}

    out["error"] = {
        "is_error": bool(out.pop("is_error", False)),
        "kind": out.pop("error_kind", None),
        "message": out.pop("error_message", None),
    }
    return out


def _iso_to_ns(value: Optional[str]) -> Optional[int]:
    from datetime import datetime as _dt

    if not value:
        return None
    try:
        return int(_dt.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1_000_000_000)
    except Exception:
        return None


def upsert_edges(
    edges: List[Dict[str, Any]],
    source: str,
    trace_metrics: Optional[Dict[str, Any]] = None,
) -> int:
    now = _now_iso()
    with neo4j_driver.session() as session:
        count = session.execute_write(_upsert_edges_tx, edges, source, now, trace_metrics)
        if trace_metrics is not None and edges:
            is_err = bool(trace_metrics.get("is_error"))
            dur_ns = int(trace_metrics.get("duration_ns") or 0)
            trace_id = trace_metrics.get("trace_id")
            span_id = trace_metrics.get("span_id")
            metric_time = trace_metrics.get("timestamp") or now
            session.execute_write(
                _record_trace_bucket, metric_time, is_err, trace_id, span_id, now,
            )
            sigs = list({
                _edge_sig(e["source_id"], e["target_id"], e["type"])
                for e in edges
                if e.get("source_id") and e.get("target_id") and e.get("type")
                and e["type"].upper() in CALL_LIKE_EDGE_TYPES
            })
            if sigs:
                session.execute_write(
                    _record_edge_activity, sigs, metric_time, is_err, dur_ns, trace_id, span_id, now,
                )
    return count


def get_edge_activity_window(
    edge_sigs: List[str],
    from_time: Optional[str],
    to_time: Optional[str],
) -> Dict[str, Dict[str, int]]:
    if not edge_sigs:
        return {}
    with neo4j_driver.session() as session:
        return session.execute_read(_read_edge_activity_window, edge_sigs, from_time, to_time)


def _read_edge_activity_window(
    tx: ManagedTransaction,
    edge_sigs: List[str],
    from_time: Optional[str],
    to_time: Optional[str],
) -> Dict[str, Dict[str, int]]:
    from datetime import datetime as _dt

    def _iso_to_ms(s: Optional[str]) -> Optional[int]:
        if not s:
            return None
        try:
            return int(_dt.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)
        except Exception:
            return None

    from_ms = _iso_to_ms(from_time)
    to_ms = _iso_to_ms(to_time)

    conditions = ["a.edge_sig IN $sigs"]
    params: Dict[str, Any] = {"sigs": edge_sigs}
    if from_ms is not None:
        conditions.append("a.bucket_ts >= $from_ms")
        params["from_ms"] = from_ms
    if to_ms is not None:
        conditions.append("a.bucket_ts < $to_ms")
        params["to_ms"] = to_ms
    where = " WHERE " + " AND ".join(conditions)

    query = (
        f"MATCH (a:EdgeActivity){where} "
        "RETURN a.edge_sig AS sig, "
        "       sum(a.span_count) AS spans, "
        "       sum(a.error_count) AS errs, "
        "       sum(a.total_duration_ns) AS dur"
    )
    out: Dict[str, Dict[str, int]] = {}
    result = tx.run(query, **params)
    for rec in result:
        out[rec["sig"]] = {
            "span_count": int(rec["spans"] or 0),
            "error_count": int(rec["errs"] or 0),
            "total_duration_ns": int(rec["dur"] or 0),
        }
    return out


def get_endpoint_activity_window(
    endpoints: List[Dict[str, str]],
    from_time: Optional[str],
    to_time: Optional[str],
) -> Dict[str, Dict[str, float]]:
    if not endpoints:
        return {}
    with neo4j_driver.session() as session:
        return session.execute_read(_read_endpoint_activity_window, endpoints, from_time, to_time)


def _read_endpoint_activity_window(
    tx: ManagedTransaction,
    endpoints: List[Dict[str, str]],
    from_time: Optional[str],
    to_time: Optional[str],
) -> Dict[str, Dict[str, float]]:
    from_ns = _iso_to_ns(from_time)
    to_ns = _iso_to_ns(to_time)

    conditions = ["s.service_name = endpoint.service_name", "s.span_name = endpoint.span_name"]
    params: Dict[str, Any] = {"endpoints": endpoints}
    if from_ns is not None:
        conditions.append("s.start_time_ns >= $from_ns")
        params["from_ns"] = from_ns
    if to_ns is not None:
        conditions.append("s.start_time_ns < $to_ns")
        params["to_ns"] = to_ns

    server_values = ["SPAN_KIND_SERVER", "SERVER", "2"]
    where = " AND ".join(conditions)
    query = (
        "UNWIND $endpoints AS endpoint "
        "MATCH (s:Span) "
        "WHERE coalesce(s.span_kind, '') IN $server_values "
        f"AND {where} "
        "RETURN endpoint.id AS endpoint_id, "
        "       count(s) AS calls, "
        "       sum(CASE WHEN coalesce(s.is_error, false) THEN 1 ELSE 0 END) AS errors, "
        "       percentileCont(toFloat(s.duration_ns) / 1000000.0, 0.99) AS p99_ms"
    )
    params["server_values"] = server_values

    out: Dict[str, Dict[str, float]] = {}
    for rec in tx.run(query, **params):
        out[rec["endpoint_id"]] = {
            "call_count": float(rec["calls"] or 0),
            "error_count": float(rec["errors"] or 0),
            "latency_p99_ms": float(rec["p99_ms"] or 0.0),
        }
    return out


def get_trace_activity(
    from_time: Optional[str],
    to_time: Optional[str],
    bucket_seconds: int,
) -> List[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(_read_trace_activity, from_time, to_time, bucket_seconds)


def _read_trace_activity(
    tx: ManagedTransaction,
    from_time: Optional[str],
    to_time: Optional[str],
    bucket_seconds: int,
) -> List[Dict[str, Any]]:
    from datetime import datetime as _dt

    def _iso_to_ms(s: Optional[str]) -> Optional[int]:
        if not s:
            return None
        try:
            return int(_dt.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)
        except Exception:
            return None

    from_ms = _iso_to_ms(from_time)
    to_ms = _iso_to_ms(to_time)

    conditions = []
    params: Dict[str, Any] = {}
    if from_ms is not None:
        conditions.append("b.bucket_ts >= $from_ms")
        params["from_ms"] = from_ms
    if to_ms is not None:
        conditions.append("b.bucket_ts < $to_ms")
        params["to_ms"] = to_ms
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    query = (
        f"MATCH (b:TraceBucket){where} "
        "RETURN b.bucket_ts AS ts, b.span_count AS spans, b.error_count AS errs "
        "ORDER BY ts"
    )
    result = tx.run(query, **params)

    out_bucket_ms = max(bucket_seconds, TRACE_BUCKET_SECONDS) * 1000
    agg: Dict[int, Dict[str, int]] = {}
    for rec in result:
        ts = int(rec["ts"])
        bid = (ts // out_bucket_ms) * out_bucket_ms
        cell = agg.setdefault(bid, {"span_count": 0, "error_count": 0})
        cell["span_count"] += int(rec["spans"] or 0)
        cell["error_count"] += int(rec["errs"] or 0)

    return [
        {
            "bucket_ts": bid,
            "timestamp": _dt.utcfromtimestamp(bid / 1000).isoformat() + "+00:00",
            "span_count": cell["span_count"],
            "error_count": cell["error_count"],
        }
        for bid, cell in sorted(agg.items())
    ]


def _upsert_edges_tx(
    tx: ManagedTransaction,
    edges: List[Dict],
    source: str,
    now: str,
    trace_metrics: Optional[Dict[str, Any]] = None,
) -> int:
    count = 0
    has_trace = trace_metrics is not None
    is_error = bool(trace_metrics.get("is_error")) if has_trace else False
    duration_ns = int(trace_metrics.get("duration_ns") or 0) if has_trace else 0

    for raw in edges:
        data = _strip_none(raw)
        source_id = data["source_id"]
        target_id = data["target_id"]
        edge_type = data["type"].upper()

        # Strip aggregate-managed props so a mapping cannot overwrite counters.
        props = _flatten_values({
            k: v for k, v in data.items()
            if k not in _EDGE_META_KEYS and k not in _EDGE_LOAD_PROPS
        })

        trace_clause = ""
        if has_trace and edge_type in CALL_LIKE_EDGE_TYPES:
            trace_clause = (
                ", rel.call_count = coalesce(rel.call_count, 0) + 1"
                ", rel.error_count = coalesce(rel.error_count, 0) + $err_inc"
                ", rel.total_duration_ns = coalesce(rel.total_duration_ns, 0) + $dur_ns"
                ", rel.last_call_at = $now"
            )

        query = (
            "MATCH (a:Resource {external_id: $source_id}) "
            "MATCH (b:Resource {external_id: $target_id}) "
            f"MERGE (a)-[rel:{edge_type}]->(b) "
            "ON CREATE SET rel.first_seen = $now, "
            "    rel.call_count = 0, rel.error_count = 0, rel.total_duration_ns = 0 "
            "SET rel.last_seen = $now, "
            "    rel.status = $status, "
            "    rel.weight = $weight, "
            "    rel.source = $source, "
            f"    rel += $props{trace_clause} "
            "RETURN rel"
        )

        params = {
            "source_id": source_id,
            "target_id": target_id,
            "status": data.get("status", "active"),
            "weight": data.get("weight", 1.0),
            "source": source,
            "now": now,
            "props": props,
        }
        if has_trace:
            params["err_inc"] = 1 if is_error else 0
            params["dur_ns"] = duration_ns

        try:
            tx.run(query, **params)
            count += 1
        except Exception:
            pass
    return count


def get_full_graph(
    limit: int = 500,
    exclude_node_types: Optional[List[str]] = None,
    exclude_edge_types: Optional[List[str]] = None,
    as_of: Optional[str] = None,
) -> Tuple[List[Dict], List[Dict]]:
    with neo4j_driver.session() as session:
        nodes = session.execute_read(_read_all_nodes, limit, exclude_node_types, as_of)
        node_ids = [n["id"] for n in nodes]
        edges = session.execute_read(_read_edges_for_nodes, node_ids, exclude_edge_types, as_of)
    return nodes, edges


def get_graph_by_sources(
    sources: List[str],
    limit: int = 500,
    exclude_node_types: Optional[List[str]] = None,
    exclude_edge_types: Optional[List[str]] = None,
    as_of: Optional[str] = None,
) -> Tuple[List[Dict], List[Dict]]:
    if not sources:
        return [], []

    with neo4j_driver.session() as session:
        nodes = session.execute_read(_read_nodes_by_sources, sources, limit, exclude_node_types, as_of)
        node_ids = [n["id"] for n in nodes]
        edges = session.execute_read(_read_edges_for_nodes, node_ids, exclude_edge_types, as_of)
    return nodes, edges


def _read_nodes_by_sources(
    tx: ManagedTransaction,
    sources: List[str],
    limit: int,
    exclude_node_types: Optional[List[str]] = None,
    as_of: Optional[str] = None,
) -> List[Dict]:
    conditions = ["r.source IN $sources"]
    params: Dict[str, Any] = {"sources": sources, "limit": limit}
    if exclude_node_types:
        conditions.append("NOT r.type IN $exclude_node_types")
        params["exclude_node_types"] = exclude_node_types
    if as_of:
        # Timeline snapshots are cumulative: once a resource appears, it stays
        # visible for later buckets unless we model explicit deletions.
        conditions.append("COALESCE(r.created_at, r.updated_at) <= $as_of")
        params["as_of"] = as_of
    where = " WHERE " + " AND ".join(conditions)
    result = tx.run(f"MATCH (r:Resource){where} RETURN r LIMIT $limit", **params)
    return [_node_record_to_dict(record["r"]) for record in result]


def _read_all_nodes(
    tx: ManagedTransaction,
    limit: int,
    exclude_node_types: Optional[List[str]] = None,
    as_of: Optional[str] = None,
) -> List[Dict]:
    conditions = []
    params: Dict[str, Any] = {"limit": limit}

    if exclude_node_types:
        conditions.append("NOT r.type IN $exclude_node_types")
        params["exclude_node_types"] = exclude_node_types

    if as_of:
        # Keep graph snapshots consistent with /timeline/events running totals.
        conditions.append("COALESCE(r.created_at, r.updated_at) <= $as_of")
        params["as_of"] = as_of

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    result = tx.run(f"MATCH (r:Resource){where} RETURN r LIMIT $limit", **params)
    return [_node_record_to_dict(record["r"]) for record in result]


def _read_edges_for_nodes(
    tx: ManagedTransaction,
    node_ids: List[str],
    exclude_edge_types: Optional[List[str]] = None,
    as_of: Optional[str] = None,
) -> List[Dict]:
    if not node_ids:
        return []
    query = (
        "MATCH (a:Resource)-[rel]->(b:Resource) "
        "WHERE a.external_id IN $ids AND b.external_id IN $ids "
    )
    params: Dict[str, Any] = {"ids": node_ids}
    if exclude_edge_types:
        query += "AND NOT type(rel) IN $exclude_edge_types "
        params["exclude_edge_types"] = [t.upper() for t in exclude_edge_types]
    if as_of:
        query += "AND rel.first_seen <= $as_of "
        params["as_of"] = as_of
    query += (
        "RETURN a.external_id AS source_id, "
        "       b.external_id AS target_id, "
        "       type(rel) AS type, "
        "       properties(rel) AS props"
    )
    result = tx.run(query, **params)
    rows: List[Dict] = []
    seen: set = set()
    for record in result:
        key = (record["source_id"], record["target_id"], record["type"])
        if key in seen:
            continue
        seen.add(key)
        row: Dict[str, Any] = {
            "source_id": record["source_id"],
            "target_id": record["target_id"],
            "type": record["type"],
        }
        row.update(record["props"] or {})
        rows.append(row)
    return rows


def get_subgraph(center_id: str, depth: int = 2,
                 node_types: Optional[List[str]] = None,
                 edge_types: Optional[List[str]] = None) -> Tuple[List[Dict], List[Dict]]:
    with neo4j_driver.session() as session:
        return session.execute_read(
            _read_subgraph, center_id, depth, node_types, edge_types
        )


def _read_subgraph(tx: ManagedTransaction, center_id: str, depth: int,
                   node_types: Optional[List[str]],
                   edge_types: Optional[List[str]]) -> Tuple[List[Dict], List[Dict]]:
    rel_filter = ""
    if edge_types:
        types_str = "|".join(t.upper() for t in edge_types)
        rel_filter = f":{types_str}"

    query = (
        f"MATCH path = (center:Resource {{external_id: $center_id}})"
        f"-[*1..{depth}{rel_filter}]-(neighbor:Resource) "
        "UNWIND nodes(path) AS n "
        "WITH collect(DISTINCT n) AS allNodes, collect(DISTINCT path) AS paths "
        "UNWIND allNodes AS nd "
        "WITH nd, paths "
    )

    if node_types:
        query += "WHERE nd.type IN $node_types "

    query += (
        "WITH collect(DISTINCT nd) AS filteredNodes, paths "
        "UNWIND paths AS p "
        "UNWIND relationships(p) AS rel "
        "WITH filteredNodes, rel, startNode(rel) AS sn, endNode(rel) AS en "
        "WHERE sn IN filteredNodes AND en IN filteredNodes "
        "RETURN filteredNodes, collect(DISTINCT {source_id: sn.external_id, "
        "       target_id: en.external_id, type: type(rel), "
        "       props: properties(rel)}) AS rels"
    )

    result = tx.run(query, center_id=center_id, node_types=node_types or [])
    record = result.single()
    if record is None:
        return [], []

    nodes = [_node_record_to_dict(n) for n in record["filteredNodes"]]
    edges = []
    for r in record["rels"]:
        edge = {"source_id": r["source_id"], "target_id": r["target_id"], "type": r["type"]}
        edge.update(r.get("props") or {})
        edges.append(edge)
    return nodes, edges


def find_shortest_path(source_id: str, target_id: str,
                       max_depth: int = 5) -> Tuple[List[Dict], List[Dict]]:
    with neo4j_driver.session() as session:
        return session.execute_read(_find_path_tx, source_id, target_id, max_depth)


def _find_path_tx(tx: ManagedTransaction, source_id: str,
                  target_id: str, max_depth: int) -> Tuple[List[Dict], List[Dict]]:
    query = (
        "MATCH path = shortestPath("
        "  (a:Resource {external_id: $source_id})"
        f"  -[*..{max_depth}]-"
        "  (b:Resource {external_id: $target_id})"
        ") "
        "RETURN nodes(path) AS ns, relationships(path) AS rs"
    )
    result = tx.run(query, source_id=source_id, target_id=target_id)
    record = result.single()
    if record is None:
        return [], []

    nodes = [_node_record_to_dict(n) for n in record["ns"]]
    edges = []
    for rel in record["rs"]:
        sn = rel.start_node
        en = rel.end_node
        edge = {
            "source_id": sn["external_id"],
            "target_id": en["external_id"],
            "type": rel.type,
        }
        edge.update(dict(rel))
        edges.append(edge)
    return nodes, edges


def get_impact(node_id: str, depth: int = 3,
               direction: str = "downstream") -> Tuple[List[Dict], List[Dict]]:

    with neo4j_driver.session() as session:
        return session.execute_read(_impact_tx, node_id, depth, direction)


def _impact_tx(tx: ManagedTransaction, node_id: str,
               depth: int, direction: str) -> Tuple[List[Dict], List[Dict]]:
    if direction == "downstream":
        arrow = f"-[*1..{depth}]->"
    elif direction == "upstream":
        arrow = f"<-[*1..{depth}]-"
    else:
        arrow = f"-[*1..{depth}]-"

    query = (
        f"MATCH path = (center:Resource {{external_id: $node_id}}){arrow}(n:Resource) "
        "UNWIND nodes(path) AS nd "
        "UNWIND relationships(path) AS rel "
        "WITH collect(DISTINCT nd) AS ns, "
        "     collect(DISTINCT {source_id: startNode(rel).external_id, "
        "             target_id: endNode(rel).external_id, type: type(rel), "
        "             props: properties(rel)}) AS rs "
        "RETURN ns, rs"
    )

    result = tx.run(query, node_id=node_id)
    record = result.single()
    if record is None:
        return [], []

    nodes = [_node_record_to_dict(n) for n in record["ns"]]
    edges = []
    for r in record["rs"]:
        edge = {"source_id": r["source_id"], "target_id": r["target_id"], "type": r["type"]}
        edge.update(r.get("props") or {})
        edges.append(edge)
    return nodes, edges


def get_graph_stats() -> Dict[str, Any]:
    with neo4j_driver.session() as session:
        return session.execute_read(_stats_tx)


def delete_graph_by_sources(sources: List[str]) -> Dict[str, int]:
    if not sources:
        return {"deleted_nodes": 0, "deleted_edges": 0}

    with neo4j_driver.session() as session:
        return session.execute_write(_delete_graph_by_sources_tx, sources)


def _delete_graph_by_sources_tx(tx: ManagedTransaction, sources: List[str]) -> Dict[str, int]:
    edge_count_record = tx.run(
        "MATCH ()-[rel]->() WHERE rel.source IN $sources RETURN count(rel) AS count",
        sources=sources,
    ).single()
    deleted_edges = int(edge_count_record["count"]) if edge_count_record else 0

    tx.run(
        "MATCH ()-[rel]->() WHERE rel.source IN $sources DELETE rel",
        sources=sources,
    )

    node_count_record = tx.run(
        "MATCH (n:Resource) WHERE n.source IN $sources RETURN count(n) AS count",
        sources=sources,
    ).single()
    deleted_nodes = int(node_count_record["count"]) if node_count_record else 0

    tx.run(
        "MATCH (n:Resource) WHERE n.source IN $sources DETACH DELETE n",
        sources=sources,
    )

    return {"deleted_nodes": deleted_nodes, "deleted_edges": deleted_edges}


def _stats_tx(tx: ManagedTransaction) -> Dict[str, Any]:
    node_res = tx.run(
        "MATCH (r:Resource) RETURN r.type AS type, count(*) AS cnt"
    )
    nodes_by_type = {
        str(rec["type"] or "unknown"): rec["cnt"] for rec in node_res
    }

    edge_res = tx.run(
        "MATCH (:Resource)-[rel]->(:Resource) RETURN type(rel) AS type, count(*) AS cnt"
    )
    edges_by_type = {
        str(rec["type"] or "unknown"): rec["cnt"] for rec in edge_res
    }

    return {
        "total_nodes": sum(nodes_by_type.values()),
        "total_edges": sum(edges_by_type.values()),
        "nodes_by_type": nodes_by_type,
        "edges_by_type": edges_by_type,
    }


def delete_stale(hours: int) -> int:
    with neo4j_driver.session() as session:
        return session.execute_write(_delete_stale_tx, hours)


def _delete_stale_tx(tx: ManagedTransaction, hours: int) -> int:
    result = tx.run(
        "MATCH (r:Resource) "
        "WHERE r.last_seen_at < datetime() - duration({hours: $hours}) "
        "DETACH DELETE r "
        "RETURN count(*) AS deleted",
        hours=hours,
    )
    record = result.single()
    return record["deleted"] if record else 0


def get_timeline_range() -> Dict[str, Optional[str]]:
    """Return the earliest created_at and latest last_seen_at across all resources."""
    with neo4j_driver.session() as session:
        return session.execute_read(_read_timeline_range)


def _to_str(val):
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if hasattr(val, "iso_format"):
        return val.iso_format()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _read_timeline_range(tx: ManagedTransaction) -> Dict[str, Optional[str]]:
    result = tx.run(
        "MATCH (r:Resource) "
        "RETURN min(COALESCE(r.created_at, r.updated_at)) AS min_time, "
        "       max(r.last_seen_at) AS max_time, "
        "       count(r) AS total_nodes"
    )
    record = result.single()
    if not record or record["min_time"] is None:
        return {"min_time": None, "max_time": None, "total_nodes": 0, "total_edges": 0}

    edge_res = tx.run("MATCH (:Resource)-[rel]->(:Resource) RETURN count(rel) AS cnt")
    edge_rec = edge_res.single()
    total_edges = edge_rec["cnt"] if edge_rec else 0

    return {
        "min_time": _to_str(record["min_time"]),
        "max_time": _to_str(record["max_time"]),
        "total_nodes": record["total_nodes"],
        "total_edges": total_edges,
    }


def get_timeline_events(
    bucket_seconds: int = 30,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(
            _read_timeline_events, bucket_seconds, from_time, to_time
        )


def _read_timeline_events(
    tx: ManagedTransaction,
    bucket_seconds: int,
    from_time: Optional[str],
    to_time: Optional[str],
) -> List[Dict[str, Any]]:
    conditions = ["r.created_at IS NOT NULL"]
    params: Dict[str, Any] = {"bucket_seconds": bucket_seconds}
    if from_time:
        conditions.append("r.created_at >= $from_time")
        params["from_time"] = from_time
    if to_time:
        conditions.append("r.created_at <= $to_time")
        params["to_time"] = to_time
    where = " WHERE " + " AND ".join(conditions)

    node_query = (
        f"MATCH (r:Resource){where} "
        "RETURN r.created_at AS created, r.type AS ntype "
        "ORDER BY created"
    )
    node_result = tx.run(node_query, **params)

    bucket_ms = bucket_seconds * 1000
    node_buckets: Dict[int, Dict] = {}

    for rec in node_result:
        created_val = rec["created"]
        ntype = str(rec["ntype"] or "unknown")

        ts_ms: int
        if isinstance(created_val, (int, float)):
            ts_ms = int(created_val)
        elif hasattr(created_val, "to_native"):
            dt = created_val.to_native()
            ts_ms = int(dt.timestamp() * 1000)
        elif isinstance(created_val, str):
            from datetime import datetime as _dt
            try:
                dt = _dt.fromisoformat(created_val.replace("Z", "+00:00"))
                ts_ms = int(dt.timestamp() * 1000)
            except Exception:
                continue
        else:
            continue

        bid = ts_ms // bucket_ms
        if bid not in node_buckets:
            node_buckets[bid] = {
                "bucket_id": bid,
                "timestamp": _to_str(created_val),
                "nodes_added": 0,
                "edges_added": 0,
                "node_types": {},
                "_ts_ms": ts_ms,
            }
        bucket = node_buckets[bid]
        bucket["nodes_added"] += 1
        bucket["node_types"][ntype] = bucket["node_types"].get(ntype, 0) + 1

    edge_conditions = ["rel.first_seen IS NOT NULL"]
    edge_params: Dict[str, Any] = {}
    if from_time:
        edge_conditions.append("rel.first_seen >= $from_time")
        edge_params["from_time"] = from_time
    if to_time:
        edge_conditions.append("rel.first_seen <= $to_time")
        edge_params["to_time"] = to_time
    edge_where = " WHERE " + " AND ".join(edge_conditions)

    edge_query = (
        f"MATCH (:Resource)-[rel]->(:Resource){edge_where} "
        "RETURN rel.first_seen AS first_seen "
        "ORDER BY first_seen"
    )
    edge_result = tx.run(edge_query, **edge_params)
    for rec in edge_result:
        fs_val = rec["first_seen"]

        ts_ms: int
        if isinstance(fs_val, (int, float)):
            ts_ms = int(fs_val)
        elif hasattr(fs_val, "to_native"):
            dt = fs_val.to_native()
            ts_ms = int(dt.timestamp() * 1000)
        elif isinstance(fs_val, str):
            from datetime import datetime as _dt
            try:
                dt = _dt.fromisoformat(fs_val.replace("Z", "+00:00"))
                ts_ms = int(dt.timestamp() * 1000)
            except Exception:
                continue
        else:
            continue

        bid = ts_ms // bucket_ms
        if bid in node_buckets:
            node_buckets[bid]["edges_added"] += 1
        else:
            node_buckets[bid] = {
                "bucket_id": bid,
                "timestamp": _to_str(fs_val),
                "nodes_added": 0,
                "edges_added": 1,
                "node_types": {},
                "_ts_ms": ts_ms,
            }

    sorted_buckets = sorted(node_buckets.values(), key=lambda b: b["bucket_id"])

    running_nodes = 0
    running_edges = 0
    for bucket in sorted_buckets:
        running_nodes += bucket["nodes_added"]
        running_edges += bucket["edges_added"]
        bucket["running_total_nodes"] = running_nodes
        bucket["running_total_edges"] = running_edges
        bucket.pop("_ts_ms", None)

    return sorted_buckets


def get_snapshot_stats(at_time: str) -> Dict[str, Any]:
    with neo4j_driver.session() as session:
        return session.execute_read(_read_snapshot_stats, at_time)


def _read_snapshot_stats(tx: ManagedTransaction, at_time: str) -> Dict[str, Any]:
    node_res = tx.run(
        "MATCH (r:Resource) "
        "WHERE COALESCE(r.created_at, r.updated_at) <= $at_time "
        "RETURN r.type AS type, count(*) AS cnt",
        at_time=at_time,
    )
    nodes_by_type: Dict[str, int] = {}
    total_nodes = 0
    for rec in node_res:
        t = str(rec["type"] or "unknown")
        nodes_by_type[t] = rec["cnt"]
        total_nodes += rec["cnt"]

    edge_res = tx.run(
        "MATCH (:Resource)-[rel]->(:Resource) "
        "WHERE rel.first_seen <= $at_time "
        "RETURN type(rel) AS type, count(*) AS cnt",
        at_time=at_time,
    )
    edges_by_type: Dict[str, int] = {}
    total_edges = 0
    for rec in edge_res:
        t = str(rec["type"] or "unknown")
        edges_by_type[t] = rec["cnt"]
        total_edges += rec["cnt"]

    return {
        "at_time": at_time,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "nodes_by_type": nodes_by_type,
        "edges_by_type": edges_by_type,
    }


def _node_record_to_dict(node) -> Dict[str, Any]:
    d = dict(node)
    d["id"] = d.pop("external_id", d.get("id"))
    return d


def find_node_by_field(
    node_type: str,
    field_name: str,
    field_value: str,
) -> Optional[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(
            _find_node_by_field_tx, node_type, field_name, field_value
        )


def _find_node_by_field_tx(
    tx: ManagedTransaction,
    node_type: str,
    field_name: str,
    field_value: str,
) -> Optional[Dict[str, Any]]:
    if field_name == "name":
        prop_query = "r.name = $value"
    elif field_name == "cluster_id":
        prop_query = "r.cluster_id = $value"
    else:
        prop_query = f"r.{field_name} = $value"

    query = (
        f"MATCH (r:Resource) "
        f"WHERE r.type = $node_type AND {prop_query} "
        f"RETURN r "
        f"LIMIT 1"
    )

    result = tx.run(query, node_type=node_type, value=field_value)
    record = result.single()
    if record is None:
        return None
    return _node_record_to_dict(record["r"])


def find_node_by_name(name: str) -> Optional[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        return session.execute_read(_find_node_by_name_tx, name)


def _find_node_by_name_tx(
    tx: ManagedTransaction,
    name: str,
) -> Optional[Dict[str, Any]]:
    query = (
        "MATCH (r:Resource) "
        "WHERE r.name = $name "
        "RETURN r.external_id AS id, r.type AS type, r.name AS name "
        "LIMIT 1"
    )
    result = tx.run(query, name=name)
    record = result.single()
    if record is None:
        return None
    return {
        "id": record["id"],
        "type": record["type"],
        "name": record["name"],
    }


def get_nodes_by_types(node_types: List[str]) -> List[Dict[str, Any]]:
    if not node_types:
        return []
    with neo4j_driver.session() as session:
        return session.execute_read(_get_nodes_by_types_tx, node_types)


def _get_nodes_by_types_tx(
    tx: ManagedTransaction,
    node_types: List[str],
) -> List[Dict[str, Any]]:
    query = (
        "MATCH (r:Resource) "
        "WHERE r.type IN $node_types "
        "RETURN r"
    )
    result = tx.run(query, node_types=node_types)
    return [_node_record_to_dict(record["r"]) for record in result]


def get_all_node_types() -> List[str]:
    with neo4j_driver.session() as session:
        return session.execute_read(_get_all_node_types_tx)


def _get_all_node_types_tx(tx: ManagedTransaction) -> List[str]:
    result = tx.run("MATCH (r:Resource) RETURN DISTINCT r.type AS type")
    return [record["type"] for record in result if record["type"]]
