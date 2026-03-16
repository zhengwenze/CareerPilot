from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.mixins import TimestampMixin, UserAuditMixin


class MatchReport(TimestampMixin, UserAuditMixin, Base):
    __tablename__ = "match_reports"
    __table_args__ = (
        Index("idx_match_reports_user_id", "user_id"),
        Index("idx_match_reports_jd_id", "jd_id"),
        Index("idx_match_reports_resume_id", "resume_id"),
        Index("idx_match_reports_status", "status"),
        Index("idx_match_reports_resume_jd", "resume_id", "jd_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_id: Mapped[UUID] = mapped_column(ForeignKey("resumes.id"), nullable=False)
    jd_id: Mapped[UUID] = mapped_column(ForeignKey("job_descriptions.id"), nullable=False)
    resume_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    job_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    fit_band: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    stale_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="fresh",
        server_default="fresh",
    )
    overall_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    rule_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    model_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    dimension_scores_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    gap_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    scorecard_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evidence_map_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    gap_taxonomy_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    action_pack_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    tailoring_plan_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    interview_blueprint_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
