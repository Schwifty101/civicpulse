from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_cache
from app.providers.cache import RedisCache
from app.schemas import StatsOut
from app.services.stats_service import get_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def stats(
    response: Response, db: Session = Depends(get_db), cache: RedisCache = Depends(get_cache)
) -> StatsOut:
    data, hit = get_stats(db, cache)
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return StatsOut(**data)
