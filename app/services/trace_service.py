from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.endpoint_identity import build_endpoint_urn


_HEX_CHARS = set("0123456789abcdefABCDEF")
_ERROR_STATUS_VALUES = {"error", "status_code_error", "2"}
_TIMEOUT_MARKERS = ("timeout", "timed out", "deadline", "cancelled", "canceled", "connection reset")


def normalize_trace_id(value: Any) -> Optional[str]:
    return _normalize_otel_id(value, expected_hex_lengths={32})


def normalize_span_id(value: Any) -> Optional[str]:
    return _normalize_otel_id(value, expected_hex_lengths={16})


def normalize_span_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None

    is_span = payload.get("kind") == "span" or payload.get("trace_id") is not None
    if not is_span:
        return None

    trace_id = normalize_trace_id(payload.get("trace_id") or payload.get("traceId"))
    span_id = normalize_span_id(payload.get("span_id") or payload.get("spanId"))
    parent_span_id = normalize_span_id(payload.get("parent_span_id") or payload.get("parentSpanId"))
    if not trace_id or not span_id:
        return None

    start_time_ns = _coerce_int(payload.get("start_time") or payload.get("startTimeUnixNano"))
    end_time_ns = _coerce_int(payload.get("end_time") or payload.get("endTimeUnixNano"))
    duration_ns = max(0, (end_time_ns or 0) - (start_time_ns or 0)) if start_time_ns and end_time_ns else 0
    timestamp = _timestamp_from_ns(start_time_ns)

    http_status_code = _coerce_int(_first_present(payload, "http_status_code", "http.status_code"))
    otel_status_code = _string_or_none(_first_present(payload, "otel_status_code", "status_code"))
    otel_status_message = _string_or_none(_first_present(payload, "otel_status_message", "status_message"))
    error_kind = _string_or_none(
        _first_present(
            payload,
            "error_kind",
            "error.type",
            "exception_type",
            "exception.type",
            "status_code",
        )
    )
    error_message = _string_or_none(
        _first_present(
            payload,
            "error_message",
            "error.message",
            "exception_message",
            "exception.message",
            "status_message",
        )
    ) or otel_status_message

    is_error = _is_strict_error(
        http_status_code=http_status_code,
        otel_status_code=otel_status_code,
        error_kind=error_kind,
        error_message=error_message,
    )
    if is_error and not error_kind:
        error_kind = _derive_error_kind(http_status_code, otel_status_code, error_message)

    service_name = _string_or_none(payload.get("service_name"))
    span_name = _string_or_none(payload.get("span_name")) or ""
    span_kind = _string_or_none(payload.get("span_kind") or payload.get("kind"))

    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "service_name": service_name,
        "span_name": span_name,
        "operation_name": _operation_name(payload, span_name),
        "span_kind": span_kind,
        "caller_service": _string_or_none(payload.get("caller_service")),
        "caller_span_kind": _string_or_none(payload.get("caller_span_kind")),
        "start_time_ns": int(start_time_ns or 0),
        "end_time_ns": int(end_time_ns or 0),
        "duration_ns": duration_ns,
        "timestamp": timestamp,
        "http_method": _string_or_none(payload.get("http_method")),
        "http_route": _string_or_none(payload.get("http_route")),
        "http_target": _string_or_none(payload.get("http_target")),
        "http_status_code": http_status_code,
        "db_system": _string_or_none(payload.get("db_system")),
        "db_name": _string_or_none(payload.get("db_name")),
        "db_table": _string_or_none(payload.get("db_table")),
        "db_operation": _string_or_none(payload.get("db_operation")),
        "messaging_destination": _string_or_none(payload.get("messaging_destination")),
        "messaging_operation": _string_or_none(payload.get("messaging_operation")),
        "rpc_service": _string_or_none(payload.get("rpc_service")),
        "rpc_method": _string_or_none(payload.get("rpc_method")),
        "peer_service": _string_or_none(payload.get("peer_service")),
        "error": {
            "is_error": is_error,
            "kind": error_kind,
            "message": error_message,
        },
        "attributes": _span_attributes(payload),
    }


def trace_metrics_from_span(span: Dict[str, Any]) -> Dict[str, Any]:
    error = span.get("error") or {}
    return {
        "trace_id": span.get("trace_id"),
        "span_id": span.get("span_id"),
        "timestamp": span.get("timestamp"),
        "start_time_ns": span.get("start_time_ns", 0),
        "end_time_ns": span.get("end_time_ns", 0),
        "duration_ns": span.get("duration_ns", 0),
        "is_error": bool(error.get("is_error")),
        "error_kind": error.get("kind"),
        "error_message": error.get("message"),
    }


def build_hops_from_spans(spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not spans:
        return []

    by_id = {str(sp.get("span_id")): sp for sp in spans if sp.get("span_id")}
    children: Dict[str, List[str]] = {}
    roots: List[str] = []
    for sid, sp in by_id.items():
        parent_id = sp.get("parent_span_id")
        if parent_id and parent_id in by_id:
            children.setdefault(parent_id, []).append(sid)
        else:
            roots.append(sid)

    for parent_id in children:
        children[parent_id].sort(key=lambda child_id: int(by_id[child_id].get("start_time_ns") or 0))
    roots.sort(key=lambda span_id: int(by_id[span_id].get("start_time_ns") or 0))

    starts = [int(sp.get("start_time_ns") or 0) for sp in spans if int(sp.get("start_time_ns") or 0) > 0]
    base = min(starts) if starts else 0
    hops: List[Dict[str, Any]] = []

    def is_server_span(span_kind: Optional[str]) -> bool:
        kind = str(span_kind or "").upper()
        return kind in {"SPAN_KIND_SERVER", "SERVER", "2"}

    def emit(
        caller: Optional[str],
        callee: Optional[str],
        kind: str,
        sp: Dict[str, Any],
        *,
        callee_id: Optional[str] = None,
        callee_owner_service: Optional[str] = None,
    ) -> None:
        if not caller or not callee or caller == callee:
            return
        start_ns = int(sp.get("start_time_ns") or 0)
        duration_ns = int(sp.get("duration_ns") or 0)
        error = sp.get("error") or {}
        hop = {
            "caller_service": caller,
            "callee_service": callee,
            "callee_kind": kind,
            "span_name": sp.get("span_name") or "",
            "span_id": sp.get("span_id"),
            "start_offset_ms": max(0, (start_ns - base) // 1_000_000) if base and start_ns else 0,
            "duration_ms": duration_ns // 1_000_000 if duration_ns > 0 else 0,
            "is_error": bool(error.get("is_error")),
            "error_kind": error.get("kind"),
            "error_message": error.get("message"),
        }
        if callee_id:
            hop["callee_id"] = callee_id
        if callee_owner_service:
            hop["callee_owner_service"] = callee_owner_service
        hops.append(hop)

    def visit(span_id: str, ancestor_service: Optional[str]) -> None:
        sp = by_id[span_id]
        service = sp.get("service_name")
        span_kind = str(sp.get("span_kind") or "")
        cross_service = bool(service and ancestor_service and service != ancestor_service)
        if cross_service:
            if is_server_span(span_kind) and service and sp.get("span_name"):
                endpoint_id = build_endpoint_urn(str(service), str(sp.get("span_name")))
                if endpoint_id:
                    emit(
                        ancestor_service,
                        service,
                        "Endpoint",
                        sp,
                        callee_id=endpoint_id,
                        callee_owner_service=service,
                    )
                else:
                    emit(ancestor_service, service, "Service", sp)
            else:
                emit(ancestor_service, service, "Service", sp)

        if is_server_span(span_kind) and service and sp.get("span_name") and not cross_service:
            endpoint_id = build_endpoint_urn(str(service), str(sp.get("span_name")))
            emit(
                service,
                sp.get("span_name"),
                "Endpoint",
                sp,
                callee_id=endpoint_id,
                callee_owner_service=service,
            )

        if span_kind == "SPAN_KIND_CLIENT" and service and not children.get(span_id):
            peer = sp.get("peer_service")
            if peer and peer != service:
                emit(service, peer, "Service", sp)

        if service:
            if sp.get("db_system") and sp.get("db_name"):
                emit(service, sp.get("db_name"), "Database", sp)
            if sp.get("db_table"):
                emit(service, sp.get("db_table"), "Table", sp)
            if sp.get("messaging_destination"):
                emit(service, sp.get("messaging_destination"), "QueueTopic", sp)

        next_ancestor = service or ancestor_service
        for child_id in children.get(span_id, []):
            visit(child_id, next_ancestor)

    for root_id in roots:
        visit(root_id, None)

    return hops


def summarize_trace(trace_id: str, spans: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not spans:
        return {
            "trace_id": trace_id,
            "root_service": "",
            "root_name": "",
            "start_time": None,
            "duration_ms": 0,
            "span_count": 0,
            "error_count": 0,
            "hop_count": 0,
            "service_count": 0,
            "services_involved": [],
            "has_errors": False,
        }

    ordered = sorted(spans, key=lambda sp: int(sp.get("start_time_ns") or 0))
    root = next((sp for sp in ordered if not sp.get("parent_span_id")), ordered[0])
    starts = [int(sp.get("start_time_ns") or 0) for sp in ordered if int(sp.get("start_time_ns") or 0) > 0]
    ends = [int(sp.get("end_time_ns") or 0) for sp in ordered if int(sp.get("end_time_ns") or 0) > 0]
    duration_ns = max(0, max(ends) - min(starts)) if starts and ends else sum(int(sp.get("duration_ns") or 0) for sp in ordered)
    hops = build_hops_from_spans(ordered)
    services = sorted({sp.get("service_name") for sp in ordered if sp.get("service_name")})
    error_count = sum(1 for sp in ordered if bool((sp.get("error") or {}).get("is_error")))

    return {
        "trace_id": trace_id,
        "root_service": root.get("service_name") or "",
        "root_name": root.get("span_name") or root.get("operation_name") or "",
        "start_time": _timestamp_from_ns(min(starts)) if starts else None,
        "duration_ms": duration_ns // 1_000_000 if duration_ns > 0 else 0,
        "span_count": len(ordered),
        "error_count": error_count,
        "hop_count": len(hops),
        "service_count": len(services),
        "services_involved": services,
        "has_errors": error_count > 0,
    }


def _normalize_otel_id(value: Any, expected_hex_lengths: set[int]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    compact = text.replace("-", "").lower()
    if len(compact) in expected_hex_lengths and all(ch in _HEX_CHARS for ch in compact):
        return compact

    for candidate in (text, _pad_base64(text)):
        try:
            decoded = base64.b64decode(candidate, validate=False)
        except (binascii.Error, ValueError):
            continue
        hex_value = decoded.hex()
        if len(hex_value) in expected_hex_lengths:
            return hex_value

    return compact


def _pad_base64(value: str) -> str:
    return value + ("=" * (-len(value) % 4))


def _coerce_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _timestamp_from_ns(value: Optional[int]) -> Optional[str]:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _first_present(payload: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return None


def _string_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_strict_error(
    http_status_code: Optional[int],
    otel_status_code: Optional[str],
    error_kind: Optional[str],
    error_message: Optional[str],
) -> bool:
    if http_status_code is not None and http_status_code >= 500:
        return True
    if otel_status_code and otel_status_code.strip().lower() in _ERROR_STATUS_VALUES:
        return True
    haystack = " ".join(part for part in (error_kind, error_message) if part).lower()
    return any(marker in haystack for marker in _TIMEOUT_MARKERS)


def _derive_error_kind(
    http_status_code: Optional[int],
    otel_status_code: Optional[str],
    error_message: Optional[str],
) -> Optional[str]:
    if http_status_code is not None and http_status_code >= 500:
        return f"http_{http_status_code}"
    if otel_status_code:
        return otel_status_code
    if error_message:
        lower = error_message.lower()
        for marker in _TIMEOUT_MARKERS:
            if marker in lower:
                return marker.replace(" ", "_")
    return None


def _operation_name(payload: Dict[str, Any], span_name: str) -> str:
    method = _string_or_none(payload.get("http_method"))
    route = _string_or_none(payload.get("http_route") or payload.get("http_target"))
    if method and route:
        return f"{method} {route}"
    if route:
        return route
    db_operation = _string_or_none(payload.get("db_operation"))
    if db_operation:
        return db_operation
    rpc_service = _string_or_none(payload.get("rpc_service"))
    rpc_method = _string_or_none(payload.get("rpc_method"))
    if rpc_service and rpc_method:
        return f"{rpc_service}/{rpc_method}"
    if rpc_method:
        return rpc_method
    messaging_operation = _string_or_none(payload.get("messaging_operation"))
    messaging_destination = _string_or_none(payload.get("messaging_destination"))
    if messaging_operation and messaging_destination:
        return f"{messaging_operation} {messaging_destination}"
    return span_name


def _span_attributes(payload: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {
        "service_version",
        "service_environment",
        "sdk_language",
        "sdk_name",
        "http_method",
        "http_route",
        "http_target",
        "http_status_code",
        "db_system",
        "db_name",
        "db_table",
        "db_operation",
        "messaging_destination",
        "messaging_operation",
        "rpc_service",
        "rpc_method",
        "peer_service",
        "cache_name",
        "external_api",
    }
    return {key: payload.get(key) for key in allowed if payload.get(key) not in (None, "")}
