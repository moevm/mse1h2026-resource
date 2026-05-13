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


def upsert_edges(edges: List[Dict[str, Any]], source: str) -> int:
    now = _now_iso()
    with neo4j_driver.session() as session:
        count = session.execute_write(_upsert_edges_tx, edges, source, now)
    return count


def _upsert_edges_tx(tx: ManagedTransaction, edges: List[Dict], source: str, now: str) -> int:
    count = 0
    for raw in edges:
        data = _strip_none(raw)
        source_id = data["source_id"]
        target_id = data["target_id"]
        edge_type = data["type"].upper()

        props = _flatten_values({k: v for k, v in data.items() if k not in _EDGE_META_KEYS})

        query = (
            "MATCH (a:Resource {external_id: $source_id}) "
            "MATCH (b:Resource {external_id: $target_id}) "
            f"MERGE (a)-[rel:{edge_type}]->(b) "
            "ON CREATE SET rel.first_seen = $now "
            "SET rel.last_seen = $now, "
            "    rel.status = $status, "
            "    rel.weight = $weight, "
            "    rel.source = $source, "
            "    rel += $props "
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
        conditions.append("COALESCE(r.created_at, r.updated_at) <= $as_of AND (r.last_seen_at >= $as_of OR r.last_seen_at IS NULL)")
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
        conditions.append("COALESCE(r.created_at, r.updated_at) <= $as_of AND (r.last_seen_at >= $as_of OR r.last_seen_at IS NULL)")
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
        query += "AND rel.first_seen <= $as_of AND (rel.last_seen >= $as_of OR rel.last_seen IS NULL) "
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
        "  AND (r.last_seen_at >= $at_time OR r.last_seen_at IS NULL) "
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
        "  AND (rel.last_seen >= $at_time OR rel.last_seen IS NULL) "
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
