import uuid

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.schemas import Category, Priority, Status

category_enum = PGEnum(
    *[c.value for c in Category], name="complaint_category", create_type=False
)
priority_enum = PGEnum(*[p.value for p in Priority], name="complaint_priority", create_type=False)
status_enum = PGEnum(*[s.value for s in Status], name="complaint_status", create_type=False)


class Complaint(Base):
    """A citizen complaint. All SQL for this table lives in repositories/, nowhere else."""

    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    text: Mapped[str] = mapped_column(String(2000), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    reporter_contact: Mapped[str | None] = mapped_column(String(200), nullable=True)

    category: Mapped[str] = mapped_column(category_enum, nullable=False)
    priority: Mapped[str] = mapped_column(priority_enum, nullable=False)
    status: Mapped[str] = mapped_column(status_enum, nullable=False, server_default=Status.OPEN)

    ai_summary: Mapped[str | None] = mapped_column(String(140), nullable=True)
    triaged_by: Mapped[str] = mapped_column(String(32), nullable=False)
    triage_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "char_length(text) >= 10 AND char_length(text) <= 2000", name="ck_text_len"
        ),
        CheckConstraint(
            "char_length(location) >= 3 AND char_length(location) <= 200", name="ck_location_len"
        ),
        CheckConstraint(
            "triaged_by IN ('llm:groq','llm:ollama','rules','rules:fallback')",
            name="ck_triaged_by",
        ),
        # Serves GET /api/complaints filtered by status and/or priority (the dashboard's
        # default "open, sorted by priority" view) — see docs/ENGINEERING-NOTES.md §D.
        Index("ix_complaints_status_priority", "status", "priority"),
        # Serves default newest-first ordering and pagination on GET /api/complaints.
        Index("ix_complaints_created_at", "created_at"),
    )
