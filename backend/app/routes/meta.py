from fastapi import APIRouter, Depends, Request

from app.deps import get_cache
from app.providers.cache import RedisCache
from app.schemas import ProvidersOut, TriageOutcome
from app.services.triage_service import get_cache_hit_rate, recent_outcomes

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/providers", response_model=ProvidersOut)
def providers(request: Request, cache: RedisCache = Depends(get_cache)) -> ProvidersOut:
    hits, total, rate = get_cache_hit_rate(cache)
    return ProvidersOut(
        active_provider=request.app.state.settings.triage_provider,
        recent_outcomes=[TriageOutcome(**o) for o in recent_outcomes(cache)],
        triage_cache_hits=hits,
        triage_cache_lookups=total,
        triage_cache_hit_rate=rate,
    )
