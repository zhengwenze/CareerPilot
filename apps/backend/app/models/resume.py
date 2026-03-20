from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.mixins import TimestampMixin, UserAuditMixin


class Resume(TimestampMixin, UserAuditMixin, Base):
    __tablename__ = "resumes"
    __table_args__ = (
        Index("idx_resumes_user_id", "user_id"),
        Index("idx_resumes_parse_status", "parse_status"),
        Index("idx_resumes_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(120), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="application/pdf",
    )
    file_size: Mapped[int] = mapped_column(nullable=False)
    parse_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parse_artifacts_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    latest_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
