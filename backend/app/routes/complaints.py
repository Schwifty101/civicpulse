"""HTTP only: parse, validate, serialise, status codes. No business rules — those live in
app/services/complaint_service.py."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import client_ip, get_cache, get_rate_limiter, get_triage_provider
from app.providers.cache import RedisCache
from app.providers.ratelimit import RedisRateLimiter
from app.providers.triage.base import TriageProvider
from app.schemas import (
    Category,
    ComplaintCreate,
    ComplaintListOut,
    ComplaintOut,
    Priority,
    Status,
    StatusUpdate,
)
from app.services import complaint_service
from app.services.state_machine import InvalidTransitionError

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintOut, status_code=201)
def create_complaint(
    payload: ComplaintCreate,
    ip: str = Depends(client_ip),
    db: Session = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
    provider: TriageProvider = Depends(get_triage_provider),
    limiter: RedisRateLimiter = Depends(get_rate_limiter),
) -> ComplaintOut:
    result = limiter.check(ip)
    if not result.allowed:
        # HTTPException.headers (not the injected Response) is what survives into the
        # error response — mutating `response.headers` here would be silently dropped.
        raise HTTPException(
            status_code=429,
            detail="rate limit exceeded, try again shortly",
            headers={"Retry-After": str(result.retry_after_seconds)},
        )

    complaint = complaint_service.create_complaint(db, cache, provider, payload)
    return ComplaintOut.model_validate(complaint)


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: uuid.UUID, db: Session = Depends(get_db)) -> ComplaintOut:
    complaint = complaint_service.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="complaint not found")
    return ComplaintOut.model_validate(complaint)


@router.get("", response_model=ComplaintListOut)
def list_complaints(
    category: Category | None = None,
    priority: Priority | None = None,
    status: Status | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> ComplaintListOut:
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="page_size must be between 1 and 100")

    items, total = complaint_service.list_complaints(
        db,
        category=category.value if category else None,
        priority=priority.value if priority else None,
        status=status.value if status else None,
        page=page,
        page_size=page_size,
    )
    return ComplaintListOut(
        items=[ComplaintOut.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{complaint_id}/status", response_model=ComplaintOut)
def update_status(
    complaint_id: uuid.UUID,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    cache: RedisCache = Depends(get_cache),
) -> ComplaintOut:
    try:
        complaint = complaint_service.transition_status(db, cache, complaint_id, payload.status)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if complaint is None:
        raise HTTPException(status_code=404, detail="complaint not found")
    return ComplaintOut.model_validate(complaint)
