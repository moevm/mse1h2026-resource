from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.endpoint_identity import build_endpoint_urn


@dataclass
class TraceTopologyEnrichment:
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    direct_edges_to_delete: List[Dict[str, str]] = field(default_factory=list)


def _string_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _looks_like_ip(value: str) -> bool:
    stripped = value.replace(".", "").replace(":", "")
    return bool(value) and value[0].isdigit() and stripped.isdigit()


def _is_server_span(span_kind: Any) -> bool:
    kind = str(span_kind or "").upper()
    return kind in {"SPAN_KIND_SERVER", "SERVER", "2"}


def _is_client_span(span_kind: Any) -> bool:
    kind = str(span_kind or "").upper()
    return kind in {"SPAN_KIND_CLIENT", "CLIENT", "3"}


def _endpoint_name(payload: Dict[str, Any]) -> Optional[str]:
    span_name = _string_or_none(payload.get("span_name"))
    path = _string_or_none(payload.get("http_route") or payload.get("http_target"))
    method = _string_or_none(payload.get("http_method"))

    if span_name and ("/" in span_name or not path):
        return span_name
    if method and path:
        return f"{method} {path}"
    return path or span_name


def _endpoint_path(payload: Dict[str, Any], endpoint_name: str) -> str:
    return (
        _string_or_none(payload.get("http_route"))
        or _string_or_none(payload.get("http_target"))
        or endpoint_name
    )


def _service_node(service_name: str) -> Dict[str, Any]:
    return {
        "id": f"urn:service:{service_name}",
        "type": "Service",
        "name": service_name,
        "status": "active",
    }


def _endpoint_node(
    service_name: str,
    endpoint_name: str,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    endpoint_id = build_endpoint_urn(service_name, endpoint_name)
    if not endpoint_id:
        return None
    return {
        "id": endpoint_id,
        "type": "Endpoint",
        "name": endpoint_name,
        "service_name": service_name,
        "path": _endpoint_path(payload, endpoint_name),
        "method": payload.get("http_method"),
        "status": "active",
    }


def _append_endpoint_call(
    enrichment: TraceTopologyEnrichment,
    caller_service: str,
    callee_service: str,
    endpoint_name: str,
    payload: Dict[str, Any],
) -> None:
    if (
        not caller_service
        or not callee_service
        or caller_service == callee_service
        or _looks_like_ip(caller_service)
        or _looks_like_ip(callee_service)
    ):
        return

    endpoint = _endpoint_node(callee_service, endpoint_name, payload)
    if not endpoint:
        return

    enrichment.nodes.extend([_service_node(caller_service), _service_node(callee_service), endpoint])
    enrichment.edges.append(
        {
            "source_id": f"urn:service:{caller_service}",
            "target_id": endpoint["id"],
            "type": "calls",
        }
    )
    enrichment.direct_edges_to_delete.append(
        {
            "source_id": f"urn:service:{caller_service}",
            "target_id": f"urn:service:{callee_service}",
            "type": "calls",
        }
    )


def build_trace_topology_enrichment(payload: Dict[str, Any]) -> TraceTopologyEnrichment:
    enrichment = TraceTopologyEnrichment()
    if not isinstance(payload, dict):
        return enrichment

    endpoint_name = _endpoint_name(payload)
    if not endpoint_name:
        return enrichment

    service_name = _string_or_none(payload.get("service_name"))
    span_kind = payload.get("span_kind")

    caller_service = _string_or_none(payload.get("caller_service"))

    if service_name and _is_server_span(span_kind):
        if caller_service:
            _append_endpoint_call(enrichment, caller_service, service_name, endpoint_name, payload)
        else:
            endpoint = _endpoint_node(service_name, endpoint_name, payload)
            if endpoint:
                enrichment.direct_edges_to_delete.append(
                    {
                        "source_id": f"urn:service:{service_name}",
                        "target_id": endpoint["id"],
                        "type": "calls",
                    }
                )

    return enrichment


def apply_trace_topology_enrichment(
    payload: Dict[str, Any],
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> TraceTopologyEnrichment:
    enrichment = build_trace_topology_enrichment(payload)
    if not enrichment.nodes and not enrichment.edges:
        return enrichment

    replaced = {
        (edge["source_id"], edge["target_id"], edge["type"].lower())
        for edge in enrichment.direct_edges_to_delete
    }
    if replaced:
        edges[:] = [
            edge
            for edge in edges
            if (
                edge.get("source_id"),
                edge.get("target_id"),
                str(edge.get("type", "")).lower(),
            )
            not in replaced
        ]

    nodes.extend(enrichment.nodes)
    edges.extend(enrichment.edges)
    return enrichment
