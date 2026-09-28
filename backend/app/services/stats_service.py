"""Read-through cache for /api/stats. TTL 30s AND explicit invalidation on every write —
see docs/adr/0002 or docs/ENGINEERING-NOTES.md for why both: the TTL is the backstop for
writes this process didn't know about (another replica, a direct DB fix), and the
invalidation is what makes a citizen's own just-submitted complaint show up immediately
instead of up to 30s later.
"""

from sqlalchemy.orm import Session

from app.providers.cache import RedisCache
from app.repositories import complaints_repo

_STATS_CACHE_KEY = "stats:snapshot"
_STATS_TTL_SECONDS = 30


def get_stats(session: Session, cache: RedisCache) -> tuple[dict, bool]:
    """Returns (stats, cache_hit)."""
    cached = cache.get_json(_STATS_CACHE_KEY)
    if cached is not None:
        return cached, True

    stats = complaints_repo.aggregate_stats(session)
    cache.set_json(_STATS_CACHE_KEY, stats, ttl_seconds=_STATS_TTL_SECONDS)
    return stats, False


def invalidate_stats_cache(cache: RedisCache) -> None:
    cache.delete(_STATS_CACHE_KEY)
