"""Redis client + a thin generic cache interface. Two consumers, one connection pool:
services/stats_service.py (read-through cache) and providers/ratelimit.py (rate limiter).
"""

import json
from typing import Any

import redis

from app.config import get_settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


def dispose_redis() -> None:
    global _client
    if _client is not None:
        _client.close()
    _client = None


class RedisCache:
    def __init__(self, client: redis.Redis | None = None) -> None:
        self._r = client or get_redis()

    def get_json(self, key: str) -> Any | None:
        raw = self._r.get(key)  # sync client; redis-py's stubs are overloaded for async too
        return json.loads(raw) if raw is not None else None  # type: ignore[arg-type]

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._r.set(key, json.dumps(value), ex=ttl_seconds)

    def delete(self, key: str) -> None:
        self._r.delete(key)

    def push_capped(self, key: str, value: Any, max_len: int) -> None:
        """LPUSH + LTRIM — a shared ring buffer so /api/meta/providers is correct
        across multiple backend replicas, not just the one that served the request."""
        pipe = self._r.pipeline()
        pipe.lpush(key, json.dumps(value))
        pipe.ltrim(key, 0, max_len - 1)
        pipe.execute()

    def list_json(self, key: str) -> list[Any]:
        return [json.loads(v) for v in self._r.lrange(key, 0, -1)]  # type: ignore[union-attr]

    def ping(self) -> bool:
        return bool(self._r.ping())
