from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.mixins import TimestampMixin, UserAuditMixin


class ResumeOptimizationSession(TimestampMixin, UserAuditMixin, Base):
    __tablename__ = "resume_optimization_sessions"
    __table_args__ = (
        Index("idx_resume_optimization_sessions_user_id", "user_id"),
        Index("idx_resume_optimization_sessions_report_id", "match_report_id"),
        Index("idx_resume_optimization_sessions_status", "status"),
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
    applied_resume_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    tailoring_plan_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    draft_sections_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    selected_tasks_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
