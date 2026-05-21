from __future__ import annotations

import base64

from app.services.trace_service import build_hops_from_spans, normalize_span_payload, summarize_trace


TRACE_ID = "0123456789abcdef0123456789abcdef"
SPAN_ID = "0123456789abcdef"


def _b64(hex_value: str) -> str:
    return base64.b64encode(bytes.fromhex(hex_value)).decode("ascii")


def test_normalize_span_payload_converts_ids_and_extracts_http_500_error():
    span = normalize_span_payload(
        {
            "kind": "span",
            "trace_id": _b64(TRACE_ID),
            "span_id": _b64(SPAN_ID),
            "service_name": "checkout",
            "span_name": "POST /pay",
            "span_kind": "SPAN_KIND_SERVER",
            "http_method": "POST",
            "http_route": "/pay",
            "http_status_code": "500",
            "start_time": "1000000000",
            "end_time": "1250000000",
        }
    )

    assert span is not None
    assert span["trace_id"] == TRACE_ID
    assert span["span_id"] == SPAN_ID
    assert span["operation_name"] == "POST /pay"
    assert span["duration_ns"] == 250000000
    assert span["error"]["is_error"] is True
    assert span["error"]["kind"] == "http_500"


def test_normalize_span_payload_does_not_mark_plain_http_404_as_error():
    span = normalize_span_payload(
        {
            "kind": "span",
            "trace_id": TRACE_ID,
            "span_id": SPAN_ID,
            "service_name": "api",
            "span_name": "GET /missing",
            "http_status_code": "404",
            "start_time": 100,
            "end_time": 200,
        }
    )

    assert span is not None
    assert span["error"]["is_error"] is False


def test_normalize_span_payload_marks_otel_error_and_timeout_as_error():
    otel_error = normalize_span_payload(
        {
            "kind": "span",
            "trace_id": TRACE_ID,
            "span_id": SPAN_ID,
            "service_name": "api",
            "span_name": "call worker",
            "otel_status_code": "STATUS_CODE_ERROR",
        }
    )
    timeout = normalize_span_payload(
        {
            "kind": "span",
            "trace_id": TRACE_ID,
            "span_id": "fedcba9876543210",
            "service_name": "api",
            "span_name": "call worker",
            "error_message": "deadline timeout while waiting for worker",
        }
    )

    assert otel_error is not None
    assert timeout is not None
    assert otel_error["error"]["is_error"] is True
    assert timeout["error"]["is_error"] is True


def test_summarize_trace_and_build_hops_from_saved_spans():
    spans = [
        {
            "trace_id": TRACE_ID,
            "span_id": "rootrootroot0001",
            "parent_span_id": None,
            "service_name": "gateway",
            "span_name": "POST /checkout",
            "operation_name": "POST /checkout",
            "span_kind": "SPAN_KIND_SERVER",
            "start_time_ns": 1_000_000_000,
            "end_time_ns": 1_500_000_000,
            "duration_ns": 500_000_000,
            "error": {"is_error": False, "kind": None, "message": None},
            "attributes": {},
        },
        {
            "trace_id": TRACE_ID,
            "span_id": "childchild000001",
            "parent_span_id": "rootrootroot0001",
            "service_name": "payments",
            "span_name": "POST /charge",
            "operation_name": "POST /charge",
            "span_kind": "SPAN_KIND_SERVER",
            "start_time_ns": 1_100_000_000,
            "end_time_ns": 1_400_000_000,
            "duration_ns": 300_000_000,
            "error": {"is_error": True, "kind": "http_500", "message": "boom"},
            "attributes": {},
        },
    ]

    summary = summarize_trace(TRACE_ID, spans)
    hops = build_hops_from_spans(spans)

    assert summary["span_count"] == 2
    assert summary["error_count"] == 1
    assert summary["service_count"] == 2
    assert summary["duration_ms"] == 500
    assert any(hop["caller_service"] == "gateway" and hop["callee_service"] == "payments" for hop in hops)
    assert any(hop["callee_kind"] == "Endpoint" and hop["is_error"] is True for hop in hops)