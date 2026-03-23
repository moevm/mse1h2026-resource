from __future__ import annotations

import redis.asyncio as redis

from app.config import settings


class RedisConnection:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password or None,
                db=0,
                decode_responses=True,
            )
        return self._client

    async def ping(self) -> bool:
        try:
            return await self.client.ping()
        except redis.ConnectionError:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


redis_client = RedisConnection()