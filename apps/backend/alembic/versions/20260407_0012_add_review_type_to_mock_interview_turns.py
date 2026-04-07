"""add review type to mock interview turns

Revision ID: 20260407_0012
Revises: 20260321_0011
Create Date: 2026-04-07 00:12:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260407_0012"
down_revision = "20260321_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mock_interview_turns",
        sa.Column(
            "review_type",
            sa.String(length=40),
            nullable=False,
            server_default="project_experience",
        ),
    )
    op.execute(
        """
        UPDATE mock_interview_turns
        SET review_type = 'project_experience'
        WHERE review_type IS NULL OR review_type = ''
        """
    )
    op.alter_column("mock_interview_turns", "review_type", server_default=None)


def downgrade() -> None:
    op.drop_column("mock_interview_turns", "review_type")
