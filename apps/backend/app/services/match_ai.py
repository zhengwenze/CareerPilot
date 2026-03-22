from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.prompts.match import (
    get_match_report_generation_prompt,
    get_match_report_repair_prompt,
)
from app.services.ai_client import AIClientError, AIProviderConfig, request_json_completion

FIT_BANDS = ("excellent", "strong", "partial", "weak")
CORE_REQUIRED_FIELDS = ("overall_score", "fit_band", "summary", "reasoning")


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


def _has_null_required_core_fields(response_json: dict[str, object]) -> bool:
    for field in CORE_REQUIRED_FIELDS:
        value = response_json.get(field)
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
    return False


def _normalize_insight_items(
    items: object,
    *,
    default_severity: str,
) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            normalized.append(
                {
                    "label": text,
                    "reason": text,
                    "severity": default_severity,
                }
            )
            continue

        if not isinstance(item, dict):
            continue

        label = str(item.get("label") or item.get("title") or "").strip()
        reason = str(item.get("reason") or item.get("description") or label).strip()
        if not label or not reason:
            continue
        normalized.append(
            {
                "label": label,
                "reason": reason,
                "severity": str(item.get("severity") or default_severity).strip()
                or default_severity,
            }
        )
    return normalized


def _normalize_rewrite_tasks(items: object) -> list[dict[str, object]]:
    if not isinstance(items, list):
        return []

    normalized: list[dict[str, object]] = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            normalized.append(
                {
                    "priority": index,
                    "title": text,
                    "instruction": text,
                    "target_section": "work_experience_or_projects",
                }
            )
            continue

        if not isinstance(item, dict):
            continue

        title = str(item.get("title") or item.get("label") or "").strip()
        instruction = str(
            item.get("instruction") or item.get("description") or item.get("reason") or title
        ).strip()
        if not title or not instruction:
            continue
        normalized.append(
            {
                "priority": max(1, int(item.get("priority") or index)),
                "title": title,
                "instruction": instruction,
                "target_section": str(
                    item.get("target_section") or "work_experience_or_projects"
                ).strip()
                or "work_experience_or_projects",
            }
        )
    return normalized


def _normalize_focus_areas(items: object) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            normalized.append({"topic": text, "reason": text, "priority": "medium"})
            continue

        if not isinstance(item, dict):
            continue

        topic = str(item.get("topic") or item.get("label") or "").strip()
        reason = str(item.get("reason") or item.get("description") or topic).strip()
        if not topic or not reason:
            continue
        normalized.append(
            {
                "topic": topic,
                "reason": reason,
                "priority": str(item.get("priority") or "medium").strip() or "medium",
            }
        )
    return normalized


def _normalize_missing_user_inputs(items: object) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []

    normalized: list[dict[str, str]] = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            normalized.append({"field": f"missing_input_{index}", "question": text})
            continue

        if not isinstance(item, dict):
            continue

        field = str(item.get("field") or f"missing_input_{index}").strip()
        question = str(item.get("question") or item.get("reason") or "").strip()
        if not question:
            continue
        normalized.append({"field": field, "question": question})
    return normalized


def _normalize_questions(items: object) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            normalized.append({"topic": text, "question": text, "intent": text})
            continue

        if not isinstance(item, dict):
            continue

        topic = str(item.get("topic") or item.get("dimension") or "").strip()
        question = str(item.get("question") or item.get("criteria") or "").strip()
        intent = str(item.get("intent") or question or topic).strip()
        if not topic or not question or not intent:
            continue
        normalized.append({"topic": topic, "question": question, "intent": intent})
    return normalized


def _normalize_rubric(items: object) -> list[dict[str, object]]:
    if not isinstance(items, list):
        return []

    normalized: list[dict[str, object]] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            normalized.append({"dimension": text, "weight": 25, "criteria": text})
            continue

        if not isinstance(item, dict):
            continue

        dimension = str(item.get("dimension") or item.get("topic") or "").strip()
        criteria = str(item.get("criteria") or item.get("question") or "").strip()
        if not dimension or not criteria:
            continue
        normalized.append(
            {
                "dimension": dimension,
                "weight": max(1, int(item.get("weight") or 25)),
                "criteria": criteria,
            }
        )
    return normalized


def _normalize_match_ai_response(response_json: dict[str, object]) -> dict[str, object]:
    evidence_map = response_json.get("evidence_map_json")
    if not isinstance(evidence_map, dict):
        evidence_map = {}
    evidence_map = {
        "matched_resume_fields": evidence_map.get("matched_resume_fields", {}),
        "matched_jd_fields": evidence_map.get("matched_jd_fields", {}),
        "missing_items": evidence_map.get("missing_items", []),
        "notes": evidence_map.get("notes", []),
        "candidate_profile": evidence_map.get(
            "candidate_profile", response_json.get("candidate_profile", {})
        ),
    }

    rewrite_tasks = _normalize_rewrite_tasks(
        response_json.get("rewrite_tasks")
        or response_json.get("resume_tailoring_tasks")
        or response_json.get("action_pack_json", {}).get("resume_tailoring_tasks")
        or response_json.get("tailoring_plan_json", {}).get("rewrite_tasks")
    )
    focus_areas = _normalize_focus_areas(
        response_json.get("focus_areas")
        or response_json.get("interview_focus_areas")
        or response_json.get("action_pack_json", {}).get("interview_focus_areas")
        or response_json.get("interview_blueprint_json", {}).get("focus_areas")
    )
    missing_user_inputs = _normalize_missing_user_inputs(
        response_json.get("missing_user_inputs")
        or response_json.get("missing_info_questions")
        or response_json.get("action_pack_json", {}).get("missing_user_inputs")
        or response_json.get("tailoring_plan_json", {}).get("missing_info_questions")
    )
    question_pack = _normalize_questions(
        response_json.get("question_pack")
        or response_json.get("interview_blueprint_json", {}).get("question_pack")
    )
    rubric = _normalize_rubric(
        response_json.get("rubric")
        or response_json.get("interview_blueprint_json", {}).get("rubric")
    )

    action_pack = response_json.get("action_pack_json")
    if not isinstance(action_pack, dict):
        action_pack = {}

    tailoring_plan = response_json.get("tailoring_plan_json")
    if not isinstance(tailoring_plan, dict):
        tailoring_plan = {}

    interview_blueprint = response_json.get("interview_blueprint_json")
    if not isinstance(interview_blueprint, dict):
        interview_blueprint = {}

    return {
        "overall_score": response_json.get("overall_score"),
        "fit_band": response_json.get("fit_band"),
        "summary": response_json.get("summary"),
        "reasoning": response_json.get("reasoning"),
        "confidence": response_json.get("confidence"),
        "strengths": _normalize_insight_items(
            response_json.get("strengths", []),
            default_severity="medium",
        ),
        "must_fix": _normalize_insight_items(
            response_json.get("must_fix", []),
            default_severity="high",
        ),
        "should_fix": _normalize_insight_items(
            response_json.get("should_fix", []),
            default_severity="medium",
        ),
        "evidence_map_json": evidence_map,
        "action_pack_json": {
            "resume_tailoring_tasks": _normalize_rewrite_tasks(
                action_pack.get("resume_tailoring_tasks") or rewrite_tasks
            ),
            "interview_focus_areas": _normalize_focus_areas(
                action_pack.get("interview_focus_areas") or focus_areas
            ),
            "missing_user_inputs": _normalize_missing_user_inputs(
                action_pack.get("missing_user_inputs") or missing_user_inputs
            ),
        },
        "tailoring_plan_json": {
            "target_summary": tailoring_plan.get("target_summary")
            or response_json.get("target_summary")
            or response_json.get("summary"),
            "rewrite_tasks": _normalize_rewrite_tasks(
                tailoring_plan.get("rewrite_tasks") or rewrite_tasks
            ),
            "must_add_evidence": tailoring_plan.get("must_add_evidence")
            or evidence_map.get("missing_items", []),
            "missing_info_questions": _normalize_missing_user_inputs(
                tailoring_plan.get("missing_info_questions") or missing_user_inputs
            ),
        },
        "interview_blueprint_json": {
            "target_role": interview_blueprint.get("target_role")
            or response_json.get("target_role"),
            "focus_areas": _normalize_focus_areas(
                interview_blueprint.get("focus_areas") or focus_areas
            ),
            "question_pack": _normalize_questions(
                interview_blueprint.get("question_pack") or question_pack
            ),
            "follow_up_rules": interview_blueprint.get("follow_up_rules") or [],
            "rubric": _normalize_rubric(interview_blueprint.get("rubric") or rubric),
        },
    }


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

    async def _request_report_json(
        self,
        *,
        instructions: str,
        payload: object,
    ) -> dict[str, object]:
        return await request_json_completion(
            config=AIProviderConfig(
                provider=self.provider,
                base_url=self.base_url,
                api_key=self.api_key,
                model=self.model,
                timeout_seconds=self.timeout_seconds,
            ),
            instructions=instructions,
            payload=payload,
            max_tokens=900,
        )

    async def correct(self, payload: AIMatchReportRequest) -> AIMatchReportResult:
        response_json = await self._request_report_json(
            instructions=get_match_report_generation_prompt(),
            payload=payload,
        )
        if _has_null_required_core_fields(response_json):
            response_json = await self._request_report_json(
                instructions=get_match_report_repair_prompt(),
                payload={
                    "original_request": {
                        "resume_snapshot": payload.resume_snapshot,
                        "job_snapshot": payload.job_snapshot,
                        "rule_result": payload.rule_result,
                    },
                    "previous_invalid_response": response_json,
                },
            )
        try:
            report_payload = MatchAIReportPayload.model_validate(
                _normalize_match_ai_response(response_json)
            )
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
        timeout_seconds=max(1, settings.match_ai_timeout_seconds),
    )
