from app.providers.cache import RedisCache
from app.services.stats_service import get_stats, invalidate_stats_cache


def test_first_call_is_miss_second_is_hit(db_session, redis_client):
    cache = RedisCache(redis_client)
    _, hit1 = get_stats(db_session, cache)
    _, hit2 = get_stats(db_session, cache)
    assert hit1 is False
    assert hit2 is True


def test_invalidate_forces_next_call_to_miss(db_session, redis_client):
    cache = RedisCache(redis_client)
    get_stats(db_session, cache)
    invalidate_stats_cache(cache)
    _, hit = get_stats(db_session, cache)
    assert hit is False
