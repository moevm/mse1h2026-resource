from __future__ import annotations

import logging
from typing import Any

from app.models.topology import GraphResponse
from app.models.traversal import TraversalRule, TraversalStep, PRESET_RULES
from app.repositories.neo4j_connection import neo4j_driver
from app.services.graph_service import _to_graph_node, _to_graph_edge

log = logging.getLogger(__name__)


def list_presets() -> list[dict]:
    return PRESET_RULES


def execute_traversal(rule: TraversalRule) -> GraphResponse:
    with neo4j_driver.session() as session:
        result = session.execute_read(_execute_rule_tx, rule)
    return result


def _execute_rule_tx(tx: Any, rule: TraversalRule) -> GraphResponse:
    if rule.start_node_id:
        start_query = "MATCH (n:Resource {external_id: $start_id}) RETURN collect(n) AS starts"
        start_result = tx.run(start_query, start_id=rule.start_node_id)
        record = start_result.single()
        start_nodes = record["starts"] if record else []
    elif rule.start_node_types:
        start_query = "MATCH (n:Resource) WHERE n.type IN $types RETURN collect(n) AS starts"
        start_result = tx.run(start_query, types=rule.start_node_types)
        record = start_result.single()
        start_nodes = record["starts"] if record else []
    else:
        return GraphResponse(nodes=[], edges=[], node_count=0, edge_count=0)

    if not start_nodes:
        return GraphResponse(nodes=[], edges=[], node_count=0, edge_count=0)

    all_node_ids: set[str] = {n["external_id"] for n in start_nodes}
    current_ids = list(all_node_ids)

    for step in rule.steps:
        if not current_ids:
            break
        new_ids = _execute_step(tx, current_ids, step)
        all_node_ids.update(new_ids)
        current_ids = list(new_ids)

    if not all_node_ids:
        return GraphResponse(nodes=[], edges=[], node_count=0, edge_count=0)

    all_ids_list = list(all_node_ids)[:rule.limit]

    nodes_query = (
        "MATCH (n:Resource) WHERE n.external_id IN $ids "
        "RETURN n"
    )
    nodes_result = tx.run(nodes_query, ids=all_ids_list)
    raw_nodes = [_neo4j_node_to_dict(record["n"]) for record in nodes_result]

    edges_query = (
        "MATCH (a:Resource)-[rel]->(b:Resource) "
        "WHERE a.external_id IN $ids AND b.external_id IN $ids "
        "RETURN a.external_id AS source_id, b.external_id AS target_id, "
        "       type(rel) AS type, properties(rel) AS props"
    )
    edges_result = tx.run(edges_query, ids=all_ids_list)
    raw_edges = []
    for record in edges_result:
        edge: dict[str, Any] = {
            "source_id": record["source_id"],
            "target_id": record["target_id"],
            "type": record["type"],
        }
        edge.update(record["props"] or {})
        raw_edges.append(edge)

    nodes = [_to_graph_node(n) for n in raw_nodes]
    edges = [_to_graph_edge(e) for e in raw_edges]

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
    )


def _execute_step(tx: Any, current_ids: list[str], step: TraversalStep) -> set[str]:
    edge_types_upper = [et.upper() for et in step.edge_types]

    if edge_types_upper:
        type_filter = ":" + "|".join(edge_types_upper)
    else:
        type_filter = ""

    depth_range = f"{step.min_depth}..{step.max_depth}"

    if step.direction == "outgoing":
        pattern = f"-[rel{type_filter}*{depth_range}]->"
    elif step.direction == "incoming":
        pattern = f"<-[rel{type_filter}*{depth_range}]-"
    else:
        pattern = f"-[rel{type_filter}*{depth_range}]-"

    query = (
        f"MATCH (start:Resource){pattern}(target:Resource) "
        f"WHERE start.external_id IN $ids "
    )

    if step.target_node_types:
        query += "AND target.type IN $target_types "

    query += "RETURN collect(DISTINCT target.external_id) AS found_ids"

    params: dict[str, Any] = {"ids": current_ids}
    if step.target_node_types:
        params["target_types"] = step.target_node_types

    result = tx.run(query, **params)
    record = result.single()

    if record and record["found_ids"]:
        return set(record["found_ids"])
    return set()


def _neo4j_node_to_dict(node: Any) -> dict[str, Any]:
    d = dict(node)
    d["id"] = d.pop("external_id", d.get("id"))
    return d
