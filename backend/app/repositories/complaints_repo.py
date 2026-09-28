"""All SQL for the complaints table lives here — routes and services never see SQLAlchemy."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.db.models import Complaint


def create(
    session: Session,
    *,
    text: str,
    location: str,
    reporter_contact: str | None,
    category: str,
    priority: str,
    ai_summary: str | None,
    triaged_by: str,
    triage_latency_ms: int | None,
) -> Complaint:
    complaint = Complaint(
        text=text,
        location=location,
        reporter_contact=reporter_contact,
        category=category,
        priority=priority,
        ai_summary=ai_summary,
        triaged_by=triaged_by,
        triage_latency_ms=triage_latency_ms,
    )
    session.add(complaint)
    session.commit()
    session.refresh(complaint)
    return complaint


def get_by_id(session: Session, complaint_id: uuid.UUID) -> Complaint | None:
    return session.get(Complaint, complaint_id)


def list_paginated(
    session: Session,
    *,
    category: str | None,
    priority: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Complaint], int]:
    stmt = select(Complaint)
    if category:
        stmt = stmt.where(Complaint.category == category)
    if priority:
        stmt = stmt.where(Complaint.priority == priority)
    if status:
        stmt = stmt.where(Complaint.status == status)

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    stmt = (
        stmt.order_by(Complaint.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(session.scalars(stmt).all())
    return items, total


def update_status(session: Session, complaint_id: uuid.UUID, new_status: str) -> Complaint | None:
    complaint = session.get(Complaint, complaint_id)
    if complaint is None:
        return None
    complaint.status = new_status
    complaint.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(complaint)
    return complaint


def aggregate_stats(session: Session) -> dict:
    total = session.scalar(select(func.count()).select_from(Complaint)) or 0

    by_category: dict[str, int] = dict(
        session.execute(
            select(Complaint.category, func.count()).group_by(Complaint.category)
        ).all()  # type: ignore[arg-type]
    )
    by_priority: dict[str, int] = dict(
        session.execute(
            select(Complaint.priority, func.count()).group_by(Complaint.priority)
        ).all()  # type: ignore[arg-type]
    )
    by_status: dict[str, int] = dict(
        session.execute(
            select(Complaint.status, func.count()).group_by(Complaint.status)
        ).all()  # type: ignore[arg-type]
    )
    return {
        "total": total,
        "by_category": by_category,
        "by_priority": by_priority,
        "by_status": by_status,
    }


def exists_with_text(session: Session, complaint_text: str) -> bool:
    return bool(session.scalar(select(exists().where(Complaint.text == complaint_text))))


def ping(session: Session) -> bool:
    return session.execute(select(1)).scalar_one() == 1
