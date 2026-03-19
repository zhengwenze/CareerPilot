"""add ai fields to resume parse jobs

Revision ID: 20260317_0007
Revises: 20260317_0006
Create Date: 2026-03-17 00:07:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260317_0007"
down_revision = "20260317_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resume_parse_jobs", sa.Column("ai_status", sa.String(length=20), nullable=True))
    op.add_column("resume_parse_jobs", sa.Column("ai_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("resume_parse_jobs", "ai_message")
    op.drop_column("resume_parse_jobs", "ai_status")
