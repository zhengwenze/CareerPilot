"""add parse artifacts json to resumes

Revision ID: 20260320_0009
Revises: 20260318_0008
Create Date: 2026-03-20 17:06:32
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260320_0009"
down_revision = "20260318_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resumes",
        sa.Column(
            "parse_artifacts_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("resumes", "parse_artifacts_json")
