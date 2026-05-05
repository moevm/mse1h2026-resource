from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from app.repositories.redis_connection import redis_client

_CACHE_PREFIX = "graph:cache:"


def _make_cache_key(user_id: str, **params: Any) -> str:
    payload = json.dumps({"user_id": user_id, **params}, sort_keys=True, default=str)
    digest = hashlib.md5(payload.encode()).hexdigest()
    return f"{_CACHE_PREFIX}{user_id}:{digest}"


async def get_cached_graph(cache_key: str) -> Optional[Dict[str, Any]]:
    client = redis_client.client
    data = await client.get(cache_key)
    if data is None:
        return None
    return json.loads(data)


async def set_cached_graph(cache_key: str, data: Dict[str, Any], ttl_seconds: int = 30) -> None:
    client = redis_client.client
    await client.setex(cache_key, ttl_seconds, json.dumps(data, default=str))


async def invalidate_graph_cache(user_id: str) -> None:
    client = redis_client.client
    pattern = f"{_CACHE_PREFIX}{user_id}:*"
    async for key in client.scan_iter(match=pattern):
        await client.delete(key)
