from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260320_0010"
down_revision = "20260320_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resume_optimization_sessions",
        sa.Column(
            "diagnosis_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "resume_optimization_sessions",
        sa.Column(
            "rewrite_tasks_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "resume_optimization_sessions",
        sa.Column(
            "optimized_resume_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "resume_optimization_sessions",
        sa.Column(
            "fact_check_report_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "resume_optimization_sessions",
        sa.Column(
            "optimized_resume_md",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("resume_optimization_sessions", "optimized_resume_md")
    op.drop_column("resume_optimization_sessions", "fact_check_report_json")
    op.drop_column("resume_optimization_sessions", "optimized_resume_json")
    op.drop_column("resume_optimization_sessions", "rewrite_tasks_json")
    op.drop_column("resume_optimization_sessions", "diagnosis_json")
