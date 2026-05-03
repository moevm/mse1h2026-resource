"""Tests for session_repo's pure logic (Redis behaviour mocked).

session_repo is a thin wrapper around redis-py. We swap the client for a
fake to verify that revocation/blacklisting logic forms the right keys
and that validate_refresh_token defaults to allow when no revocation
key exists (the desired behaviour after the blacklist-model migration).
"""
from __future__ import annotations

import asyncio
from typing import Dict
from unittest.mock import patch

import pytest


class FakeRedis:
    """Minimal subset of redis.asyncio used by session_repo."""

    def __init__(self):
        self.store: Dict[str, str] = {}

    async def setex(self, key, ttl, value):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)

    async def exists(self, key):
        return 1 if key in self.store else 0

    async def scan_iter(self, match=None):
        # naive glob: '*' suffix only
        prefix = match.rstrip("*") if match else ""
        for k in list(self.store):
            if k.startswith(prefix):
                yield k


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture(autouse=True)
def patch_redis(fake_redis):
    """Replace the singleton's `.client` attribute with our fake."""
    from app.repositories import session_repo

    class _Holder:
        client = fake_redis

    with patch.object(session_repo, "redis_client", _Holder()):
        yield


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_validate_refresh_default_allows_when_redis_empty():
    """The post-fix behaviour: if nothing is in Redis, the token is allowed
    (because we default-allow and only block explicitly revoked tokens)."""
    from app.repositories import session_repo

    assert run(session_repo.validate_refresh_token("u1", "j1")) is True


def test_revoke_then_validate_blocks(fake_redis):
    from app.repositories import session_repo

    run(session_repo.revoke_refresh_token("u1", "j1"))
    assert run(session_repo.validate_refresh_token("u1", "j1")) is False


def test_other_user_revocation_does_not_affect_this_user():
    from app.repositories import session_repo

    run(session_repo.revoke_refresh_token("user-a", "shared-jti"))
    assert run(session_repo.validate_refresh_token("user-b", "shared-jti")) is True


def test_blacklist_access_token():
    from app.repositories import session_repo

    assert run(session_repo.is_token_blacklisted("jti-x")) is False
    run(session_repo.blacklist_access_token("jti-x", ttl_seconds=60))
    assert run(session_repo.is_token_blacklisted("jti-x")) is True


def test_store_refresh_token_writes_under_correct_key(fake_redis):
    from app.repositories import session_repo

    run(session_repo.store_refresh_token("u1", "j1"))
    expected_key = f"{session_repo.REFRESH_PREFIX}u1:j1"
    assert expected_key in fake_redis.store
