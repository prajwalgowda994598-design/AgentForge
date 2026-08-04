"""
AgentForge – Redis Service
============================
LOCAL_DEV=true  → Uses fakeredis (in-process, no Redis server needed)
LOCAL_DEV=false → Connects to a real Redis instance

FakeRedis is API-compatible with redis.asyncio so all callers work unchanged.
"""

import json
import os
from typing import Any, Optional

from agentforge.backend.core.config import settings
from agentforge.backend.core.logging import get_logger

logger = get_logger(__name__)

_LOCAL_DEV = os.getenv("LOCAL_DEV", "true").lower() in ("true", "1", "yes")

# Module-level singleton
_redis_client = None


async def get_redis_client():
    """Return the shared Redis connection (real or fake depending on LOCAL_DEV)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if _LOCAL_DEV:
        # Use fakeredis — no Redis server needed
        try:
            # fakeredis >= 2.x — async client lives at fakeredis.aioredis
            import fakeredis
            _redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
            logger.info("redis_fakeredis_started", mode="local_dev")
        except Exception:
            try:
                # Older fakeredis — try legacy import path
                import fakeredis.aioredis as _fakeredis_async
                _redis_client = _fakeredis_async.FakeRedis(decode_responses=True)
                logger.info("redis_fakeredis_legacy_started", mode="local_dev")
            except Exception:
                # Fallback: minimal dict-based mock if fakeredis not installed
                logger.warning("fakeredis_not_installed", fallback="dict_mock")
                _redis_client = _DictRedis()
    else:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info("redis_connected", url=settings.REDIS_URL)

    return _redis_client


async def close_redis() -> None:
    """Gracefully close the Redis connection."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None
        logger.info("redis_closed")


class _DictRedis:
    """
    Minimal async dict-based Redis stand-in.
    Used only when fakeredis is not available.
    Supports get/set/delete/exists/ping/pipeline.
    """

    def __init__(self):
        self._store: dict = {}
        self._expiry: dict = {}

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    async def incr(self, key: str) -> int:
        val = int(self._store.get(key, 0)) + 1
        self._store[key] = str(val)
        return val

    async def expire(self, key: str, ttl: int) -> None:
        pass

    async def aclose(self) -> None:
        pass

    def pipeline(self) -> "_DictPipeline":
        return _DictPipeline(self)


class _DictPipeline:
    def __init__(self, parent: _DictRedis):
        self._parent = parent
        self._cmds: list = []

    def incr(self, key: str):
        self._cmds.append(("incr", key))
        return self

    def expire(self, key: str, ttl: int):
        self._cmds.append(("expire", key, ttl))
        return self

    async def execute(self) -> list:
        results = []
        for cmd in self._cmds:
            if cmd[0] == "incr":
                results.append(await self._parent.incr(cmd[1]))
            elif cmd[0] == "expire":
                results.append(None)
        return results


class CacheService:
    """High-level cache operations wrapping the Redis client."""

    def __init__(self, client):
        self._client = client

    async def get(self, key: str) -> Optional[Any]:
        raw = await self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        serialised = json.dumps(value, default=str)
        if ttl is not None:
            await self._client.setex(key, ttl, serialised)
        else:
            await self._client.set(key, serialised)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(key))

    async def set_session_state(self, session_id: str, state: dict, ttl: int = 3600) -> None:
        await self.set(f"session:{session_id}:state", state, ttl=ttl)

    async def get_session_state(self, session_id: str) -> Optional[dict]:
        return await self.get(f"session:{session_id}:state")

    async def cache_research_result(self, query_hash: str, result: dict, ttl: int = settings.REDIS_TTL) -> None:
        await self.set(f"research:{query_hash}", result, ttl=ttl)

    async def get_cached_research(self, query_hash: str) -> Optional[dict]:
        return await self.get(f"research:{query_hash}")

    async def increment_rate_limit(self, identifier: str, window: int = 60) -> int:
        key = f"rate:{identifier}"
        pipe = self._client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        results = await pipe.execute()
        return int(results[0])
