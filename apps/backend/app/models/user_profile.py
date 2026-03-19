from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UserAuditMixin


class UserProfile(TimestampMixin, UserAuditMixin, Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        Index("idx_user_profiles_target_city", "target_city"),
        Index("idx_user_profiles_target_role", "target_role"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    job_direction: Mapped[str | None] = mapped_column(String(120), nullable=True)
    target_city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_role: Mapped[str | None] = mapped_column(String(120), nullable=True)

    user = relationship("User", back_populates="profile", foreign_keys=[user_id])
