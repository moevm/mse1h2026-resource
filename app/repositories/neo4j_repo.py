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
        props = {k: v for k, v in data.items() if k not in _NODE_META_KEYS}

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
                "RETURN r"
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

        props = {k: v for k, v in data.items() if k not in _EDGE_META_KEYS}

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

        tx.run(query, **params)
        count += 1
    return count


def get_full_graph(limit: int = 500) -> Tuple[List[Dict], List[Dict]]:
    """Return all nodes and edges (edges are restricted to the fetched node set)."""
    with neo4j_driver.session() as session:
        nodes = session.execute_read(_read_all_nodes, limit)
        node_ids = [n["id"] for n in nodes]
        edges = session.execute_read(_read_edges_for_nodes, node_ids)
    return nodes, edges


def get_graph_by_sources(sources: List[str], limit: int = 500) -> Tuple[List[Dict], List[Dict]]:
    """Return nodes and edges filtered by source (agent name).

    Used for application-scoped graph visualization.
    """
    if not sources:
        return [], []

    with neo4j_driver.session() as session:
        nodes = session.execute_read(_read_nodes_by_sources, sources, limit)
        node_ids = [n["id"] for n in nodes]
        edges = session.execute_read(_read_edges_for_nodes, node_ids)
    return nodes, edges


def _read_nodes_by_sources(tx: ManagedTransaction, sources: List[str], limit: int) -> List[Dict]:
    result = tx.run(
        "MATCH (r:Resource) "
        "WHERE r.source IN $sources "
        "RETURN r LIMIT $limit",
        sources=sources,
        limit=limit,
    )
    return [_node_record_to_dict(record["r"]) for record in result]


def _read_all_nodes(tx: ManagedTransaction, limit: int) -> List[Dict]:
    result = tx.run(
        "MATCH (r:Resource) RETURN r LIMIT $limit",
        limit=limit,
    )
    return [_node_record_to_dict(record["r"]) for record in result]


def _read_all_edges(tx: ManagedTransaction, limit: int) -> List[Dict]:
    result = tx.run(
        "MATCH (a:Resource)-[rel]->(b:Resource) "
        "RETURN a.external_id AS source_id, "
        "       b.external_id AS target_id, "
        "       type(rel) AS type, "
        "       properties(rel) AS props "
        "LIMIT $limit",
        limit=limit,
    )
    rows = []
    for record in result:
        row = {
            "source_id": record["source_id"],
            "target_id": record["target_id"],
            "type": record["type"],
        }
        row.update(record["props"] or {})
        rows.append(row)
    return rows


def _read_edges_for_nodes(tx: ManagedTransaction, node_ids: List[str]) -> List[Dict]:
    """Fetch ALL edges whose source AND target are in node_ids (no arbitrary cut-off).

    Using this instead of a separate LIMIT keeps the edge set coherent
    with the returned node set: every visible connection is present.
    Duplicate parallel relationships (same source/target/type) are
    de-duplicated here to save bandwidth.
    """
    if not node_ids:
        return []
    result = tx.run(
        "MATCH (a:Resource)-[rel]->(b:Resource) "
        "WHERE a.external_id IN $ids AND b.external_id IN $ids "
        "RETURN a.external_id AS source_id, "
        "       b.external_id AS target_id, "
        "       type(rel) AS type, "
        "       properties(rel) AS props",
        ids=node_ids,
    )
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
    """BFS from center_id up to *depth* hops, optionally filtering types."""
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
    """Find shortest path between two nodes."""
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
    """Delete graph data produced by specific sources (agent names).

    Removes:
    - relationships where rel.source IN sources
    - nodes where node.source IN sources (with DETACH DELETE)
    """
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


def _node_record_to_dict(node) -> Dict[str, Any]:
    d = dict(node)
    d["id"] = d.pop("external_id", d.get("id"))
    return d


def find_node_by_field(
    node_type: str,
    field_name: str,
    field_value: str,
) -> Optional[Dict[str, Any]]:
    """Find a node by type and field value.

    Used for auto-edge creation to find target nodes.

    Args:
        node_type: The type of node to find (Service, Node, Database, etc.)
        field_name: The field to match (name, cluster_id, etc.)
        field_value: The value to match

    Returns:
        Node dictionary or None if not found
    """
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
    # Map field_name to Neo4j property
    # In Neo4j, 'name' is stored directly, other fields are in props
    if field_name == "name":
        prop_query = "r.name = $value"
    elif field_name == "cluster_id":
        prop_query = "r.cluster_id = $value"
    else:
        # For other fields, check if they exist as direct properties
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
    """Find a node by name field across all types.

    Used for resolving edge URN format - finds node to determine its type.

    Args:
        name: The node name to search for

    Returns:
        Node dictionary with 'id' and 'type' fields, or None if not found
    """
    with neo4j_driver.session() as session:
        return session.execute_read(_find_node_by_name_tx, name)


def _find_node_by_name_tx(
    tx: ManagedTransaction,
    name: str,
) -> Optional[Dict[str, Any]]:
    """Transaction for find_node_by_name."""
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
    """Get all nodes of specified types.

    Used for edge recreation after bulk node insertion.

    Args:
        node_types: List of node types to fetch (e.g., ['Service', 'Database'])

    Returns:
        List of node dictionaries with all properties
    """
    if not node_types:
        return []
    with neo4j_driver.session() as session:
        return session.execute_read(_get_nodes_by_types_tx, node_types)


def _get_nodes_by_types_tx(
    tx: ManagedTransaction,
    node_types: List[str],
) -> List[Dict[str, Any]]:
    """Transaction for get_nodes_by_types."""
    query = (
        "MATCH (r:Resource) "
        "WHERE r.type IN $node_types "
        "RETURN r"
    )
    result = tx.run(query, node_types=node_types)
    return [_node_record_to_dict(record["r"]) for record in result]


def get_all_node_types() -> List[str]:
    """Get all unique node types in the graph."""
    with neo4j_driver.session() as session:
        return session.execute_read(_get_all_node_types_tx)


def _get_all_node_types_tx(tx: ManagedTransaction) -> List[str]:
    """Transaction for get_all_node_types."""
    result = tx.run("MATCH (r:Resource) RETURN DISTINCT r.type AS type")
    return [record["type"] for record in result if record["type"]]