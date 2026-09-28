"""Triage orchestration: content-hash cache, timeout/retry already inside the provider,
fallback to RuleBasedTriage on any failure, latency measurement, and the last-20 outcomes
ring buffer that backs /api/meta/providers.
"""

import hashlib
import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from app.metrics import TRIAGE_FALLBACK_COUNT, TRIAGE_LATENCY
from app.providers.cache import RedisCache
from app.providers.triage.base import TriageError, TriageProvider
from app.providers.triage.rules import RuleBasedTriage
from app.schemas import TriageResult

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 24 * 60 * 60
_OUTCOMES_KEY = "triage:outcomes"
_OUTCOMES_MAX_LEN = 20
_CACHE_COUNTER_KEY = "triage:cache:counters"  # {"hits": n, "total": n}
_CACHEABLE_PROVIDERS = {"llm:groq", "llm:ollama"}

_rule_fallback = RuleBasedTriage()


@dataclass
class TriageOutcome:
    result: TriageResult
    triaged_by: str
    latency_ms: int
    fallback: bool
    from_cache: bool


def _cache_key(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"triage:result:{digest}"


def _record_cache_lookup(cache: RedisCache, *, hit: bool) -> None:
    counters = cache.get_json(_CACHE_COUNTER_KEY) or {"hits": 0, "total": 0}
    counters["total"] += 1
    if hit:
        counters["hits"] += 1
    cache.set_json(_CACHE_COUNTER_KEY, counters, ttl_seconds=_CACHE_TTL_SECONDS)


def get_cache_hit_rate(cache: RedisCache) -> tuple[int, int, float]:
    counters = cache.get_json(_CACHE_COUNTER_KEY) or {"hits": 0, "total": 0}
    hits, total = counters["hits"], counters["total"]
    rate = round(hits / total, 4) if total else 0.0
    return hits, total, rate


def triage_complaint(
    provider: TriageProvider, cache: RedisCache, text: str, location: str
) -> TriageOutcome:
    key = _cache_key(text)
    cached = cache.get_json(key)
    _record_cache_lookup(cache, hit=cached is not None)

    if cached is not None:
        outcome = TriageOutcome(
            result=TriageResult.model_validate(cached["result"]),
            triaged_by=cached["triaged_by"],
            latency_ms=0,
            fallback=False,
            from_cache=True,
        )
        _push_outcome(cache, outcome)
        return outcome

    start = time.monotonic()
    fallback = False
    try:
        result = provider.triage(text, location)
        triaged_by = provider.name
    except TriageError as exc:
        logger.warning(
            "triage fallback to rules",
            extra={"provider": provider.name, "error_class": type(exc).__name__},
        )
        result = _rule_fallback.triage(text, location)
        triaged_by = "rules:fallback"
        fallback = True

    latency_ms = int((time.monotonic() - start) * 1000)
    TRIAGE_LATENCY.labels(provider=provider.name).observe(latency_ms / 1000)
    if fallback:
        TRIAGE_FALLBACK_COUNT.inc()

    outcome = TriageOutcome(
        result=result,
        triaged_by=triaged_by,
        latency_ms=latency_ms,
        fallback=fallback,
        from_cache=False,
    )

    if triaged_by in _CACHEABLE_PROVIDERS:
        cache.set_json(
            key,
            {"result": result.model_dump(mode="json"), "triaged_by": triaged_by},
            ttl_seconds=_CACHE_TTL_SECONDS,
        )

    _push_outcome(cache, outcome)
    return outcome


def _push_outcome(cache: RedisCache, outcome: TriageOutcome) -> None:
    cache.push_capped(
        _OUTCOMES_KEY,
        {
            "provider": outcome.triaged_by,
            "latency_ms": outcome.latency_ms,
            "fallback": outcome.fallback,
            "at": datetime.now(UTC).isoformat(),
        },
        _OUTCOMES_MAX_LEN,
    )


def recent_outcomes(cache: RedisCache) -> list[dict]:
    return cache.list_json(_OUTCOMES_KEY)
