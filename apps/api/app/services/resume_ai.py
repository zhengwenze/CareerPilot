from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field

from app.core.config import Settings
from app.schemas.resume import ResumeStructuredData
from app.services.ai_client import AIProviderConfig, request_json_completion
from app.services.resume_parser import EMAIL_PATTERN, PHONE_PATTERN

logger = logging.getLogger(__name__)

EMPTY_PROVIDER_VALUES = {"", "disabled", "none", "off"}
MAX_SUMMARY_LENGTH = 280
LIST_LIMITS = {
    "education": 8,
    "work_experience": 10,
    "projects": 10,
    "certifications": 8,
    "technical": 30,
    "tools": 20,
    "languages": 10,
}
JSON_RESPONSE_INSTRUCTIONS = """
You are a resume structure correction engine.
You receive raw PDF text plus a rule-based structured resume.
Your job is to correct section assignment, fill obvious missing fields, remove duplicates,
and normalize output without inventing facts.

Rules:
1. Do not add fields outside this schema:
   basic_info{name,email,phone,location,summary},
   education[], work_experience[], projects[],
   skills{technical[],tools[],languages[]},
   certifications[].
2. Never fabricate schools, companies, dates, projects, certifications, or skills.
3. Prefer evidence from the raw_text over the rule output when they conflict.
4. Return strict JSON only. No markdown. No explanation outside JSON.
5. Keep list items concise and preserve original evidence wording when possible.

Return JSON with keys:
{
  "structured_json": <schema above>,
  "corrections": [{"field": "...", "reason": "..."}],
  "confidence": 0.0-1.0,
  "reasoning": "short summary"
}
""".strip()


@dataclass(slots=True)
class ResumeAICorrectionRequest:
    raw_text: str
    rule_structured_json: dict[str, object]


@dataclass(slots=True)
class ResumeAICorrectionResult:
    provider: str
    model: str | None
    status: str
    structured_data: ResumeStructuredData | None = None
    corrections: list[dict[str, object]] = field(default_factory=list)
    confidence: float | None = None
    reasoning: str = ""


class ResumeAICorrectionProvider:
    async def correct(
        self, payload: ResumeAICorrectionRequest
    ) -> ResumeAICorrectionResult:
        raise NotImplementedError


class DisabledResumeAICorrectionProvider(ResumeAICorrectionProvider):
    async def correct(
        self, payload: ResumeAICorrectionRequest
    ) -> ResumeAICorrectionResult:
        return ResumeAICorrectionResult(
            provider="disabled",
            model=None,
            status="skipped",
            reasoning="Resume AI correction is disabled",
        )


class ConfiguredResumeAICorrectionProvider(ResumeAICorrectionProvider):
    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip() if api_key else ""
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def correct(
        self, payload: ResumeAICorrectionRequest
    ) -> ResumeAICorrectionResult:
        payload_json = await request_json_completion(
            config=AIProviderConfig(
                provider=self.provider,
                base_url=self.base_url,
                api_key=self.api_key or None,
                model=self.model,
                timeout_seconds=self.timeout_seconds,
            ),
            instructions=JSON_RESPONSE_INSTRUCTIONS,
            payload=payload,
        )
        structured_payload = payload_json.get("structured_json", payload_json)
        structured_data = ResumeStructuredData.model_validate(structured_payload)

        corrections = payload_json.get("corrections")
        if not isinstance(corrections, list):
            corrections = []

        confidence = payload_json.get("confidence")
        if confidence is not None:
            confidence = max(0.0, min(1.0, float(confidence)))

        return ResumeAICorrectionResult(
            provider=self.provider,
            model=self.model,
            status="applied",
            structured_data=structured_data,
            corrections=[item for item in corrections if isinstance(item, dict)],
            confidence=confidence,
            reasoning=str(payload_json.get("reasoning", "")).strip(),
        )


def build_resume_ai_correction_provider(
    settings: Settings,
) -> ResumeAICorrectionProvider:
    provider = settings.resume_ai_provider.strip().lower()
    if provider in EMPTY_PROVIDER_VALUES:
        return DisabledResumeAICorrectionProvider()

    if not settings.resume_ai_base_url or not settings.resume_ai_model:
        return DisabledResumeAICorrectionProvider()

    return ConfiguredResumeAICorrectionProvider(
        provider=provider,
        base_url=settings.resume_ai_base_url,
        api_key=settings.resume_ai_api_key,
        model=settings.resume_ai_model,
        timeout_seconds=settings.resume_ai_timeout_seconds,
    )


def merge_resume_ai_correction(
    *,
    raw_text: str,
    rule_result: ResumeStructuredData,
    ai_result: ResumeStructuredData,
) -> ResumeStructuredData:
    normalized_raw_text = _normalize_evidence(raw_text)

    basic_info = {
        "name": _choose_evidence_backed_scalar(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_value=rule_result.basic_info.name,
            ai_value=ai_result.basic_info.name,
            use_overlap=False,
        ),
        "email": _choose_contact_field(
            rule_value=rule_result.basic_info.email,
            ai_value=ai_result.basic_info.email,
            normalized_raw_text=normalized_raw_text,
            pattern=EMAIL_PATTERN,
        ),
        "phone": _choose_contact_field(
            rule_value=rule_result.basic_info.phone,
            ai_value=ai_result.basic_info.phone,
            normalized_raw_text=normalized_raw_text,
            pattern=PHONE_PATTERN,
        ),
        "location": _choose_evidence_backed_scalar(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_value=rule_result.basic_info.location,
            ai_value=ai_result.basic_info.location,
            use_overlap=False,
        ),
        "summary": _choose_summary(
            raw_text=raw_text,
            rule_value=rule_result.basic_info.summary,
            ai_value=ai_result.basic_info.summary,
        ),
    }

    education = _choose_supported_items(
        raw_text=raw_text,
        normalized_raw_text=normalized_raw_text,
        rule_items=rule_result.education,
        ai_items=ai_result.education,
        limit=LIST_LIMITS["education"],
    )
    work_experience = _choose_supported_items(
        raw_text=raw_text,
        normalized_raw_text=normalized_raw_text,
        rule_items=rule_result.work_experience,
        ai_items=ai_result.work_experience,
        limit=LIST_LIMITS["work_experience"],
    )
    projects = _choose_supported_items(
        raw_text=raw_text,
        normalized_raw_text=normalized_raw_text,
        rule_items=rule_result.projects,
        ai_items=ai_result.projects,
        limit=LIST_LIMITS["projects"],
    )
    certifications = _choose_supported_items(
        raw_text=raw_text,
        normalized_raw_text=normalized_raw_text,
        rule_items=rule_result.certifications,
        ai_items=ai_result.certifications,
        limit=LIST_LIMITS["certifications"],
    )

    skills = {
        "technical": _choose_supported_items(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_items=rule_result.skills.technical,
            ai_items=ai_result.skills.technical,
            limit=LIST_LIMITS["technical"],
            use_overlap=False,
        ),
        "tools": _choose_supported_items(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_items=rule_result.skills.tools,
            ai_items=ai_result.skills.tools,
            limit=LIST_LIMITS["tools"],
            use_overlap=False,
        ),
        "languages": _choose_supported_items(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_items=rule_result.skills.languages,
            ai_items=ai_result.skills.languages,
            limit=LIST_LIMITS["languages"],
            use_overlap=False,
        ),
    }

    merged = ResumeStructuredData(
        basic_info=basic_info,
        education=education,
        work_experience=work_experience,
        projects=projects,
        skills=skills,
        certifications=certifications,
    )
    logger.info(
        (
            "resume_ai.merge:done name=%s email=%s education_count=%s "
            "work_count=%s project_count=%s technical_count=%s"
        ),
        merged.basic_info.name,
        merged.basic_info.email,
        len(merged.education),
        len(merged.work_experience),
        len(merged.projects),
        len(merged.skills.technical),
    )
    return merged


def _choose_contact_field(
    *,
    rule_value: str,
    ai_value: str,
    normalized_raw_text: str,
    pattern: re.Pattern[str],
) -> str:
    rule_value = rule_value.strip()
    ai_value = ai_value.strip()
    if (
        ai_value
        and pattern.fullmatch(ai_value)
        and _appears_in_raw_text(ai_value, normalized_raw_text)
    ):
        return ai_value
    if rule_value and pattern.fullmatch(rule_value):
        return rule_value
    return ""


def _choose_evidence_backed_scalar(
    *,
    raw_text: str,
    normalized_raw_text: str,
    rule_value: str,
    ai_value: str,
    use_overlap: bool,
) -> str:
    cleaned_rule = _clean_text(rule_value)
    cleaned_ai = _clean_text(ai_value)
    if cleaned_ai:
        ai_supported = (
            _has_text_overlap(cleaned_ai, raw_text)
            if use_overlap
            else _appears_in_raw_text(cleaned_ai, normalized_raw_text)
        )
        rule_supported = (
            _has_text_overlap(cleaned_rule, raw_text)
            if use_overlap
            else _appears_in_raw_text(cleaned_rule, normalized_raw_text)
        )
        if ai_supported and (not cleaned_rule or not rule_supported):
            return cleaned_ai
    return cleaned_rule


def _choose_summary(*, raw_text: str, rule_value: str, ai_value: str) -> str:
    cleaned_rule = _clean_text(rule_value)
    cleaned_ai = _clean_text(ai_value)
    if (
        cleaned_ai
        and len(cleaned_ai) <= MAX_SUMMARY_LENGTH
        and _has_text_overlap(cleaned_ai, raw_text)
    ):
        return cleaned_ai
    return cleaned_rule


def _choose_supported_items(
    *,
    raw_text: str,
    normalized_raw_text: str,
    rule_items: list[str],
    ai_items: list[str],
    limit: int,
    use_overlap: bool = True,
) -> list[str]:
    filtered_ai = _filter_supported_items(
        items=ai_items,
        raw_text=raw_text,
        normalized_raw_text=normalized_raw_text,
        limit=limit,
        use_overlap=use_overlap,
    )
    if filtered_ai:
        return filtered_ai
    return _dedupe_clean_items(rule_items, limit=limit)


def _filter_supported_items(
    *,
    items: list[str],
    raw_text: str,
    normalized_raw_text: str,
    limit: int,
    use_overlap: bool,
) -> list[str]:
    filtered: list[str] = []
    for item in items:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        if use_overlap:
            supported = _appears_in_raw_text(
                cleaned, normalized_raw_text
            ) or _has_text_overlap(
                cleaned,
                raw_text,
            )
        else:
            supported = _appears_in_raw_text(cleaned, normalized_raw_text)
        if supported:
            filtered.append(cleaned)
    return _dedupe_clean_items(filtered, limit=limit)


def _dedupe_clean_items(items: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        lowered = cleaned.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _normalize_evidence(value: str) -> str:
    normalized = _clean_text(value).lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", normalized)


def _appears_in_raw_text(value: str, normalized_raw_text: str) -> bool:
    normalized_value = _normalize_evidence(value)
    return bool(normalized_value) and normalized_value in normalized_raw_text


def _has_text_overlap(candidate: str, raw_text: str) -> bool:
    normalized_raw_text = _normalize_evidence(raw_text)
    tokens = [
        _normalize_evidence(token)
        for token in re.findall(
            r"[A-Za-z0-9+#./-]{2,}|[\u4e00-\u9fff]{2,}", _clean_text(candidate)
        )
    ]
    tokens = [token for token in tokens if token]
    if not tokens:
        return False
    matches = sum(1 for token in tokens if token in normalized_raw_text)
    if len(tokens) == 1:
        return matches == 1
    return matches >= min(2, len(tokens))
