"""Liveness/readiness/metrics. /health must NEVER touch a dependency — a slow database
must not turn into a restart loop across the whole deployment (that's what /ready is for;
Kubernetes uses the two probes for different decisions, see k8s/base/backend.yaml)."""

from fastapi import APIRouter, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.db.session import get_sessionmaker
from app.providers.cache import get_redis
from app.repositories import complaints_repo

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "alive"}


@router.get("/ready")
def ready() -> dict:
    failed: list[str] = []

    session = get_sessionmaker()()
    try:
        complaints_repo.ping(session)
    except Exception:
        failed.append("database")
    finally:
        session.close()

    try:
        get_redis().ping()
    except Exception:
        failed.append("cache")

    if failed:
        raise HTTPException(status_code=503, detail=f"not ready: {', '.join(failed)} unreachable")
    return {"status": "ready"}


@router.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
