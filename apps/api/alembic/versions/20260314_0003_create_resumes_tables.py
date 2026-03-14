from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260314_0003"
down_revision = "20260314_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("storage_bucket", sa.String(length=120), nullable=False),
        sa.Column("storage_object_key", sa.Text(), nullable=False),
        sa.Column(
            "content_type",
            sa.String(length=120),
            nullable=False,
            server_default="application/pdf",
        ),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("parse_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("structured_json", sa.JSON(), nullable=True),
        sa.Column("latest_version", sa.Integer(), nullable=False, server_default="1"),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_object_key"),
    )
    op.create_index("idx_resumes_created_at", "resumes", ["created_at"], unique=False)
    op.create_index("idx_resumes_parse_status", "resumes", ["parse_status"], unique=False)
    op.create_index("idx_resumes_user_id", "resumes", ["user_id"], unique=False)

    op.create_table(
        "resume_parse_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_resume_parse_jobs_resume_id",
        "resume_parse_jobs",
        ["resume_id"],
        unique=False,
    )
    op.create_index(
        "idx_resume_parse_jobs_status",
        "resume_parse_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_resume_parse_jobs_status", table_name="resume_parse_jobs")
    op.drop_index("idx_resume_parse_jobs_resume_id", table_name="resume_parse_jobs")
    op.drop_table("resume_parse_jobs")

    op.drop_index("idx_resumes_user_id", table_name="resumes")
    op.drop_index("idx_resumes_parse_status", table_name="resumes")
    op.drop_index("idx_resumes_created_at", table_name="resumes")
    op.drop_table("resumes")
