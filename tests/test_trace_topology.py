from __future__ import annotations

import base64
from datetime import datetime, timezone

from app.api.receiver import _trace_caller_enrichment
from app.api.timeline import _build_hops_from_trace
from app.models.mapper.raw_data import RawDataChunk
from app.repositories.mapping_template_repo import mapping_template_repo
from app.services.mapper_service import mapper_service


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def test_trace_caller_enrichment_targets_endpoint():
    enriched = _trace_caller_enrichment(
        {
            "caller_service": "frontend",
            "service_name": "orders",
            "span_name": "POST /orders",
            "span_kind": "SPAN_KIND_SERVER",
            "http_route": "/orders",
            "http_method": "POST",
        }
    )

    assert enriched is not None
    nodes, edge = enriched

    endpoint = next(node for node in nodes if node["type"] == "Endpoint")
    assert endpoint["id"] == "urn:endpoint:orders:POST /orders"
    assert endpoint["service_name"] == "orders"
    assert edge == {
        "source_id": "urn:service:frontend",
        "target_id": "urn:endpoint:orders:POST /orders",
        "type": "calls",
    }


def test_build_hops_from_trace_uses_endpoint_for_cross_service_server_span():
    trace_id = b"\x10" * 16
    client_span_id = b"\x20" * 8
    server_span_id = b"\x30" * 8

    trace = {
        "batches": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "frontend"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": _b64(trace_id),
                                "spanId": _b64(client_span_id),
                                "name": "call orders",
                                "kind": "SPAN_KIND_CLIENT",
                                "startTimeUnixNano": "1000000000",
                                "endTimeUnixNano": "2000000000",
                                "attributes": [],
                            }
                        ]
                    }
                ],
            },
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "orders"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": _b64(trace_id),
                                "spanId": _b64(server_span_id),
                                "parentSpanId": _b64(client_span_id),
                                "name": "POST /orders",
                                "kind": "SPAN_KIND_SERVER",
                                "startTimeUnixNano": "1500000000",
                                "endTimeUnixNano": "1800000000",
                                "attributes": [],
                            }
                        ]
                    }
                ],
            },
        ]
    }

    hops = _build_hops_from_trace(trace)["hops"]

    assert len(hops) == 1
    assert hops[0]["caller_service"] == "frontend"
    assert hops[0]["callee_service"] == "POST /orders"
    assert hops[0]["callee_kind"] == "Endpoint"
    assert hops[0]["callee_id"] == "urn:endpoint:orders:POST /orders"
    assert hops[0]["callee_owner_service"] == "orders"


def test_active_otel_template_builds_service_scoped_endpoint_ids():
    mapping = mapping_template_repo.get("watcher-otel-traces-v1")
    assert mapping is not None

    chunk = RawDataChunk(
        id="chunk-1",
        agent_id="agent-1",
        timestamp=datetime.now(timezone.utc),
        data={
            "kind": "span",
            "service_name": "orders",
            "span_name": "POST /orders",
            "http_route": "/orders",
            "span_kind": "SPAN_KIND_SERVER",
        },
    )

    nodes, _, _ = mapper_service.map_chunk(chunk, mapping)
    endpoint = next(node for node in nodes if node["type"] == "Endpoint")
    service = next(node for node in nodes if node["type"] == "Service")

    assert endpoint["id"] == "urn:endpoint:orders:POST /orders"
    assert endpoint["service_name"] == service["name"] == "orders"
    assert "calls_services" not in service or service["calls_services"] is None
