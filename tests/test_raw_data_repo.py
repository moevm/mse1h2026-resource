from __future__ import annotations

import asyncio
import fnmatch
import json
from typing import Any

from app.repositories.raw_data_repo import RawDataRepository, raw_data_repo
from app.repositories.redis_connection import redis_client


def run(coro):
    return asyncio.run(coro)


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}

    async def setex(self, key: str, ttl, value: str) -> None:
        seconds = int(ttl.total_seconds()) if hasattr(ttl, "total_seconds") else int(ttl)
        self.store[key] = value
        self.ttls[key] = seconds

    async def set(self, key: str, value: str) -> None:
        self.store[key] = value
        self.ttls.setdefault(key, None)

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def sadd(self, key: str, value: str) -> None:
        values = set(json.loads(self.store.get(key, "[]")))
        values.add(value)
        self.store[key] = json.dumps(sorted(values))
        self.ttls.setdefault(key, None)

    async def srem(self, key: str, value: str) -> None:
        values = set(json.loads(self.store.get(key, "[]")))
        values.discard(value)
        self.store[key] = json.dumps(sorted(values))

    async def expire(self, key: str, ttl) -> None:
        seconds = int(ttl.total_seconds()) if hasattr(ttl, "total_seconds") else int(ttl)
        self.ttls[key] = seconds

    async def ttl(self, key: str) -> int:
        ttl = self.ttls.get(key)
        return ttl if ttl is not None else -1

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)
        self.ttls.pop(key, None)

    async def incr(self, key: str) -> int:
        current = int(self.store.get(key, "0"))
        current += 1
        self.store[key] = str(current)
        self.ttls.setdefault(key, None)
        return current

    async def scan_iter(self, match: str | None = None, count: int = 10):
        del count
        for key in sorted(self.store):
            if match is None or fnmatch.fnmatch(key, match):
                yield key


def test_build_chunk_signature_uses_recursive_paths_and_normalized_arrays():
    payload_a = {
        "kind": "metric",
        "labels": {"service": "svc-a"},
        "metrics": [{"name": "latency", "value": 1}, {"name": "rps", "value": None}],
    }
    payload_b = {
        "kind": "metric",
        "labels": {"service": "svc-b"},
        "metrics": [{"name": "latency", "value": 2}, {"name": "rps", "value": 3}],
    }
    payload_c = {
        "kind": "metric",
        "labels": {"service": "svc-b"},
        "metrics": [{"name": "latency", "value": 2, "unit": "ms"}],
    }

    sig_a, paths_a = RawDataRepository.build_chunk_signature(payload_a)
    sig_b, paths_b = RawDataRepository.build_chunk_signature(payload_b)
    sig_c, paths_c = RawDataRepository.build_chunk_signature(payload_c)

    assert sig_a == sig_b
    assert paths_a == paths_b
    assert sig_a != sig_c
    assert "metrics[].name" in paths_a
    assert "metrics[].value" in paths_a
    assert "labels.service" in paths_a
    assert "metrics[].unit" in paths_c


def test_store_chunk_assigns_stable_type_ids_and_list_filters_with_lazy_backfill(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(redis_client, "_client", fake)

    agent_a = "agent-a"
    agent_b = "agent-b"
    span_payload: dict[str, Any] = {"kind": "span", "service_name": "svc", "span_name": "op", "http_status_code": None}
    metric_payload: dict[str, Any] = {"kind": "metric", "service_name": "svc", "metrics": {"latency": 1}, "labels": {"service": "svc"}}

    chunk_a1 = run(raw_data_repo.store_chunk(agent_a, span_payload, {"agent_name": "otel"}))
    chunk_a2 = run(raw_data_repo.store_chunk(agent_a, span_payload, {"agent_name": "otel"}))
    chunk_a3 = run(raw_data_repo.store_chunk(agent_a, metric_payload, {"agent_name": "otel"}))
    chunk_b1 = run(raw_data_repo.store_chunk(agent_b, span_payload, {"agent_name": "otel"}))

    listed = run(raw_data_repo.list_chunks(agent_id=agent_a, limit=10))
    by_id = {chunk.id: chunk for chunk in listed.chunks}

    assert by_id[chunk_a1].chunk_type_id == 1
    assert by_id[chunk_a2].chunk_type_id == 1
    assert by_id[chunk_a3].chunk_type_id == 2

    other = run(raw_data_repo.list_chunks(agent_id=agent_b, limit=10))
    assert other.chunks[0].id == chunk_b1
    assert other.chunks[0].chunk_type_id == 1

    type_ids = [chunk_type.id for chunk_type in listed.chunk_types]
    assert type_ids == [1, 2]
    assert listed.chunk_types[0].chunks_count == 2
    assert listed.chunk_types[1].chunks_count == 1

    filtered = run(raw_data_repo.list_chunks(agent_id=agent_a, chunk_type_id=2, limit=10))
    assert [chunk.id for chunk in filtered.chunks] == [chunk_a3]
    assert [chunk_type.id for chunk_type in filtered.chunk_types] == [1, 2]

    legacy_chunk = {
        "id": "legacy-1",
        "agent_id": agent_a,
        "timestamp": listed.chunks[0].timestamp.isoformat(),
        "sequence": 0,
        "data": span_payload,
        "metadata": {"agent_name": "otel"},
        "size_bytes": 42,
        "is_processed": False,
        "processed_at": None,
        "mapping_id": None,
        "is_pinned": False,
    }
    legacy_key = f"{raw_data_repo.KEY_PREFIX}{agent_a}:legacy-1"
    run(fake.setex(legacy_key, raw_data_repo.ttl, json.dumps(legacy_chunk)))

    fetched = run(raw_data_repo.get_chunk("legacy-1"))
    assert fetched is not None
    assert fetched["chunk_type_id"] == 1
    assert fetched["chunk_type_kind"] == "span"

    refreshed = run(raw_data_repo.list_chunks(agent_id=agent_a, limit=20))
    refreshed_types = {chunk_type.id: chunk_type for chunk_type in refreshed.chunk_types}
    assert refreshed_types[1].chunks_count == 3
