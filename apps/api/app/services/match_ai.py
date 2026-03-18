from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.services.ai_client import AIClientError, AIProviderConfig, request_json_completion

FIT_BANDS = ("excellent", "strong", "partial", "weak")
JSON_RESPONSE_INSTRUCTIONS = """
You are the final resume-job matching report engine.
You receive a structured resume, a structured job target, and a rule-based baseline.
Your job is to produce the final actionable match report in strict JSON.

Rules:
1. You must return strict JSON only. No markdown. No explanation outside JSON.
2. You must not invent experience, projects, skills, employers, dates, or metrics.
3. Use the rule_result only as baseline evidence and hints. Do not ignore the resume/job snapshots.
4. overall_score must be a number between 0 and 100.
5. fit_band must be one of: excellent, strong, partial, weak.
6. strengths, must_fix, should_fix, rewrite_tasks, focus_areas, question_pack, rubric
   must all be arrays. Use empty arrays when needed.
7. Keep evidence_map_json grounded in actual resume/job evidence.
8. rewrite_tasks must be specific and executable.
9. If evidence is weak, say so in notes or reasons rather than fabricating evidence.

Return JSON with exactly this shape:
{
  "overall_score": 0,
  "fit_band": "partial",
  "summary": "一句最终判断",
  "reasoning": "简短解释为何得出该判断",
  "confidence": 0.0,
  "strengths": [{"label": "string", "reason": "string", "severity": "medium"}],
  "must_fix": [{"label": "string", "reason": "string", "severity": "high"}],
  "should_fix": [{"label": "string", "reason": "string", "severity": "medium"}],
  "evidence_map_json": {
    "matched_resume_fields": {"skills": ["string"]},
    "matched_jd_fields": {"required_skills": ["string"]},
    "missing_items": ["string"],
    "notes": ["string"],
    "candidate_profile": {"skills": ["string"]}
  },
  "action_pack_json": {
    "resume_tailoring_tasks": [
      {
        "priority": 1,
        "title": "string",
        "instruction": "string",
        "target_section": "work_experience_or_projects"
      }
    ],
    "interview_focus_areas": [
      {"topic": "string", "reason": "string", "priority": "high"}
    ],
    "missing_user_inputs": [{"field": "string", "question": "string"}]
  },
  "tailoring_plan_json": {
    "target_summary": "string",
    "rewrite_tasks": [
      {
        "priority": 1,
        "title": "string",
        "instruction": "string",
        "target_section": "work_experience_or_projects"
      }
    ],
    "must_add_evidence": ["string"],
    "missing_info_questions": [{"field": "string", "question": "string"}]
  },
  "interview_blueprint_json": {
    "target_role": "string",
    "focus_areas": [{"topic": "string", "reason": "string", "priority": "high"}],
    "question_pack": [{"topic": "string", "question": "string", "intent": "string"}],
    "follow_up_rules": ["string"],
    "rubric": [{"dimension": "string", "weight": 25, "criteria": "string"}]
  }
}
""".strip()


@dataclass(slots=True)
class AIMatchReportRequest:
    resume_snapshot: dict[str, object]
    job_snapshot: dict[str, object]
    rule_result: dict[str, object]


class MatchInsightItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    severity: str = "medium"


class MatchRewriteTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: int = Field(ge=1)
    title: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    target_section: str = "work_experience_or_projects"


class MissingUserInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1)
    question: str = Field(min_length=1)


class InterviewFocusArea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    priority: str = "medium"


class InterviewQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    question: str = Field(min_length=1)
    intent: str = Field(min_length=1)


class InterviewRubricItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str = Field(min_length=1)
    weight: int = Field(ge=1)
    criteria: str = Field(min_length=1)


class MatchEvidenceMap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matched_resume_fields: dict[str, list[str]] = Field(default_factory=dict)
    matched_jd_fields: dict[str, list[str]] = Field(default_factory=dict)
    missing_items: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    candidate_profile: dict[str, Any] = Field(default_factory=dict)


class MatchActionPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_tailoring_tasks: list[MatchRewriteTask] = Field(default_factory=list)
    interview_focus_areas: list[InterviewFocusArea] = Field(default_factory=list)
    missing_user_inputs: list[MissingUserInput] = Field(default_factory=list)


class MatchTailoringPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_summary: str | None = None
    rewrite_tasks: list[MatchRewriteTask] = Field(default_factory=list)
    must_add_evidence: list[str] = Field(default_factory=list)
    missing_info_questions: list[MissingUserInput] = Field(default_factory=list)


class MatchInterviewBlueprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_role: str | None = None
    focus_areas: list[InterviewFocusArea] = Field(default_factory=list)
    question_pack: list[InterviewQuestion] = Field(default_factory=list)
    follow_up_rules: list[str] = Field(default_factory=list)
    rubric: list[InterviewRubricItem] = Field(default_factory=list)


class MatchAIReportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_score: float = Field(ge=0.0, le=100.0)
    fit_band: Literal["excellent", "strong", "partial", "weak"]
    summary: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    strengths: list[MatchInsightItem] = Field(default_factory=list)
    must_fix: list[MatchInsightItem] = Field(default_factory=list)
    should_fix: list[MatchInsightItem] = Field(default_factory=list)
    evidence_map_json: MatchEvidenceMap
    action_pack_json: MatchActionPack
    tailoring_plan_json: MatchTailoringPlan
    interview_blueprint_json: MatchInterviewBlueprint


@dataclass(slots=True)
class AIMatchReportResult:
    provider: str
    model: str | None
    status: str
    report_payload: MatchAIReportPayload | None = None


class AIMatchReportProvider:
    async def correct(self, payload: AIMatchReportRequest) -> AIMatchReportResult:
        raise NotImplementedError


class ConfiguredAIMatchReportProvider(AIMatchReportProvider):
    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def correct(self, payload: AIMatchReportRequest) -> AIMatchReportResult:
        response_json = await request_json_completion(
            config=AIProviderConfig(
                provider=self.provider,
                base_url=self.base_url,
                api_key=self.api_key,
                model=self.model,
                timeout_seconds=self.timeout_seconds,
            ),
            instructions=JSON_RESPONSE_INSTRUCTIONS,
            payload=payload,
            max_tokens=2800,
        )
        try:
            report_payload = MatchAIReportPayload.model_validate(response_json)
        except ValidationError as exc:
            raise AIClientError(
                category="invalid_response_format",
                detail=f"Match AI structured payload validation failed: {exc}",
            ) from exc

        return AIMatchReportResult(
            provider=self.provider,
            model=self.model,
            status="applied",
            report_payload=report_payload,
        )


def build_ai_match_correction_provider(settings: Settings) -> AIMatchReportProvider:
    provider = settings.match_ai_provider.strip().lower()
    if provider != "minimax":
        raise ValueError("MATCH_AI_PROVIDER must be minimax for match report generation")
    if not settings.match_ai_base_url.strip():
        raise ValueError("MATCH_AI_BASE_URL is required for match report generation")
    if not settings.match_ai_api_key or not settings.match_ai_api_key.strip():
        raise ValueError("MATCH_AI_API_KEY is required for match report generation")
    if not settings.match_ai_model or not settings.match_ai_model.strip():
        raise ValueError("MATCH_AI_MODEL is required for match report generation")

    return ConfiguredAIMatchReportProvider(
        provider=provider,
        base_url=settings.match_ai_base_url,
        api_key=settings.match_ai_api_key.strip(),
        model=settings.match_ai_model.strip(),
        timeout_seconds=settings.match_ai_timeout_seconds,
    )
