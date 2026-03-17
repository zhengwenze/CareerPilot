from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260317_0006"
down_revision = "20260316_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_optimization_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("jd_id", sa.Uuid(), nullable=False),
        sa.Column("match_report_id", sa.Uuid(), nullable=False),
        sa.Column("source_resume_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_job_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("applied_resume_version", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column(
            "tailoring_plan_snapshot_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "draft_sections_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "selected_tasks_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["jd_id"], ["job_descriptions.id"]),
        sa.ForeignKeyConstraint(["match_report_id"], ["match_reports.id"]),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_resume_optimization_sessions_user_id",
        "resume_optimization_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_resume_optimization_sessions_report_id",
        "resume_optimization_sessions",
        ["match_report_id"],
        unique=False,
    )
    op.create_index(
        "idx_resume_optimization_sessions_status",
        "resume_optimization_sessions",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_resume_optimization_sessions_status",
        table_name="resume_optimization_sessions",
    )
    op.drop_index(
        "idx_resume_optimization_sessions_report_id",
        table_name="resume_optimization_sessions",
    )
    op.drop_index(
        "idx_resume_optimization_sessions_user_id",
        table_name="resume_optimization_sessions",
    )
    op.drop_table("resume_optimization_sessions")
