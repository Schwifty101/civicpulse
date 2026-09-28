"""FastAPI dependency providers. Routes depend on these, never on providers/ directly."""

from fastapi import Request

from app.providers.cache import RedisCache
from app.providers.ratelimit import RedisRateLimiter
from app.providers.triage.base import TriageProvider


def get_cache() -> RedisCache:
    return RedisCache()


def get_triage_provider(request: Request) -> TriageProvider:
    return request.app.state.triage_provider


def get_rate_limiter(request: Request) -> RedisRateLimiter:
    return request.app.state.rate_limiter


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
