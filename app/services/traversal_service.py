from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from app.models.topology import GraphResponse
from app.models.traversal import TraversalRule, TraversalStep, PRESET_RULES
from app.repositories import agent_repo, application_repo
from app.repositories.neo4j_connection import neo4j_driver
from app.services.graph_service import _to_graph_node, _to_graph_edge

log = logging.getLogger(__name__)


@dataclass
class StepResult:
    next_node_ids: list[str]
    node_ids: list[str]
    raw_edges: list[dict[str, Any]]


def list_presets() -> list[dict]:
    return PRESET_RULES


def execute_traversal(
    rule: TraversalRule,
    user_id: str | None = None,
    app_id: str | None = None,
) -> GraphResponse:
    allowed_sources = _resolve_allowed_sources(user_id, app_id)
    if user_id is not None and not allowed_sources:
        return _empty_graph()

    with neo4j_driver.session() as session:
        result = session.execute_read(_execute_rule_tx, rule, allowed_sources)
    return result


def _resolve_allowed_sources(user_id: str | None, app_id: str | None) -> list[str] | None:
    if user_id is None:
        return None
    if app_id:
        return application_repo.get_agent_names_for_application_and_user(app_id, user_id)
    return agent_repo.get_agent_names_for_user(user_id)


def _execute_rule_tx(
    tx: Any,
    rule: TraversalRule,
    allowed_sources: list[str] | None = None,
) -> GraphResponse:
    start_nodes = _load_start_nodes(tx, rule, allowed_sources)

    if not start_nodes:
        return _empty_graph()

    node_order: list[str] = []
    seen_node_ids: set[str] = set()
    raw_edges_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}

    current_ids = sorted(_node_external_id(n) for n in start_nodes)
    _add_node_ids(node_order, seen_node_ids, current_ids)

    for step_index, step in enumerate(rule.steps):
        if not current_ids:
            break
        step_result = _execute_step(tx, current_ids, step, step_index, allowed_sources)
        _add_node_ids(node_order, seen_node_ids, step_result.node_ids)
        for edge in step_result.raw_edges:
            _add_node_ids(node_order, seen_node_ids, [edge["source_id"], edge["target_id"]])
            key = _edge_key(edge)
            if key not in raw_edges_by_key:
                raw_edges_by_key[key] = edge
        current_ids = step_result.next_node_ids

    if not node_order:
        return _empty_graph()

    limited_ids = node_order[:rule.limit]
    limited_id_set = set(limited_ids)

    nodes_query = (
        "MATCH (n:Resource) "
        "WHERE n.external_id IN $ids "
        "AND COALESCE(n.status, 'active') <> 'deleted' "
        f"{_source_scope_clause('n', allowed_sources)}"
        "RETURN n"
    )
    nodes_result = tx.run(
        nodes_query,
        **_scope_params({"ids": limited_ids}, allowed_sources),
    )
    raw_nodes = [_neo4j_node_to_dict(record["n"]) for record in nodes_result]
    raw_nodes_by_id = {node["id"]: node for node in raw_nodes}
    ordered_raw_nodes = [raw_nodes_by_id[node_id] for node_id in limited_ids if node_id in raw_nodes_by_id]
    raw_edges = [
        edge for edge in raw_edges_by_key.values()
        if edge["source_id"] in limited_id_set and edge["target_id"] in limited_id_set
    ]
    raw_edges.sort(key=lambda edge: (edge["source_id"], edge["target_id"], edge["type"]))

    nodes = [_to_graph_node(n) for n in ordered_raw_nodes]
    edges = [_to_graph_edge(e) for e in raw_edges]

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
    )


def _load_start_nodes(
    tx: Any,
    rule: TraversalRule,
    allowed_sources: list[str] | None,
) -> list[Any]:
    if rule.start_node_id:
        start_query = (
            "MATCH (n:Resource {external_id: $start_id}) "
            "WHERE COALESCE(n.status, 'active') <> 'deleted' "
            f"{_source_scope_clause('n', allowed_sources)}"
            "WITH n ORDER BY n.external_id "
            "RETURN collect(n) AS starts"
        )
        params = {"start_id": rule.start_node_id}
    elif rule.start_node_types:
        start_query = (
            "MATCH (n:Resource) "
            "WHERE n.type IN $types "
            "AND COALESCE(n.status, 'active') <> 'deleted' "
            f"{_source_scope_clause('n', allowed_sources)}"
            "WITH n ORDER BY n.external_id "
            "RETURN collect(n) AS starts"
        )
        params = {"types": rule.start_node_types}
    else:
        return []

    start_result = tx.run(start_query, **_scope_params(params, allowed_sources))
    record = start_result.single()
    return record["starts"] if record else []


def _execute_step(
    tx: Any,
    current_ids: list[str],
    step: TraversalStep,
    step_index: int,
    allowed_sources: list[str] | None = None,
) -> StepResult:
    if not current_ids:
        return StepResult(next_node_ids=[], node_ids=[], raw_edges=[])

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
        f"MATCH path = (start:Resource){pattern}(target:Resource) "
        "WHERE start.external_id IN $ids "
        "AND COALESCE(start.status, 'active') <> 'deleted' "
        "AND COALESCE(target.status, 'active') <> 'deleted' "
    )

    if step.source_node_types:
        query += "AND start.type IN $source_types "

    if step.target_node_types:
        query += "AND target.type IN $target_types "

    query += (
        "WITH path, target, nodes(path) AS path_nodes, relationships(path) AS path_rels "
        "WHERE all(path_node IN path_nodes WHERE COALESCE(path_node.status, 'active') <> 'deleted'"
        f"{_path_node_scope_clause(allowed_sources)}) "
        "AND all(path_rel IN path_rels WHERE COALESCE(path_rel.status, 'active') <> 'deleted') "
        "WITH collect(DISTINCT target.external_id) AS found_ids, collect(DISTINCT path) AS paths "
        "UNWIND paths AS p "
        "UNWIND nodes(p) AS matched_node "
        "WITH found_ids, paths, collect(DISTINCT matched_node) AS matched_nodes "
        "UNWIND paths AS p "
        "UNWIND relationships(p) AS rel "
        "RETURN found_ids, matched_nodes, "
        "       collect(DISTINCT {source_id: startNode(rel).external_id, "
        "                         target_id: endNode(rel).external_id, "
        "                         type: type(rel), "
        "                         props: properties(rel)}) AS rels"
    )

    params: dict[str, Any] = {"ids": current_ids}
    if step.source_node_types:
        params["source_types"] = step.source_node_types
    if step.target_node_types:
        params["target_types"] = step.target_node_types
    params = _scope_params(params, allowed_sources)

    result = tx.run(query, **params)
    record = result.single()

    if not record:
        return StepResult(next_node_ids=[], node_ids=[], raw_edges=[])

    next_node_ids = sorted(set(record["found_ids"] or []))
    node_ids = sorted({_node_external_id(node) for node in record["matched_nodes"] or []})
    raw_edges = [
        _edge_from_payload(payload, step, step_index)
        for payload in record["rels"] or []
    ]
    raw_edges.sort(key=lambda edge: (edge["source_id"], edge["target_id"], edge["type"]))

    return StepResult(next_node_ids=next_node_ids, node_ids=node_ids, raw_edges=raw_edges)


def _empty_graph() -> GraphResponse:
    return GraphResponse(nodes=[], edges=[], node_count=0, edge_count=0)


def _scope_params(params: dict[str, Any], allowed_sources: list[str] | None) -> dict[str, Any]:
    if allowed_sources is not None:
        params["sources"] = allowed_sources
    return params


def _source_scope_clause(alias: str, allowed_sources: list[str] | None) -> str:
    if allowed_sources is None:
        return ""
    return f"AND {alias}.source IN $sources "


def _path_node_scope_clause(allowed_sources: list[str] | None) -> str:
    if allowed_sources is None:
        return ""
    return " AND path_node.source IN $sources"


def _node_external_id(node: Any) -> str:
    return node["external_id"]


def _add_node_ids(node_order: list[str], seen_node_ids: set[str], node_ids: list[str]) -> None:
    for node_id in node_ids:
        if node_id not in seen_node_ids:
            seen_node_ids.add(node_id)
            node_order.append(node_id)


def _edge_key(edge: dict[str, Any]) -> tuple[str, str, str]:
    return (edge["source_id"], edge["target_id"], edge["type"].upper())


def _edge_from_payload(
    payload: dict[str, Any],
    step: TraversalStep,
    step_index: int,
) -> dict[str, Any]:
    edge: dict[str, Any] = {
        "source_id": payload["source_id"],
        "target_id": payload["target_id"],
        "type": payload["type"],
    }
    edge.update(payload.get("props") or {})
    edge["traversal_step_index"] = step_index
    edge["traversal_step_label"] = step.label or f"Step {step_index + 1}"
    edge["traversal_direction"] = step.direction
    return edge


def _neo4j_node_to_dict(node: Any) -> dict[str, Any]:
    d = dict(node)
    d["id"] = d.pop("external_id", d.get("id"))
    return d
