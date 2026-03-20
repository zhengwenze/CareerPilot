from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UserAuditMixin


class UserProfile(TimestampMixin, UserAuditMixin, Base):
    """
    用户画像表

    存储用户的求职偏好和目标信息，供岗位匹配模块使用。
    与 User 表为一对一关系，通过 user_id 主键关联。
    """

    __tablename__ = "user_profiles"
    __table_args__ = (
        Index("idx_user_profiles_target_city", "target_city"),
        Index("idx_user_profiles_target_role", "target_role"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    job_direction: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        doc="求职方向，如：后端开发、算法工程师、产品经理",
    )

    target_city: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        doc="目标城市，如：北京、上海、深圳",
    )

    target_role: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        doc="目标岗位名称，如：Senior Backend Engineer",
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="profile",
        foreign_keys=[user_id],
        doc="关联的 User 对象",
    )
