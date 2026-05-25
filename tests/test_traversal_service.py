from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.models.traversal import PRESET_RULES, VALID_TRAVERSAL_EDGE_TYPES, TraversalRule
from app.services import traversal_service


class FakeResult:
    def __init__(self, records: list[dict[str, Any]]):
        self.records = records

    def single(self) -> dict[str, Any] | None:
        return self.records[0] if self.records else None

    def __iter__(self):
        return iter(self.records)


class FakeTx:
    def __init__(self) -> None:
        self.nodes = {
            "svc-a": {"external_id": "svc-a", "type": "Service", "name": "A", "status": "active"},
            "svc-b": {"external_id": "svc-b", "type": "Service", "name": "B", "status": "active"},
            "svc-c": {"external_id": "svc-c", "type": "Service", "name": "C", "status": "active"},
        }
        self.traversed_edges = [
            {"source_id": "svc-a", "target_id": "svc-b", "type": "CALLS", "props": {"status": "active"}},
            {"source_id": "svc-b", "target_id": "svc-c", "type": "CALLS", "props": {"status": "active"}},
        ]
        self.extra_edges = [
            {"source_id": "svc-a", "target_id": "svc-c", "type": "CALLS", "props": {"status": "active"}},
        ]

    def run(self, query: str, **params: Any) -> FakeResult:
        if "RETURN collect(n) AS starts" in query:
            return FakeResult([{"starts": [self.nodes["svc-a"]]}])

        if "MATCH path =" in query:
            return FakeResult([
                {
                    "found_ids": ["svc-b", "svc-c"],
                    "matched_nodes": [self.nodes["svc-a"], self.nodes["svc-b"], self.nodes["svc-c"]],
                    "rels": self.traversed_edges,
                }
            ])

        if "RETURN collect(DISTINCT target.external_id) AS found_ids" in query:
            return FakeResult([{"found_ids": ["svc-b", "svc-c"]}])

        if "RETURN n" in query:
            ids = params["ids"]
            return FakeResult([{"n": self.nodes[node_id]} for node_id in ids])

        if "MATCH (a:Resource)-[rel]->(b:Resource)" in query:
            return FakeResult(self.traversed_edges + self.extra_edges)

        return FakeResult([])


def test_traversal_returns_only_edges_from_matched_paths() -> None:
    rule = TraversalRule(
        name="Service chain",
        start_node_types=["Service"],
        steps=[
            {
                "edge_types": ["calls"],
                "direction": "outgoing",
                "target_node_types": ["Service"],
                "min_depth": 1,
                "max_depth": 2,
            }
        ],
        limit=20,
    )

    result = traversal_service._execute_rule_tx(FakeTx(), rule)

    assert {(edge.source_id, edge.target_id, edge.type) for edge in result.edges} == {
        ("svc-a", "svc-b", "calls"),
        ("svc-b", "svc-c", "calls"),
    }
    assert {edge.properties["traversal_step_index"] for edge in result.edges} == {0}
    assert {edge.properties["traversal_direction"] for edge in result.edges} == {"outgoing"}


def test_presets_are_generic_and_use_supported_edge_types() -> None:
    serialized = str(PRESET_RULES)

    assert "Payments" not in serialized
    for preset in PRESET_RULES:
        for step in preset["steps"]:
            assert step.get("source_node_types")
            assert set(step["edge_types"]) <= VALID_TRAVERSAL_EDGE_TYPES


def test_traversal_rule_rejects_unknown_edge_types() -> None:
    with pytest.raises(ValueError, match="Unsupported traversal edge types"):
        TraversalRule(
            name="Unsupported aliases",
            start_node_types=["SecretConfig"],
            steps=[{"edge_types": ["usedby"], "direction": "outgoing"}],
        )


def test_default_edge_preset_uses_supported_edge_types() -> None:
    default_preset = json.loads(Path("edge_presets/default.json").read_text(encoding="utf-8"))

    edge_types = {rule["edge_type"] for rule in default_preset["rules"]}

    assert edge_types <= VALID_TRAVERSAL_EDGE_TYPES