from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import settings
from app.models.mapper.raw_data import ChunkTypeSummary, RawDataChunk, RawDataListResponse
from app.repositories.redis_connection import redis_client


class RawDataRepository:
    KEY_PREFIX = "raw:chunk:"
    INDEX_KEY = "raw:index"
    TYPE_COUNTER_PREFIX = "raw:chunktype:counter:"
    TYPE_SIG_PREFIX = "raw:chunktype:sig:"
    TYPE_META_PREFIX = "raw:chunktype:meta:"

    @property
    def ttl(self) -> timedelta:
        return timedelta(hours=settings.raw_data_ttl_hours)

    @staticmethod
    def _normalize_array_path(prefix: str) -> str:
        return f"{prefix}[]" if prefix else "[]"

    @classmethod
    def build_chunk_paths(cls, payload: Any) -> List[str]:
        paths: Set[str] = set()

        def visit(value: Any, prefix: str) -> None:
            if isinstance(value, dict):
                if not value and prefix:
                    paths.add(prefix)
                    return
                for key, nested in value.items():
                    child = f"{prefix}.{key}" if prefix else str(key)
                    visit(nested, child)
                return

            if isinstance(value, list):
                array_path = cls._normalize_array_path(prefix)
                if not value:
                    paths.add(array_path)
                    return
                for nested in value:
                    visit(nested, array_path)
                return

            if prefix:
                paths.add(prefix)

        visit(payload, "")
        return sorted(paths)

    @classmethod
    def build_chunk_signature(cls, payload: Dict[str, Any]) -> Tuple[str, List[str]]:
        paths = cls.build_chunk_paths(payload)
        signature = "\n".join(paths)
        digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()
        return digest, paths

    @staticmethod
    def build_chunk_type_label(type_id: int, kind: Optional[str], paths_count: int, chunks_count: int) -> str:
        safe_kind = kind or "unknown"
        return f"#{type_id} {safe_kind} ({paths_count} paths, {chunks_count} chunks)"

    @classmethod
    def _type_counter_key(cls, agent_id: str) -> str:
        return f"{cls.TYPE_COUNTER_PREFIX}{agent_id}"

    @classmethod
    def _type_sig_key(cls, agent_id: str, signature_hash: str) -> str:
        return f"{cls.TYPE_SIG_PREFIX}{agent_id}:{signature_hash}"

    @classmethod
    def _type_meta_key(cls, agent_id: str, type_id: int) -> str:
        return f"{cls.TYPE_META_PREFIX}{agent_id}:{type_id}"

    @staticmethod
    async def _persist_json_with_ttl(client, key: str, payload: Dict[str, Any], ttl_seconds: Optional[int]) -> None:
        if ttl_seconds is None:
            await client.set(key, json.dumps(payload, default=str))
        else:
            await client.setex(key, timedelta(seconds=ttl_seconds), json.dumps(payload, default=str))

    async def _read_chunk_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        client = redis_client.client
        data = await client.get(key)
        if not data:
            return None
        chunk = json.loads(data)
        if chunk.get("chunk_type_id") is None:
            ttl = await client.ttl(key)
            ttl_seconds = ttl if ttl > 0 else None
            chunk = await self._ensure_chunk_type_for_chunk(chunk, ttl_seconds=ttl_seconds, key=key)
        else:
            meta = await self._load_type_meta(chunk["agent_id"], int(chunk["chunk_type_id"]))
            if meta:
                chunk["chunk_type_kind"] = meta.get("kind")
                chunk["chunk_type_label"] = meta.get("label")
        return chunk

    async def _load_type_meta(self, agent_id: str, type_id: int) -> Optional[Dict[str, Any]]:
        client = redis_client.client
        data = await client.get(self._type_meta_key(agent_id, type_id))
        if not data:
            return None
        return json.loads(data)

    async def _register_chunk_type(
        self,
        agent_id: str,
        payload: Dict[str, Any],
        timestamp: datetime,
    ) -> Dict[str, Any]:
        client = redis_client.client
        signature_hash, paths = self.build_chunk_signature(payload)
        sig_key = self._type_sig_key(agent_id, signature_hash)
        existing_id = await client.get(sig_key)
        kind = payload.get("kind") if isinstance(payload, dict) else None
        paths_count = len(paths)

        if existing_id is not None:
            type_id = int(existing_id)
            meta_key = self._type_meta_key(agent_id, type_id)
            meta_raw = await client.get(meta_key)
            if meta_raw:
                meta = json.loads(meta_raw)
            else:
                meta = {
                    "id": type_id,
                    "kind": kind,
                    "paths_count": paths_count,
                    "chunks_count": 0,
                    "first_seen_at": timestamp.isoformat(),
                    "last_seen_at": timestamp.isoformat(),
                    "signature_hash": signature_hash,
                }
            meta["kind"] = meta.get("kind") or kind
            meta["paths_count"] = paths_count
            meta["chunks_count"] = int(meta.get("chunks_count", 0)) + 1
            meta["last_seen_at"] = timestamp.isoformat()
            meta["label"] = self.build_chunk_type_label(
                type_id,
                meta.get("kind"),
                paths_count,
                int(meta["chunks_count"]),
            )
            await client.set(meta_key, json.dumps(meta, default=str))
            return meta

        type_id = int(await client.incr(self._type_counter_key(agent_id)))
        meta = {
            "id": type_id,
            "kind": kind,
            "paths_count": paths_count,
            "chunks_count": 1,
            "first_seen_at": timestamp.isoformat(),
            "last_seen_at": timestamp.isoformat(),
            "signature_hash": signature_hash,
        }
        meta["label"] = self.build_chunk_type_label(type_id, kind, paths_count, 1)
        await client.set(sig_key, str(type_id))
        await client.set(self._type_meta_key(agent_id, type_id), json.dumps(meta, default=str))
        return meta

    async def _ensure_chunk_type_for_chunk(
        self,
        chunk: Dict[str, Any],
        ttl_seconds: Optional[int],
        key: Optional[str] = None,
    ) -> Dict[str, Any]:
        agent_id = chunk["agent_id"]
        timestamp_raw = chunk.get("timestamp")
        if isinstance(timestamp_raw, str):
            timestamp = datetime.fromisoformat(timestamp_raw)
        else:
            timestamp = datetime.utcnow()
        meta = await self._register_chunk_type(agent_id, chunk.get("data", {}), timestamp)
        chunk["chunk_type_id"] = int(meta["id"])
        chunk["chunk_type_kind"] = meta.get("kind")
        chunk["chunk_type_label"] = meta.get("label")

        if key is not None:
            client = redis_client.client
            await self._persist_json_with_ttl(client, key, chunk, ttl_seconds)

        return chunk

    async def _collect_chunks_for_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        client = redis_client.client
        chunks: List[Dict[str, Any]] = []
        pattern = f"{self.KEY_PREFIX}{agent_id}:*"
        async for key in client.scan_iter(match=pattern, count=200):
            chunk = await self._read_chunk_by_key(key)
            if chunk:
                chunks.append(chunk)
        return chunks

    async def _list_chunk_type_summaries(self, agent_id: str) -> List[ChunkTypeSummary]:
        client = redis_client.client
        out: List[ChunkTypeSummary] = []
        pattern = f"{self.TYPE_META_PREFIX}{agent_id}:*"
        async for key in client.scan_iter(match=pattern, count=100):
            raw = await client.get(key)
            if not raw:
                continue
            meta = json.loads(raw)
            out.append(
                ChunkTypeSummary(
                    id=int(meta["id"]),
                    kind=meta.get("kind"),
                    label=meta.get("label") or self.build_chunk_type_label(
                        int(meta["id"]),
                        meta.get("kind"),
                        int(meta.get("paths_count", 0)),
                        int(meta.get("chunks_count", 0)),
                    ),
                    paths_count=int(meta.get("paths_count", 0)),
                    chunks_count=int(meta.get("chunks_count", 0)),
                    first_seen_at=datetime.fromisoformat(meta["first_seen_at"]),
                    last_seen_at=datetime.fromisoformat(meta["last_seen_at"]),
                )
            )
        out.sort(key=lambda item: item.id)
        return out

    async def store_chunk(
        self,
        agent_id: str,
        data: Dict[str, Any],
        metadata: Dict[str, Any],
        is_pinned: bool = False,
    ) -> str:
        chunk_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        key = f"{self.KEY_PREFIX}{agent_id}:{chunk_id}"

        chunk_data = {
            "id": chunk_id,
            "agent_id": agent_id,
            "timestamp": timestamp.isoformat(),
            "sequence": 0,
            "data": data,
            "metadata": metadata,
            "size_bytes": len(json.dumps(data)),
            "is_processed": False,
            "processed_at": None,
            "mapping_id": None,
            "is_pinned": is_pinned,
        }
        type_meta = await self._register_chunk_type(agent_id, data, timestamp)
        chunk_data["chunk_type_id"] = int(type_meta["id"])
        chunk_data["chunk_type_kind"] = type_meta.get("kind")
        chunk_data["chunk_type_label"] = type_meta.get("label")

        # Pinned chunks get a much longer TTL (1 year)
        ttl = timedelta(days=365) if is_pinned else self.ttl

        client = redis_client.client
        await client.setex(
            key,
            ttl,
            json.dumps(chunk_data, default=str),
        )
        await client.sadd(self.INDEX_KEY, chunk_id)
        await client.expire(self.INDEX_KEY, self.ttl)

        return chunk_id

    async def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        client = redis_client.client
        pattern = f"{self.KEY_PREFIX}*:{chunk_id}"
        async for key in client.scan_iter(match=pattern, count=1):
            return await self._read_chunk_by_key(key)
        return None

    async def list_chunks(
        self,
        agent_id: Optional[str] = None,
        chunk_type_id: Optional[int] = None,
        limit: int = 100,
    ) -> RawDataListResponse:
        client = redis_client.client
        chunks: List[Dict[str, Any]] = []
        chunk_types: List[ChunkTypeSummary] = []

        if agent_id:
            all_chunks = await self._collect_chunks_for_agent(agent_id)
            chunk_types = await self._list_chunk_type_summaries(agent_id)
            chunks = all_chunks
        else:
            pattern = f"{self.KEY_PREFIX}*"
            async for key in client.scan_iter(match=pattern, count=max(200, limit * 2)):
                chunk = await self._read_chunk_by_key(key)
                if chunk:
                    chunks.append(chunk)

        if chunk_type_id is not None:
            chunks = [chunk for chunk in chunks if int(chunk.get("chunk_type_id") or -1) == int(chunk_type_id)]

        chunks.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        total = len(chunks)
        chunks = chunks[:limit]

        timeline_min = None
        timeline_max = None
        if chunks:
            timestamps = [
                datetime.fromisoformat(c["timestamp"])
                for c in chunks
                if c.get("timestamp")
            ]
            if timestamps:
                timeline_min = min(timestamps)
                timeline_max = max(timestamps)

        return RawDataListResponse(
            chunks=[RawDataChunk(**c) for c in chunks],
            total=total,
            timeline_min=timeline_min,
            timeline_max=timeline_max,
            chunk_types=chunk_types,
        )

    async def mark_processed(
        self,
        chunk_id: str,
        mapping_id: str,
    ) -> bool:
        chunk = await self.get_chunk(chunk_id)
        if not chunk:
            return False

        chunk["is_processed"] = True
        chunk["processed_at"] = datetime.utcnow().isoformat()
        chunk["mapping_id"] = mapping_id

        client = redis_client.client
        pattern = f"{self.KEY_PREFIX}*:{chunk_id}"
        async for key in client.scan_iter(match=pattern, count=1):
            ttl = await client.ttl(key)
            if ttl > 0:
                await client.setex(key, timedelta(seconds=ttl), json.dumps(chunk, default=str))
            return True
        return False

    async def delete_chunk(self, chunk_id: str) -> bool:
        client = redis_client.client
        pattern = f"{self.KEY_PREFIX}*:{chunk_id}"
        async for key in client.scan_iter(match=pattern, count=1):
            await client.delete(key)
            await client.srem(self.INDEX_KEY, chunk_id)
            return True
        return False

    async def pin_chunk(self, chunk_id: str) -> bool:
        """Pin a chunk so it doesn't expire. Returns True if found."""
        chunk = await self.get_chunk(chunk_id)
        if not chunk:
            return False

        chunk["is_pinned"] = True

        client = redis_client.client
        pattern = f"{self.KEY_PREFIX}*:{chunk_id}"
        async for key in client.scan_iter(match=pattern, count=1):
            await client.setex(key, timedelta(days=365), json.dumps(chunk, default=str))
            return True
        return False

    async def unpin_chunk(self, chunk_id: str) -> bool:
        """Unpin a chunk, restoring normal TTL. Returns True if found."""
        chunk = await self.get_chunk(chunk_id)
        if not chunk:
            return False

        chunk["is_pinned"] = False

        client = redis_client.client
        pattern = f"{self.KEY_PREFIX}*:{chunk_id}"
        async for key in client.scan_iter(match=pattern, count=1):
            await client.setex(key, self.ttl, json.dumps(chunk, default=str))
            return True
        return False

    async def get_timeline_bounds(
        self,
        agent_id: str,
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        response = await self.list_chunks(agent_id=agent_id, limit=1000)
        return response.timeline_min, response.timeline_max


raw_data_repo = RawDataRepository()
