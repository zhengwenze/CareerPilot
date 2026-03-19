from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.mixins import TimestampMixin, UserAuditMixin


class MockInterviewSession(TimestampMixin, UserAuditMixin, Base):
    __tablename__ = "mock_interview_sessions"
    __table_args__ = (
        Index("idx_mock_interview_sessions_user_id", "user_id"),
        Index("idx_mock_interview_sessions_match_report_id", "match_report_id"),
        Index("idx_mock_interview_sessions_status", "status"),
        Index("idx_mock_interview_sessions_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_id: Mapped[UUID] = mapped_column(ForeignKey("resumes.id"), nullable=False)
    jd_id: Mapped[UUID] = mapped_column(ForeignKey("job_descriptions.id"), nullable=False)
    match_report_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_reports.id"),
        nullable=False,
    )
    optimization_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("resume_optimization_sessions.id"),
        nullable=True,
    )
    source_resume_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    source_job_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="general",
        server_default="general",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )
    current_question_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    current_follow_up_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    max_questions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=6,
        server_default="6",
    )
    max_follow_ups_per_question: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    review_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    follow_up_tasks_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
