from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.core.config import Settings
from app.prompts.resume import get_resume_structure_correction_prompt
from app.schemas.resume import ResumeStructuredData
from app.services.ai_client import (
    AIClientError,
    AIProviderConfig,
    request_json_completion,
)
from app.services.resume_parser import EMAIL_PATTERN, PHONE_PATTERN

logger = logging.getLogger(__name__)

EMPTY_PROVIDER_VALUES = {"", "disabled", "none", "off"}
MAX_SUMMARY_LENGTH = 280
LIST_LIMITS = {
    "education": 8,
    "work_experience": 10,
    "projects": 10,
    "certifications": 8,
    "awards": 8,
    "technical": 30,
    "tools": 20,
    "languages": 10,
    "custom_section_items": 20,
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

    education, education_items = _normalize_education_payload(payload.get("education"))
    work_experience, work_experience_items = _normalize_work_experience_payload(
        payload.get("work_experience")
    )
    projects, project_items = _normalize_project_payload(payload.get("projects"))
    certifications, certification_items = _normalize_certification_payload(
        payload.get("certifications")
    )

    normalized = {
        "basic_info": _normalize_basic_info(
            basic_info_payload if isinstance(basic_info_payload, dict) else {}
        ),
        "education": education,
        "education_items": education_items,
        "work_experience": work_experience,
        "work_experience_items": work_experience_items,
        "projects": projects,
        "project_items": project_items,
        "skills": _normalize_skills(
            skills_payload if isinstance(skills_payload, dict) else {}
        ),
        "certifications": certifications,
        "certification_items": certification_items,
        "awards": _normalize_list_field(payload.get("awards"), field_name="awards"),
        "custom_sections": _normalize_custom_sections(payload.get("custom_sections")),
    }
    return normalized


def _normalize_basic_info(payload: dict[str, object]) -> dict[str, object]:
    return {
        "name": _normalize_scalar_text(payload.get("name")),
        "title": _normalize_scalar_text(payload.get("title")),
        "status": _normalize_scalar_text(payload.get("status")),
        "email": _normalize_scalar_text(payload.get("email")),
        "phone": _normalize_scalar_text(payload.get("phone")),
        "location": _normalize_scalar_text(payload.get("location")),
        "links": _normalize_list_field(payload.get("links"), field_name="skills"),
        "summary": _normalize_professional_punctuation(
            _normalize_scalar_text(payload.get("summary")),
            ensure_terminal_sentence=True,
        ),
    }


def _normalize_skills(payload: dict[str, object]) -> dict[str, list[str]]:
    return {
        "technical": _normalize_list_field(
            payload.get("technical"), field_name="skills"
        ),
        "tools": _normalize_list_field(payload.get("tools"), field_name="skills"),
        "languages": _normalize_list_field(
            payload.get("languages"), field_name="skills"
        ),
    }


def _normalize_custom_sections(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        return []

    normalized_sections: list[dict[str, object]] = []
    for index, section in enumerate(payload, start=1):
        if not isinstance(section, dict):
            continue
        title = _normalize_scalar_text(section.get("title"))
        if not title:
            continue
        items_payload = section.get("items")
        items: list[dict[str, object]] = []
        if isinstance(items_payload, list):
            for item_index, item in enumerate(items_payload, start=1):
                if not isinstance(item, dict):
                    continue
                description = _normalize_list_field(
                    item.get("description"),
                    field_name="custom_section_items",
                )
                normalized_item = {
                    "id": _normalize_scalar_text(item.get("id"))
                    or f"custom_{index}_{item_index}",
                    "title": _normalize_scalar_text(item.get("title")),
                    "subtitle": _normalize_scalar_text(item.get("subtitle")),
                    "years": _normalize_scalar_text(item.get("years")),
                    "description": description,
                }
                if (
                    normalized_item["title"]
                    or normalized_item["subtitle"]
                    or normalized_item["years"]
                    or normalized_item["description"]
                ):
                    items.append(normalized_item)
        normalized_sections.append(
            {
                "id": _normalize_scalar_text(section.get("id")) or f"custom_{index}",
                "title": title,
                "items": items,
            }
        )
    return normalized_sections


def _normalize_education_payload(
    payload: object,
) -> tuple[list[str], list[dict[str, object]]]:
    if not isinstance(payload, list):
        values = _normalize_list_field(payload, field_name="education")
        return values, []

    strings: list[str] = []
    items: list[dict[str, object]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            text = _normalize_professional_punctuation(
                _flatten_list_item(item, field_name="education")
            )
            if text:
                strings.append(text)
            continue
        normalized_item = {
            "id": _normalize_scalar_text(item.get("id")) or f"edu_{index}",
            "school": _normalize_scalar_text(item.get("school")),
            "degree": _normalize_scalar_text(item.get("degree")),
            "major": _normalize_scalar_text(item.get("major")),
            "start_date": _normalize_scalar_text(item.get("start_date")),
            "end_date": _normalize_scalar_text(item.get("end_date")),
            "gpa": _normalize_scalar_text(item.get("gpa")),
            "honors": _normalize_list_field(item.get("honors"), field_name="education"),
        }
        if any(
            normalized_item[key]
            for key in (
                "school",
                "degree",
                "major",
                "start_date",
                "end_date",
                "gpa",
                "honors",
            )
        ):
            items.append(normalized_item)
            strings.append(
                _normalize_professional_punctuation(
                    _flatten_object_item(item, field_name="education")
                )
            )
    return _dedupe_clean_items(strings, limit=LIST_LIMITS["education"]), items


def _normalize_work_experience_payload(
    payload: object,
) -> tuple[list[str], list[dict[str, object]]]:
    if not isinstance(payload, list):
        values = _normalize_list_field(payload, field_name="work_experience")
        return values, []

    strings: list[str] = []
    items: list[dict[str, object]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            text = _normalize_professional_punctuation(
                _flatten_list_item(item, field_name="work_experience"),
                ensure_terminal_sentence=True,
            )
            if text:
                strings.append(text)
            continue
        bullets = _normalize_list_field(
            item.get("bullets")
            or item.get("highlights")
            or item.get("responsibilities")
            or item.get("achievements"),
            field_name="work_experience",
        )
        normalized_item = {
            "id": _normalize_scalar_text(item.get("id")) or f"work_{index}",
            "company": _normalize_scalar_text(item.get("company")),
            "title": _normalize_scalar_text(item.get("title") or item.get("role")),
            "department": _normalize_scalar_text(item.get("department")),
            "location": _normalize_scalar_text(item.get("location")),
            "start_date": _normalize_scalar_text(item.get("start_date")),
            "end_date": _normalize_scalar_text(item.get("end_date")),
            "employment_type": _normalize_scalar_text(item.get("employment_type")),
            "bullets": [
                {"id": f"work_{index}_b{bullet_index}", "text": bullet}
                for bullet_index, bullet in enumerate(bullets, start=1)
            ],
        }
        if any(
            normalized_item[key]
            for key in (
                "company",
                "title",
                "department",
                "location",
                "start_date",
                "end_date",
                "employment_type",
                "bullets",
            )
        ):
            items.append(normalized_item)
            strings.append(
                _normalize_professional_punctuation(
                    _flatten_object_item(item, field_name="work_experience"),
                    ensure_terminal_sentence=True,
                )
            )
    return _dedupe_clean_items(strings, limit=LIST_LIMITS["work_experience"]), items


def _normalize_project_payload(
    payload: object,
) -> tuple[list[str], list[dict[str, object]]]:
    if not isinstance(payload, list):
        values = _normalize_list_field(payload, field_name="projects")
        return values, []

    strings: list[str] = []
    items: list[dict[str, object]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            text = _normalize_professional_punctuation(
                _flatten_list_item(item, field_name="projects"),
                ensure_terminal_sentence=True,
            )
            if text:
                strings.append(text)
            continue
        bullets = _normalize_list_field(
            item.get("bullets") or item.get("description") or item.get("highlights"),
            field_name="projects",
        )
        normalized_item = {
            "id": _normalize_scalar_text(item.get("id")) or f"proj_{index}",
            "name": _normalize_scalar_text(item.get("name")),
            "role": _normalize_scalar_text(item.get("role")),
            "start_date": _normalize_scalar_text(item.get("start_date")),
            "end_date": _normalize_scalar_text(item.get("end_date")),
            "summary": _normalize_professional_punctuation(
                _normalize_scalar_text(item.get("summary"))
            ),
            "bullets": [
                {"id": f"proj_{index}_b{bullet_index}", "text": bullet}
                for bullet_index, bullet in enumerate(bullets, start=1)
            ],
            "skills_used": _normalize_list_field(
                item.get("skills_used") or item.get("tech_stack"),
                field_name="skills",
            ),
        }
        if any(
            normalized_item[key]
            for key in (
                "name",
                "role",
                "start_date",
                "end_date",
                "summary",
                "bullets",
                "skills_used",
            )
        ):
            items.append(normalized_item)
            strings.append(
                _normalize_professional_punctuation(
                    _flatten_object_item(item, field_name="projects"),
                    ensure_terminal_sentence=True,
                )
            )
    return _dedupe_clean_items(strings, limit=LIST_LIMITS["projects"]), items


def _normalize_certification_payload(
    payload: object,
) -> tuple[list[str], list[dict[str, object]]]:
    if not isinstance(payload, list):
        values = _normalize_list_field(payload, field_name="certifications")
        return values, []

    strings: list[str] = []
    items: list[dict[str, object]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            text = _normalize_professional_punctuation(
                _flatten_list_item(item, field_name="certifications"),
                ensure_terminal_sentence=True,
            )
            if text:
                strings.append(text)
            continue
        normalized_item = {
            "id": _normalize_scalar_text(item.get("id")) or f"cert_{index}",
            "name": _normalize_scalar_text(item.get("name")),
            "issuer": _normalize_scalar_text(item.get("issuer")),
            "date": _normalize_scalar_text(item.get("date")),
        }
        if any(normalized_item[key] for key in ("name", "issuer", "date")):
            items.append(normalized_item)
            strings.append(
                _normalize_professional_punctuation(
                    _flatten_object_item(item, field_name="certifications"),
                    ensure_terminal_sentence=True,
                )
            )
    return _dedupe_clean_items(strings, limit=LIST_LIMITS["certifications"]), items


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
    deduped = _dedupe_clean_items(
        normalized_items, limit=LIST_LIMITS.get(field_name, 50)
    )
    return _normalize_professional_items(deduped, field_name=field_name)


def _flatten_list_item(value: object, *, field_name: str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return _flatten_object_item(value, field_name=field_name)
    if isinstance(value, list):
        return " ".join(
            part
            for part in (
                _flatten_list_item(item, field_name=field_name) for item in value
            )
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
        "title": _choose_evidence_backed_scalar(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_value=rule_result.basic_info.title,
            ai_value=ai_result.basic_info.title,
            use_overlap=True,
        ),
        "status": _choose_evidence_backed_scalar(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_value=rule_result.basic_info.status,
            ai_value=ai_result.basic_info.status,
            use_overlap=True,
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
        "links": _choose_supported_items(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_items=rule_result.basic_info.links,
            ai_items=ai_result.basic_info.links,
            limit=5,
            use_overlap=False,
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
    awards = _choose_supported_items(
        raw_text=raw_text,
        normalized_raw_text=normalized_raw_text,
        rule_items=rule_result.awards,
        ai_items=ai_result.awards,
        limit=LIST_LIMITS["awards"],
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
    awards = _normalize_professional_items(awards, field_name="awards")

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
        education_items=_choose_structured_items(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_items=[item.model_dump() for item in rule_result.education_items],
            ai_items=[item.model_dump() for item in ai_result.education_items],
            item_text_builder=_education_item_text,
            limit=LIST_LIMITS["education"],
        ),
        work_experience=work_experience,
        work_experience_items=_choose_structured_items(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_items=[
                item.model_dump() for item in rule_result.work_experience_items
            ],
            ai_items=[item.model_dump() for item in ai_result.work_experience_items],
            item_text_builder=_work_experience_item_text,
            limit=LIST_LIMITS["work_experience"],
        ),
        projects=projects,
        project_items=_choose_structured_items(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_items=[item.model_dump() for item in rule_result.project_items],
            ai_items=[item.model_dump() for item in ai_result.project_items],
            item_text_builder=_project_item_text,
            limit=LIST_LIMITS["projects"],
        ),
        skills=skills,
        certifications=certifications,
        certification_items=_choose_structured_items(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_items=[item.model_dump() for item in rule_result.certification_items],
            ai_items=[item.model_dump() for item in ai_result.certification_items],
            item_text_builder=_certification_item_text,
            limit=LIST_LIMITS["certifications"],
        ),
        awards=awards,
        custom_sections=_choose_custom_sections(
            raw_text=raw_text,
            normalized_raw_text=normalized_raw_text,
            rule_sections=rule_result.custom_sections,
            ai_sections=ai_result.custom_sections,
        ),
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


def _choose_structured_items(
    *,
    raw_text: str,
    normalized_raw_text: str,
    rule_items: list[dict[str, object]],
    ai_items: list[dict[str, object]],
    item_text_builder: callable,
    limit: int,
) -> list[dict[str, object]]:
    supported_ai: list[dict[str, object]] = []
    for item in ai_items:
        text = _clean_text(item_text_builder(item))
        if not text:
            continue
        if _appears_in_raw_text(text, normalized_raw_text) or _has_text_overlap(
            text, raw_text
        ):
            supported_ai.append(item)
        if len(supported_ai) >= limit:
            break
    if supported_ai:
        return supported_ai
    return rule_items[:limit]


def _education_item_text(item: dict[str, object]) -> str:
    return _join_text_parts(
        [
            item.get("school"),
            item.get("major"),
            item.get("degree"),
            item.get("start_date"),
            item.get("end_date"),
            item.get("gpa"),
            " ".join(
                str(value)
                for value in item.get("honors", [])
                if _clean_text(str(value))
            ),
        ]
    )


def _work_experience_item_text(item: dict[str, object]) -> str:
    bullets = item.get("bullets", [])
    bullet_text = " ".join(
        _clean_text(bullet.get("text", "") if isinstance(bullet, dict) else str(bullet))
        for bullet in bullets
    )
    return _join_text_parts(
        [
            item.get("company"),
            item.get("title"),
            item.get("department"),
            item.get("location"),
            item.get("start_date"),
            item.get("end_date"),
            item.get("employment_type"),
            bullet_text,
        ]
    )


def _project_item_text(item: dict[str, object]) -> str:
    bullets = item.get("bullets", [])
    bullet_text = " ".join(
        _clean_text(bullet.get("text", "") if isinstance(bullet, dict) else str(bullet))
        for bullet in bullets
    )
    return _join_text_parts(
        [
            item.get("name"),
            item.get("role"),
            item.get("start_date"),
            item.get("end_date"),
            item.get("summary"),
            bullet_text,
            " ".join(
                _clean_text(str(value))
                for value in item.get("skills_used", [])
                if _clean_text(str(value))
            ),
        ]
    )


def _certification_item_text(item: dict[str, object]) -> str:
    return _join_text_parts([item.get("name"), item.get("issuer"), item.get("date")])


def _join_text_parts(parts: list[object]) -> str:
    return " ".join(_clean_text(str(part)) for part in parts if _clean_text(str(part)))


def _choose_custom_sections(
    *,
    raw_text: str,
    normalized_raw_text: str,
    rule_sections: list[dict] | list,
    ai_sections: list[dict] | list,
) -> list[dict]:
    supported_sections: list[dict] = []
    for section in ai_sections:
        title = (
            _clean_text(section.get("title", ""))
            if isinstance(section, dict)
            else _clean_text(getattr(section, "title", ""))
        )
        items_source = (
            section.get("items", [])
            if isinstance(section, dict)
            else getattr(section, "items", [])
        )
        if not title or not _appears_in_raw_text(title, normalized_raw_text):
            continue
        items: list[dict[str, object]] = []
        for item in items_source:
            item_title = (
                _clean_text(item.get("title", ""))
                if isinstance(item, dict)
                else _clean_text(getattr(item, "title", ""))
            )
            subtitle = (
                _clean_text(item.get("subtitle", ""))
                if isinstance(item, dict)
                else _clean_text(getattr(item, "subtitle", ""))
            )
            years = (
                _clean_text(item.get("years", ""))
                if isinstance(item, dict)
                else _clean_text(getattr(item, "years", ""))
            )
            description_source = (
                item.get("description", [])
                if isinstance(item, dict)
                else getattr(item, "description", [])
            )
            description = _filter_supported_items(
                items=[str(value) for value in description_source],
                raw_text=raw_text,
                normalized_raw_text=normalized_raw_text,
                limit=LIST_LIMITS["custom_section_items"],
                use_overlap=True,
            )
            if not any([item_title, subtitle, years, description]):
                continue
            if item_title and not _has_text_overlap(item_title, raw_text):
                continue
            items.append(
                {
                    "title": item_title,
                    "subtitle": subtitle,
                    "years": years,
                    "description": description,
                }
            )
        if items:
            supported_sections.append({"title": title, "items": items})
    if supported_sections:
        return supported_sections
    return list(rule_sections)


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
        cleaned = cleaned.replace(",", "，").replace(";", "；").replace(":", "：")
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
