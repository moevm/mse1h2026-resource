from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.export import ExportFormat, ExportRequest, ExportResponse


def test_export_request_defaults():
    r = ExportRequest()
    assert r.format == ExportFormat.JSON
    assert r.include_properties is True
    assert r.limit > 0


def test_export_request_accepts_known_formats():
    for fmt in ExportFormat:
        r = ExportRequest(format=fmt)
        assert r.format == fmt


def test_export_request_rejects_unknown_format():
    with pytest.raises(ValidationError):
        ExportRequest(format="totally-not-a-format")  # type: ignore[arg-type]


def test_export_request_rejects_zero_limit():
    with pytest.raises(ValidationError):
        ExportRequest(limit=0)


def test_export_request_rejects_excessive_limit():
    with pytest.raises(ValidationError):
        ExportRequest(limit=10_000_000)


def test_export_request_accepts_type_filters():
    r = ExportRequest(node_types=["service", "db"], edge_types=["calls"])
    assert r.node_types == ["service", "db"]
    assert r.edge_types == ["calls"]


def test_export_response_basic():
    r = ExportResponse(
        format="json",
        node_count=5,
        edge_count=4,
        filename="topology.json",
        content_type="application/json",
    )
    assert r.filename == "topology.json"
