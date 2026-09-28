"""Business rules for complaints: triage orchestration, persistence, state machine,
stats-cache invalidation on write. No SQL here — repositories/ owns that."""

import uuid

from sqlalchemy.orm import Session

from app.db.models import Complaint
from app.providers.cache import RedisCache
from app.providers.triage.base import TriageProvider
from app.repositories import complaints_repo
from app.schemas import ComplaintCreate, Status
from app.services.state_machine import assert_transition_allowed
from app.services.stats_service import invalidate_stats_cache
from app.services.triage_service import triage_complaint


def create_complaint(
    session: Session, cache: RedisCache, provider: TriageProvider, payload: ComplaintCreate
) -> Complaint:
    outcome = triage_complaint(provider, cache, payload.text, payload.location)
    complaint = complaints_repo.create(
        session,
        text=payload.text,
        location=payload.location,
        reporter_contact=payload.reporter_contact,
        category=outcome.result.category.value,
        priority=outcome.result.priority.value,
        ai_summary=outcome.result.summary,
        triaged_by=outcome.triaged_by,
        triage_latency_ms=outcome.latency_ms,
    )
    invalidate_stats_cache(cache)
    return complaint


def get_complaint(session: Session, complaint_id: uuid.UUID) -> Complaint | None:
    return complaints_repo.get_by_id(session, complaint_id)


def list_complaints(
    session: Session,
    *,
    category: str | None,
    priority: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Complaint], int]:
    return complaints_repo.list_paginated(
        session,
        category=category,
        priority=priority,
        status=status,
        page=page,
        page_size=page_size,
    )


def transition_status(
    session: Session, cache: RedisCache, complaint_id: uuid.UUID, target: Status
) -> Complaint | None:
    complaint = complaints_repo.get_by_id(session, complaint_id)
    if complaint is None:
        return None

    assert_transition_allowed(Status(complaint.status), target)
    updated = complaints_repo.update_status(session, complaint_id, target.value)
    invalidate_stats_cache(cache)
    return updated
