from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskState(BaseModel):
    status: Literal["pending", "processing", "success", "failed"] = "pending"
    phase: str = ""
    message: str = ""
    current_step: int = 0
    total_steps: int = 0
    started_at: datetime | None = None
    first_completed_at: datetime | None = None
    completed_at: datetime | None = None
    last_updated_at: datetime | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class SegmentExplanation(BaseModel):
    what: str = ""
    why: str = ""
    value: str = ""


class ContentSegment(BaseModel):
    key: str
    label: str
    sequence: int
    status: Literal["pending", "processing", "success", "failed"] = "pending"
    original_text: str = ""
    suggested_text: str = ""
    markdown: str = ""
    explanation: SegmentExplanation = Field(default_factory=SegmentExplanation)
    error_message: str | None = None
    generated_at: datetime | None = None


class ClientEventRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    occurred_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ClientEventResponse(BaseModel):
    recorded: bool = True
