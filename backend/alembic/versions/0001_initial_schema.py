"""initial schema: complaints table, enums, indexes

Revision ID: 0001
Revises:
Create Date: 2026-09-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

category_values = ("water", "electricity", "sanitation", "roads", "streetlights", "other")
priority_values = ("high", "normal", "low")
status_values = ("open", "in_progress", "resolved", "rejected")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    category_enum = postgresql.ENUM(*category_values, name="complaint_category")
    priority_enum = postgresql.ENUM(*priority_values, name="complaint_priority")
    status_enum = postgresql.ENUM(*status_values, name="complaint_status")
    category_enum.create(op.get_bind())
    priority_enum.create(op.get_bind())
    status_enum.create(op.get_bind())

    # Types already created above — create_type=False stops create_table's own
    # before_create hook from trying (and failing) to CREATE TYPE a second time.
    category_enum = postgresql.ENUM(
        *category_values, name="complaint_category", create_type=False
    )
    priority_enum = postgresql.ENUM(
        *priority_values, name="complaint_priority", create_type=False
    )
    status_enum = postgresql.ENUM(*status_values, name="complaint_status", create_type=False)

    op.create_table(
        "complaints",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("text", sa.String(length=2000), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("reporter_contact", sa.String(length=200), nullable=True),
        sa.Column("category", category_enum, nullable=False),
        sa.Column("priority", priority_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="open"),
        sa.Column("ai_summary", sa.String(length=140), nullable=True),
        sa.Column("triaged_by", sa.String(length=32), nullable=False),
        sa.Column("triage_latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "char_length(text) >= 10 AND char_length(text) <= 2000", name="ck_text_len"
        ),
        sa.CheckConstraint(
            "char_length(location) >= 3 AND char_length(location) <= 200",
            name="ck_location_len",
        ),
        sa.CheckConstraint(
            "triaged_by IN ('llm:groq','llm:ollama','rules','rules:fallback')",
            name="ck_triaged_by",
        ),
    )

    # Serves GET /api/complaints filtered by status and/or priority (dashboard default view).
    op.create_index(
        "ix_complaints_status_priority", "complaints", ["status", "priority"]
    )
    # Serves newest-first ordering and pagination on GET /api/complaints.
    op.create_index("ix_complaints_created_at", "complaints", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_complaints_created_at", table_name="complaints")
    op.drop_index("ix_complaints_status_priority", table_name="complaints")
    op.drop_table("complaints")

    postgresql.ENUM(name="complaint_status").drop(op.get_bind())
    postgresql.ENUM(name="complaint_priority").drop(op.get_bind())
    postgresql.ENUM(name="complaint_category").drop(op.get_bind())
