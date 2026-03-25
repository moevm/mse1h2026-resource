from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.mapper.raw_data import RawDataChunk, RawDataSource, RawDataListResponse
from app.repositories.redis_connection import redis_client


class RawDataRepository:
    KEY_PREFIX = "raw:chunk:"
    INDEX_KEY = "raw:index"

    @property
    def ttl(self) -> timedelta:
        return timedelta(hours=settings.raw_data_ttl_hours)

    async def store_chunk(
        self,
        agent_id: str,
        source_type: RawDataSource,
        data: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> str:
        chunk_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        key = f"{self.KEY_PREFIX}{agent_id}:{chunk_id}"

        chunk_data = {
            "id": chunk_id,
            "agent_id": agent_id,
            "source_type": source_type.value,
            "timestamp": timestamp.isoformat(),
            "sequence": 0,
            "data": data,
            "metadata": metadata,
            "size_bytes": len(json.dumps(data)),
            "is_processed": False,
            "processed_at": None,
            "mapping_id": None,
        }

        client = redis_client.client
        await client.setex(
            key,
            self.ttl,
            json.dumps(chunk_data, default=str),
        )
        await client.sadd(self.INDEX_KEY, chunk_id)
        await client.expire(self.INDEX_KEY, self.ttl)

        return chunk_id

    async def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        client = redis_client.client
        pattern = f"{self.KEY_PREFIX}*:{chunk_id}"
        keys = []
        async for key in client.scan_iter(match=pattern, count=1):
            keys.append(key)

        if not keys:
            return None

        data = await client.get(keys[0])
        if data:
            return json.loads(data)
        return None

    async def list_chunks(
        self,
        agent_id: Optional[str] = None,
        source_type: Optional[RawDataSource] = None,
        limit: int = 100,
    ) -> RawDataListResponse:
        client = redis_client.client
        chunks: List[Dict[str, Any]] = []

        if agent_id:
            pattern = f"{self.KEY_PREFIX}{agent_id}:*"
        else:
            pattern = f"{self.KEY_PREFIX}*"

        async for key in client.scan_iter(match=pattern, count=limit * 2):
            data = await client.get(key)
            if data:
                chunk = json.loads(data)
                if source_type is None or chunk.get("source_type") == source_type.value:
                    chunks.append(chunk)

        chunks.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
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
            total=len(chunks),
            timeline_min=timeline_min,
            timeline_max=timeline_max,
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

    async def get_timeline_bounds(
        self,
        agent_id: str,
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        response = await self.list_chunks(agent_id=agent_id, limit=1000)
        return response.timeline_min, response.timeline_max


raw_data_repo = RawDataRepository()
