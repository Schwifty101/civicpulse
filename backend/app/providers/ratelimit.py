"""Distributed fixed-window rate limiter, keyed by client IP, backed by Redis.

Must live in Redis rather than an in-process counter: the moment the HPA scales the
backend to N pods, an in-process limiter would let N times the configured rate through,
because each pod would count independently. Redis INCR is the shared, atomic counter.
"""

import time
from dataclasses import dataclass

import redis


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int


class RedisRateLimiter:
    def __init__(self, client: redis.Redis, limit_per_minute: int) -> None:
        self._r = client
        self._limit = limit_per_minute

    def check(self, client_ip: str) -> RateLimitResult:
        window = int(time.time() // 60)
        key = f"ratelimit:{client_ip}:{window}"

        pipe = self._r.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, 60, nx=True)
        count, _ = pipe.execute()

        seconds_into_window = int(time.time()) % 60
        retry_after = 60 - seconds_into_window

        if count > self._limit:
            return RateLimitResult(allowed=False, retry_after_seconds=retry_after)
        return RateLimitResult(allowed=True, retry_after_seconds=0)
