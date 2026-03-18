"""create mock interview tables

Revision ID: 20260318_0008
Revises: 20260317_0007
Create Date: 2026-03-18 00:08:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260318_0008"
down_revision = "20260317_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mock_interview_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("jd_id", sa.Uuid(), nullable=False),
        sa.Column("match_report_id", sa.Uuid(), nullable=False),
        sa.Column("optimization_session_id", sa.Uuid(), nullable=True),
        sa.Column("source_resume_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_job_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("mode", sa.String(length=30), nullable=False, server_default="general"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("current_question_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_follow_up_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_questions", sa.Integer(), nullable=False, server_default="6"),
        sa.Column(
            "max_follow_ups_per_question",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("plan_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("review_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "follow_up_tasks_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("overall_score", sa.Numeric(precision=5, scale=2), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.ForeignKeyConstraint(["jd_id"], ["job_descriptions.id"]),
        sa.ForeignKeyConstraint(["match_report_id"], ["match_reports.id"]),
        sa.ForeignKeyConstraint(
            ["optimization_session_id"],
            ["resume_optimization_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_mock_interview_sessions_user_id",
        "mock_interview_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_mock_interview_sessions_match_report_id",
        "mock_interview_sessions",
        ["match_report_id"],
        unique=False,
    )
    op.create_index(
        "idx_mock_interview_sessions_status",
        "mock_interview_sessions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "idx_mock_interview_sessions_created_at",
        "mock_interview_sessions",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "mock_interview_turns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("question_group_index", sa.Integer(), nullable=False),
        sa.Column(
            "question_source",
            sa.String(length=30),
            nullable=False,
            server_default="blueprint",
        ),
        sa.Column("question_topic", sa.String(length=120), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_intent", sa.Text(), nullable=True),
        sa.Column(
            "question_rubric_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_latency_seconds", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="asked"),
        sa.Column("evaluation_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("decision_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("asked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["mock_interview_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_mock_interview_turns_session_id",
        "mock_interview_turns",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "idx_mock_interview_turns_turn_index",
        "mock_interview_turns",
        ["turn_index"],
        unique=False,
    )
    op.create_index(
        "idx_mock_interview_turns_question_group_index",
        "mock_interview_turns",
        ["question_group_index"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_mock_interview_turns_question_group_index",
        table_name="mock_interview_turns",
    )
    op.drop_index("idx_mock_interview_turns_turn_index", table_name="mock_interview_turns")
    op.drop_index("idx_mock_interview_turns_session_id", table_name="mock_interview_turns")
    op.drop_table("mock_interview_turns")

    op.drop_index(
        "idx_mock_interview_sessions_created_at",
        table_name="mock_interview_sessions",
    )
    op.drop_index("idx_mock_interview_sessions_status", table_name="mock_interview_sessions")
    op.drop_index(
        "idx_mock_interview_sessions_match_report_id",
        table_name="mock_interview_sessions",
    )
    op.drop_index("idx_mock_interview_sessions_user_id", table_name="mock_interview_sessions")
    op.drop_table("mock_interview_sessions")
