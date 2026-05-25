from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import require_agent
from app.api.auth import CurrentUser
from app.models.mapper.raw_data import RawDataListResponse
from app.repositories.raw_data_repo import raw_data_repo
from app.repositories.mapping_repo import mapping_repo
from app.repositories.neo4j_repo import delete_edge, upsert_nodes, upsert_edges, upsert_trace_span
from app.services.mapper_service import mapper_service
from app.services.endpoint_identity import build_endpoint_urn
from app.services.trace_service import normalize_span_payload, trace_metrics_from_span
from app.services.trace_topology import apply_trace_topology_enrichment

router = APIRouter()
log = logging.getLogger(__name__)


def _trace_caller_enrichment(
    span: Dict[str, Any],
) -> Optional[tuple[list[Dict[str, Any]], Dict[str, Any]]]:
    """Build Endpoint node + calls edge for a SERVER span that has a known caller.

    Returns (nodes, edge) or None if the span is not a server span or lacks
    the required fields.
    """
    if span.get("span_kind") != "SPAN_KIND_SERVER":
        return None
    service_name: Optional[str] = span.get("service_name")
    span_name: Optional[str] = span.get("span_name")
    caller_service: Optional[str] = span.get("caller_service")
    if not service_name or not span_name or not caller_service:
        return None

    endpoint_urn = build_endpoint_urn(service_name, span_name)
    if not endpoint_urn:
        return None

    endpoint_node: Dict[str, Any] = {
        "id": endpoint_urn,
        "type": "Endpoint",
        "name": span_name,
        "service_name": service_name,
    }
    http_route: Optional[str] = span.get("http_route")
    http_method: Optional[str] = span.get("http_method")
    if http_route:
        endpoint_node["http_route"] = http_route
    if http_method:
        endpoint_node["http_method"] = http_method

    service_node: Dict[str, Any] = {
        "id": f"urn:service:{service_name}",
        "type": "Service",
        "name": service_name,
    }

    edge: Dict[str, Any] = {
        "source_id": f"urn:service:{caller_service}",
        "target_id": endpoint_urn,
        "type": "calls",
    }

    return [endpoint_node, service_node], edge


def _extract_trace_metrics(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    span = normalize_span_payload(payload)
    if not span:
        return None
    return trace_metrics_from_span(span)


@router.post(
    "/raw",
    summary="Receive raw telemetry data",
    description="Accept any JSON format from telemetry sources. Mapping is auto-detected by trying all active mappings.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_raw_data(
    payload: Dict[str, Any],
    agent: Dict[str, Any] = Depends(require_agent),
):
    agent_name = agent.get("name", "unknown")

    chunk_id = await raw_data_repo.store_chunk(
        agent_id=agent["agent_id"],
        data=payload,
        metadata={
            "agent_name": agent_name,
        },
    )

    active_mappings = mapping_repo.list(is_active=True, limit=100).mappings

    nodes_created = 0
    edges_created = 0
    mapping_applied = False
    applied_mapping_name = None
    mapping_errors: list[dict[str, str]] = []
    trace_span = normalize_span_payload(payload)
    trace_result: Optional[Dict[str, Any]] = None
    if trace_span:
        try:
            trace_result = upsert_trace_span(trace_span, source=agent_name)
        except Exception as e:
            log.exception("Trace span persistence failed for chunk %s", chunk_id[:8])
            trace_result = {"stored": False, "reason": str(e)}

    from app.models.mapper.raw_data import RawDataChunk
    from datetime import datetime, timezone

    temp_chunk = RawDataChunk(
        id=chunk_id,
        agent_id=agent["agent_id"],
        timestamp=datetime.now(timezone.utc),
        data=payload,
    )

    for mapping in active_mappings:
        try:
            applicable = mapper_service._evaluate_conditional_rules(
                payload, mapping.conditional_rules
            )
            if not applicable and not mapping.conditional_rules:
                continue
            if not applicable:
                continue

            nodes, edges, unresolved = mapper_service.map_chunk(temp_chunk, mapping)
            topology_enrichment = apply_trace_topology_enrichment(payload, nodes, edges)
            for edge_to_delete in topology_enrichment.direct_edges_to_delete:
                try:
                    delete_edge(
                        edge_to_delete["source_id"],
                        edge_to_delete["target_id"],
                        edge_to_delete["type"],
                    )
                except Exception:
                    log.exception(
                        "Failed to delete direct edge %s -> %s (%s)",
                        edge_to_delete["source_id"],
                        edge_to_delete["target_id"],
                        edge_to_delete["type"],
                    )

            if nodes:
                upsert_nodes(nodes, source=agent_name)
                nodes_created = len(nodes)
                if trace_span:
                    trace_result = upsert_trace_span(trace_span, source=agent_name)

            if nodes:
                new_edges, new_unresolved = mapper_service.recreate_edges_for_nodes(nodes, mapping)
                edges.extend(new_edges)
                unresolved.extend(new_unresolved)

            if edges:
                trace_metrics = trace_metrics_from_span(trace_span) if trace_span else None
                upsert_edges(edges, source=agent_name, trace_metrics=trace_metrics)
                edges_created = len(edges)

            if not nodes and not edges:
                log.info(
                    "Mapping '%s' matched chunk %s but produced no nodes/edges; trying next mapping",
                    mapping.name,
                    chunk_id[:8],
                )
                continue

            mapping_applied = True
            applied_mapping_name = mapping.name

            log.info(
                f"Auto-applied mapping '{mapping.name}' to chunk {chunk_id[:8]}: "
                f"{nodes_created} nodes, {edges_created} edges"
            )
            break

        except Exception as e:
            mapping_errors.append({"mapping_name": mapping.name, "error": str(e)})
            log.exception("Error trying mapping '%s'", mapping.name)
            continue

    if not mapping_applied:
        log.warning(f"No matching mapping found for chunk {chunk_id[:8]}")

    return {
        "chunk_id": chunk_id,
        "status": "stored",
        "mapped": mapping_applied,
        "mapping_name": applied_mapping_name,
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "trace": trace_result,
        "mapping_errors": mapping_errors,
        "message": (
            f"Data stored and mapped with '{applied_mapping_name}'."
            if mapping_applied
            else "Data stored. No active mapping matched this data."
        ),
    }


@router.get(
    "/raw",
    response_model=RawDataListResponse,
    summary="List stored raw data chunks",
)
async def list_raw_data(
    user: CurrentUser,
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    chunk_type_id: Optional[int] = Query(None, ge=1, description="Filter by chunk type ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of chunks to return"),
):
    return await raw_data_repo.list_chunks(
        agent_id=agent_id,
        chunk_type_id=chunk_type_id,
        limit=limit,
    )


@router.get(
    "/raw/{chunk_id}",
    summary="Get specific raw data chunk",
)
async def get_raw_data(user: CurrentUser, chunk_id: str):
    chunk = await raw_data_repo.get_chunk(chunk_id)
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found or expired",
        )
    return chunk


@router.delete(
    "/raw/{chunk_id}",
    summary="Delete a raw data chunk",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_raw_data(user: CurrentUser, chunk_id: str):
    deleted = await raw_data_repo.delete_chunk(chunk_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found",
        )


@router.post(
    "/raw/{chunk_id}/pin",
    summary="Pin a raw data chunk so it won't expire",
)
async def pin_raw_data(user: CurrentUser, chunk_id: str):
    pinned = await raw_data_repo.pin_chunk(chunk_id)
    if not pinned:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found",
        )
    return {"chunk_id": chunk_id, "is_pinned": True}


@router.post(
    "/raw/{chunk_id}/unpin",
    summary="Unpin a raw data chunk, restoring normal TTL",
)
async def unpin_raw_data(user: CurrentUser, chunk_id: str):
    unpinned = await raw_data_repo.unpin_chunk(chunk_id)
    if not unpinned:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found",
        )
    return {"chunk_id": chunk_id, "is_pinned": False}
