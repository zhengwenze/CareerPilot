from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.mixins import TimestampMixin, UserAuditMixin


class JobReadinessEvent(TimestampMixin, UserAuditMixin, Base):
    __tablename__ = "job_readiness_events"
    __table_args__ = (
        Index("idx_job_readiness_events_job_id", "job_id"),
        Index("idx_job_readiness_events_status_to", "status_to"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_id: Mapped[UUID | None] = mapped_column(ForeignKey("resumes.id"), nullable=True)
    match_report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("match_reports.id"),
        nullable=True,
    )
    status_from: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status_to: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
