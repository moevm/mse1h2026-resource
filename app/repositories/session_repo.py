from __future__ import annotations

from app.config import settings
from app.repositories.redis_connection import redis_client

REFRESH_PREFIX = "session:refresh:"
REFRESH_REVOKED_PREFIX = "session:refresh_revoked:"
BLACKLIST_PREFIX = "session:blacklist:"


async def store_refresh_token(user_id: str, jti: str) -> None:
    client = redis_client.client
    key = f"{REFRESH_PREFIX}{user_id}:{jti}"
    ttl = settings.refresh_token_expire_days * 86400
    await client.setex(key, ttl, "1")


async def validate_refresh_token(user_id: str, jti: str) -> bool:
    """Refresh tokens are valid as long as the JWT signature/expiry holds and they
    are not explicitly revoked. We default-allow so that Redis data loss
    (or migrations from a non-persistent Redis) doesn't sign every user out."""
    client = redis_client.client
    revoked_key = f"{REFRESH_REVOKED_PREFIX}{user_id}:{jti}"
    return await client.exists(revoked_key) == 0


async def revoke_refresh_token(user_id: str, jti: str) -> None:
    client = redis_client.client
    allow_key = f"{REFRESH_PREFIX}{user_id}:{jti}"
    revoked_key = f"{REFRESH_REVOKED_PREFIX}{user_id}:{jti}"
    ttl = settings.refresh_token_expire_days * 86400
    await client.delete(allow_key)
    await client.setex(revoked_key, ttl, "1")


async def revoke_all_user_tokens(user_id: str) -> None:
    client = redis_client.client
    pattern = f"{REFRESH_PREFIX}{user_id}:*"
    async for key in client.scan_iter(match=pattern):
        await client.delete(key)


async def blacklist_access_token(jti: str, ttl_seconds: int) -> None:
    client = redis_client.client
    key = f"{BLACKLIST_PREFIX}{jti}"
    await client.setex(key, ttl_seconds, "1")


async def is_token_blacklisted(jti: str) -> bool:
    client = redis_client.client
    key = f"{BLACKLIST_PREFIX}{jti}"
    return await client.exists(key) > 0
