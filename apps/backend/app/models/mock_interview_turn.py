from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.mixins import TimestampMixin, UserAuditMixin


class MockInterviewTurn(TimestampMixin, UserAuditMixin, Base):
    __tablename__ = "mock_interview_turns"
    __table_args__ = (
        Index("idx_mock_interview_turns_session_id", "session_id"),
        Index("idx_mock_interview_turns_turn_index", "turn_index"),
        Index("idx_mock_interview_turns_question_group_index", "question_group_index"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("mock_interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_group_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="blueprint",
        server_default="blueprint",
    )
    question_topic: Mapped[str] = mapped_column(String(120), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_rubric_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_latency_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="asked",
        server_default="asked",
    )
    evaluation_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    decision_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    asked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(nullable=True)
