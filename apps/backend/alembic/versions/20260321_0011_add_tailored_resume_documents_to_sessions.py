from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260321_0011"
down_revision = "20260320_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resume_optimization_sessions",
        sa.Column(
            "tailored_resume_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "resume_optimization_sessions",
        sa.Column(
            "audit_report_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "resume_optimization_sessions",
        sa.Column(
            "tailored_resume_md",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("resume_optimization_sessions", "tailored_resume_md")
    op.drop_column("resume_optimization_sessions", "audit_report_json")
    op.drop_column("resume_optimization_sessions", "tailored_resume_json")
