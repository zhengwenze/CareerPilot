from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260316_0005"
down_revision = "20260315_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_descriptions",
        sa.Column("latest_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "job_descriptions",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "job_descriptions",
        sa.Column("status_stage", sa.String(length=40), nullable=False, server_default="draft"),
    )
    op.add_column("job_descriptions", sa.Column("recommended_resume_id", sa.Uuid(), nullable=True))
    op.add_column("job_descriptions", sa.Column("latest_match_report_id", sa.Uuid(), nullable=True))
    op.add_column(
        "job_descriptions",
        sa.Column("parse_confidence", sa.Numeric(precision=4, scale=2), nullable=True),
    )
    op.add_column(
        "job_descriptions",
        sa.Column("competency_graph_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )

    op.create_table(
        "job_parse_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["job_id"], ["job_descriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_job_parse_jobs_job_id", "job_parse_jobs", ["job_id"], unique=False)
    op.create_index("idx_job_parse_jobs_status", "job_parse_jobs", ["status"], unique=False)

    op.create_table(
        "job_readiness_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=True),
        sa.Column("match_report_id", sa.Uuid(), nullable=True),
        sa.Column("status_from", sa.String(length=40), nullable=True),
        sa.Column("status_to", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
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
        sa.ForeignKeyConstraint(["job_id"], ["job_descriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_report_id"], ["match_reports.id"]),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_job_readiness_events_job_id",
        "job_readiness_events",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "idx_job_readiness_events_status_to",
        "job_readiness_events",
        ["status_to"],
        unique=False,
    )

    op.add_column(
        "match_reports",
        sa.Column("resume_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "match_reports",
        sa.Column("job_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "match_reports",
        sa.Column("fit_band", sa.String(length=20), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "match_reports",
        sa.Column("stale_status", sa.String(length=20), nullable=False, server_default="fresh"),
    )
    op.add_column(
        "match_reports",
        sa.Column("scorecard_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "match_reports",
        sa.Column("evidence_map_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "match_reports",
        sa.Column("gap_taxonomy_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "match_reports",
        sa.Column("action_pack_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "match_reports",
        sa.Column("tailoring_plan_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "match_reports",
        sa.Column(
            "interview_blueprint_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("match_reports", "interview_blueprint_json")
    op.drop_column("match_reports", "tailoring_plan_json")
    op.drop_column("match_reports", "action_pack_json")
    op.drop_column("match_reports", "gap_taxonomy_json")
    op.drop_column("match_reports", "evidence_map_json")
    op.drop_column("match_reports", "scorecard_json")
    op.drop_column("match_reports", "stale_status")
    op.drop_column("match_reports", "fit_band")
    op.drop_column("match_reports", "job_version")
    op.drop_column("match_reports", "resume_version")

    op.drop_index("idx_job_readiness_events_status_to", table_name="job_readiness_events")
    op.drop_index("idx_job_readiness_events_job_id", table_name="job_readiness_events")
    op.drop_table("job_readiness_events")

    op.drop_index("idx_job_parse_jobs_status", table_name="job_parse_jobs")
    op.drop_index("idx_job_parse_jobs_job_id", table_name="job_parse_jobs")
    op.drop_table("job_parse_jobs")

    op.drop_column("job_descriptions", "competency_graph_json")
    op.drop_column("job_descriptions", "parse_confidence")
    op.drop_column("job_descriptions", "latest_match_report_id")
    op.drop_column("job_descriptions", "recommended_resume_id")
    op.drop_column("job_descriptions", "status_stage")
    op.drop_column("job_descriptions", "priority")
    op.drop_column("job_descriptions", "latest_version")
