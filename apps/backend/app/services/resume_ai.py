from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.core.config import Settings
from app.prompts.resume import get_resume_structure_correction_prompt
from app.schemas.resume import ResumeStructuredData
from app.services.ai_client import AIClientError, AIProviderConfig, request_json_completion
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
PROFESSIONAL_PUNCTUATION_MAP = str.maketrans(
    {
        ",": "，",
        ";": "；",
        ":": "：",
        "?": "？",
        "!": "！",
    }
)
TERMINAL_SENTENCE_FIELDS = {"work_experience", "projects", "certifications"}
LIST_FIELD_PRIORITIES = {
    "education": (
        "school",
        "degree",
        "major",
        "start_date",
        "end_date",
        "dates",
        "gpa",
        "notes",
    ),
    "work_experience": (
        "company",
        "role",
        "title",
        "department",
        "start_date",
        "end_date",
        "dates",
        "summary",
        "highlights",
        "responsibilities",
        "achievements",
    ),
    "projects": (
        "name",
        "role",
        "start_date",
        "end_date",
        "dates",
        "tech_stack",
        "summary",
        "description",
        "highlights",
        "outcome",
    ),
    "certifications": (
        "name",
        "issuer",
        "date",
        "type",
        "notes",
    ),
}


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
        logger.info(
            "Resume AI correction started provider=%s model=%s "
            "raw_text_chars=%s rule_sections=%s has_api_key=%s",
            self.provider,
            self.model,
            len(payload.raw_text),
            ",".join(sorted(payload.rule_structured_json.keys())),
            bool(self.api_key),
        )
        payload_json = await request_json_completion(
            config=AIProviderConfig(
                provider=self.provider,
                base_url=self.base_url,
                api_key=self.api_key or None,
                model=self.model,
                timeout_seconds=self.timeout_seconds,
            ),
            instructions=get_resume_structure_correction_prompt(),
            payload=payload,
            max_tokens=2200,
        )
        logger.info(
            "Resume AI correction response received provider=%s model=%s top_level_keys=%s",
            self.provider,
            self.model,
            ",".join(sorted(payload_json.keys())),
        )
        structured_payload = _normalize_ai_structured_payload(
            payload_json.get("structured_json", payload_json)
        )
        try:
            structured_data = ResumeStructuredData.model_validate(structured_payload)
        except ValidationError as exc:
            logger.exception(
                "Resume AI correction structured payload validation failed provider=%s model=%s",
                self.provider,
                self.model,
            )
            raise AIClientError(
                category="invalid_response_format",
                detail=f"Resume AI structured payload validation failed: {exc}",
            ) from exc
        logger.info(
            "Resume AI correction structured payload validated "
            "provider=%s model=%s education=%s work_experience=%s "
            "projects=%s certifications=%s",
            self.provider,
            self.model,
            len(structured_data.education),
            len(structured_data.work_experience),
            len(structured_data.projects),
            len(structured_data.certifications),
        )

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


def _normalize_ai_structured_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise AIClientError(
            category="invalid_response_format",
            detail="Resume AI structured payload must be a JSON object",
        )

    basic_info_payload = payload.get("basic_info")
    skills_payload = payload.get("skills")

    normalized = {
        "basic_info": _normalize_basic_info(
            basic_info_payload if isinstance(basic_info_payload, dict) else {}
        ),
        "education": _normalize_list_field(payload.get("education"), field_name="education"),
        "work_experience": _normalize_list_field(
            payload.get("work_experience"),
            field_name="work_experience",
        ),
        "projects": _normalize_list_field(payload.get("projects"), field_name="projects"),
        "skills": _normalize_skills(skills_payload if isinstance(skills_payload, dict) else {}),
        "certifications": _normalize_list_field(
            payload.get("certifications"),
            field_name="certifications",
        ),
    }
    return normalized


def _normalize_basic_info(payload: dict[str, object]) -> dict[str, str]:
    return {
        "name": _normalize_scalar_text(payload.get("name")),
        "email": _normalize_scalar_text(payload.get("email")),
        "phone": _normalize_scalar_text(payload.get("phone")),
        "location": _normalize_scalar_text(payload.get("location")),
        "summary": _normalize_professional_punctuation(
            _normalize_scalar_text(payload.get("summary")),
            ensure_terminal_sentence=True,
        ),
    }


def _normalize_skills(payload: dict[str, object]) -> dict[str, list[str]]:
    return {
        "technical": _normalize_list_field(payload.get("technical"), field_name="skills"),
        "tools": _normalize_list_field(payload.get("tools"), field_name="skills"),
        "languages": _normalize_list_field(payload.get("languages"), field_name="skills"),
    }


def _normalize_scalar_text(value: object) -> str:
    if isinstance(value, str):
        return _clean_text(value)
    if value is None:
        return ""
    return _clean_text(str(value))


def _normalize_list_field(value: object, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = [value]

    normalized_items: list[str] = []
    for item in raw_items:
        flattened = _flatten_list_item(item, field_name=field_name)
        cleaned = _clean_text(flattened)
        if cleaned:
            normalized_items.append(cleaned)
    deduped = _dedupe_clean_items(normalized_items, limit=LIST_LIMITS.get(field_name, 50))
    return _normalize_professional_items(deduped, field_name=field_name)


def _flatten_list_item(value: object, *, field_name: str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return _flatten_object_item(value, field_name=field_name)
    if isinstance(value, list):
        return " ".join(
            part
            for part in (_flatten_list_item(item, field_name=field_name) for item in value)
            if _clean_text(part)
        )
    if value is None:
        return ""
    return str(value)


def _flatten_object_item(value: dict[str, object], *, field_name: str) -> str:
    ordered_parts: list[str] = []
    seen_parts: set[str] = set()

    for key in LIST_FIELD_PRIORITIES.get(field_name, ()):
        if key not in value:
            continue
        for part in _extract_text_parts(value[key]):
            _append_part(ordered_parts, seen_parts, part)

    for key, item in value.items():
        if key in LIST_FIELD_PRIORITIES.get(field_name, ()):
            continue
        for part in _extract_text_parts(item):
            _append_part(ordered_parts, seen_parts, part)

    return " ".join(ordered_parts)


def _extract_text_parts(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = _clean_text(value)
        return [cleaned] if cleaned else []
    if isinstance(value, dict):
        parts: list[str] = []
        for item in value.values():
            parts.extend(_extract_text_parts(item))
        return parts
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            parts.extend(_extract_text_parts(item))
        return parts
    if value is None:
        return []
    cleaned = _clean_text(str(value))
    return [cleaned] if cleaned else []


def _append_part(parts: list[str], seen_parts: set[str], value: str) -> None:
    cleaned = _clean_text(value)
    if not cleaned:
        return
    lowered = cleaned.casefold()
    if lowered in seen_parts:
        return
    seen_parts.add(lowered)
    parts.append(cleaned)


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
        "summary": _normalize_professional_punctuation(
            _choose_summary(
                raw_text=raw_text,
                rule_value=rule_result.basic_info.summary,
                ai_value=ai_result.basic_info.summary,
            ),
            ensure_terminal_sentence=True,
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
    education = _normalize_professional_items(education, field_name="education")
    work_experience = _normalize_professional_items(
        work_experience,
        field_name="work_experience",
    )
    projects = _normalize_professional_items(projects, field_name="projects")
    certifications = _normalize_professional_items(
        certifications,
        field_name="certifications",
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


def _normalize_professional_items(items: list[str], *, field_name: str) -> list[str]:
    normalized: list[str] = []
    for item in items:
        polished = _normalize_professional_punctuation(
            item,
            ensure_terminal_sentence=field_name in TERMINAL_SENTENCE_FIELDS,
        )
        if polished:
            normalized.append(polished)
    return _dedupe_items_preserve_style(
        normalized,
        limit=LIST_LIMITS.get(field_name, 50),
    )


def _dedupe_items_preserve_style(items: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = re.sub(r"\s+", " ", item).strip()
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


def _normalize_professional_punctuation(
    value: str,
    *,
    ensure_terminal_sentence: bool = False,
) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return ""

    if re.search(r"[\u4e00-\u9fff]", cleaned):
        cleaned = cleaned.translate(PROFESSIONAL_PUNCTUATION_MAP)
        cleaned = re.sub(r"(?<!\d)\.(?!\d)", "。", cleaned)
        cleaned = re.sub(r"\s*([，。；：！？、])\s*", r"\1", cleaned)
        cleaned = re.sub(r"([，。；：！？、])\1+", r"\1", cleaned)

    cleaned = re.sub(r"^[，。；：、\s]+", "", cleaned)
    cleaned = re.sub(r"[，；：、\s]+$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""

    if ensure_terminal_sentence and re.search(r"[\u4e00-\u9fff]", cleaned):
        if not re.search(r"[。！？]$", cleaned):
            cleaned = f"{cleaned}。"
    return cleaned


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
