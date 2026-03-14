from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from redis.asyncio import Redis


class TokenBlocklist(Protocol):
    async def add(self, jti: str, expires_at: datetime) -> None: ...
    async def contains(self, jti: str) -> bool: ...


class InMemoryTokenBlocklist:
    def __init__(self) -> None:
        self._items: dict[str, datetime] = {}

    def _cleanup(self) -> None:
        now = datetime.now(UTC)
        expired = [jti for jti, expires_at in self._items.items() if expires_at <= now]
        for jti in expired:
            self._items.pop(jti, None)

    async def add(self, jti: str, expires_at: datetime) -> None:
        self._cleanup()
        self._items[jti] = expires_at

    async def contains(self, jti: str) -> bool:
        self._cleanup()
        return jti in self._items


class RedisTokenBlocklist:
    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client

    @staticmethod
    def _key(jti: str) -> str:
        return f"auth:blocklist:{jti}"

    async def add(self, jti: str, expires_at: datetime) -> None:
        ttl = int((expires_at - datetime.now(UTC)).total_seconds())
        ttl = max(ttl, 1)
        await self.redis.set(self._key(jti), "1", ex=ttl)

    async def contains(self, jti: str) -> bool:
        return bool(await self.redis.exists(self._key(jti)))
