from app.providers.ratelimit import RedisRateLimiter


def test_allows_up_to_limit_then_blocks(redis_client):
    limiter = RedisRateLimiter(redis_client, limit_per_minute=2)
    ip = "10.0.0.1"

    assert limiter.check(ip).allowed is True
    assert limiter.check(ip).allowed is True
    result = limiter.check(ip)
    assert result.allowed is False
    assert result.retry_after_seconds > 0


def test_different_ips_have_independent_counters(redis_client):
    limiter = RedisRateLimiter(redis_client, limit_per_minute=1)
    assert limiter.check("10.0.0.1").allowed is True
    assert limiter.check("10.0.0.2").allowed is True  # different IP, own counter
