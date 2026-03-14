from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260315_0004"
down_revision = "20260314_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_descriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("job_city", sa.String(length=120), nullable=True),
        sa.Column("employment_type", sa.String(length=50), nullable=True),
        sa.Column("source_name", sa.String(length=80), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("parse_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("structured_json", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_job_descriptions_created_at",
        "job_descriptions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "idx_job_descriptions_parse_status",
        "job_descriptions",
        ["parse_status"],
        unique=False,
    )
    op.create_index("idx_job_descriptions_user_id", "job_descriptions", ["user_id"], unique=False)

    op.create_table(
        "match_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("jd_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("overall_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0"),
        sa.Column("rule_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0"),
        sa.Column("model_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0"),
        sa.Column("dimension_scores_json", sa.JSON(), nullable=False),
        sa.Column("gap_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["jd_id"], ["job_descriptions.id"]),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_match_reports_jd_id", "match_reports", ["jd_id"], unique=False)
    op.create_index(
        "idx_match_reports_resume_id",
        "match_reports",
        ["resume_id"],
        unique=False,
    )
    op.create_index(
        "idx_match_reports_resume_jd",
        "match_reports",
        ["resume_id", "jd_id"],
        unique=False,
    )
    op.create_index("idx_match_reports_status", "match_reports", ["status"], unique=False)
    op.create_index("idx_match_reports_user_id", "match_reports", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_match_reports_user_id", table_name="match_reports")
    op.drop_index("idx_match_reports_status", table_name="match_reports")
    op.drop_index("idx_match_reports_resume_jd", table_name="match_reports")
    op.drop_index("idx_match_reports_resume_id", table_name="match_reports")
    op.drop_index("idx_match_reports_jd_id", table_name="match_reports")
    op.drop_table("match_reports")

    op.drop_index("idx_job_descriptions_user_id", table_name="job_descriptions")
    op.drop_index("idx_job_descriptions_parse_status", table_name="job_descriptions")
    op.drop_index("idx_job_descriptions_created_at", table_name="job_descriptions")
    op.drop_table("job_descriptions")
