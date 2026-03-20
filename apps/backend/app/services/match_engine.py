from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from math import isclose
from typing import Literal

from app.schemas.job import JobStructuredData
from app.schemas.resume import (
    ResumeProjectItem,
    ResumeStructuredData,
    ResumeWorkExperienceItem,
)
from app.services.job_parser import KEYWORD_PHRASES, SKILL_KEYWORDS

EXPERIENCE_SPAN_PATTERN = re.compile(
    r"(20\d{2})\s*[./-]\s*(20\d{2}|至今|present|now|current)",
    re.IGNORECASE,
)
TEXT_TOKEN_PATTERN = re.compile(r"[a-z0-9+#./-]+|[\u4e00-\u9fff]{2,}", re.IGNORECASE)
LOCATION_KEYWORDS = ["上海", "北京", "杭州", "深圳", "广州", "成都", "苏州", "南京", "remote", "远程"]
EDUCATION_ORDER = {
    "专科": 1,
    "专科及以上": 1,
    "本科": 2,
    "本科及以上": 2,
    "硕士": 3,
    "硕士及以上": 3,
    "博士": 4,
    "博士及以上": 4,
}
RULE_DIMENSION_WEIGHTS = {
    "required_skills": 30.0,
    "preferred_skills": 10.0,
    "responsibilities": 20.0,
    "domain_keywords": 10.0,
    "experience_years": 15.0,
    "education": 10.0,
    "location": 5.0,
}
SEMANTIC_DIMENSION_WEIGHTS = {
    "required_skills": 0.35,
    "responsibilities": 0.35,
    "domain_keywords": 0.15,
    "preferred_skills": 0.10,
    "must_have": 0.05,
}


@dataclass(slots=True)
class EvidenceSnippet:
    snippet_id: str
    source_type: Literal["summary", "work_experience", "project", "raw_text"]
    source_label: str
    text: str
    skills: list[str]
    keywords: list[str]


@dataclass(slots=True)
class ResumeEvidenceProfile:
    skills: list[str]
    keywords: list[str]
    locations: list[str]
    education_level: int | None
    education_label: str | None
    estimated_years: float
    summary: str
    experience_evidence: list[str]
    project_evidence: list[str]
    evidence_snippets: list[EvidenceSnippet]


@dataclass(slots=True)
class RuleMatchResult:
    overall_score: float
    rule_score: float
    semantic_score: float
    dimension_scores: dict[str, float]
    strengths: list[dict[str, object]]
    gaps: list[dict[str, object]]
    actions: list[dict[str, object]]
    evidence: dict[str, object]
    evidence_map: dict[str, object]


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _tokenize_text(value: str) -> list[str]:
    return [token.lower() for token in TEXT_TOKEN_PATTERN.findall(value.lower())]


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = _normalize_text(item)
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(normalized)
    return result


def _extract_resume_skills(resume: ResumeStructuredData, raw_text: str | None) -> list[str]:
    explicit = [
        *resume.skills.technical,
        *resume.skills.tools,
        *resume.skills.languages,
    ]
    implicit_parts: list[str] = []
    for item in resume.work_experience_items:
        implicit_parts.extend(bullet.text for bullet in item.bullets)
        for bullet in item.bullets:
            implicit_parts.extend(bullet.skills_used)
    for item in resume.project_items:
        implicit_parts.append(item.summary)
        implicit_parts.extend(item.skills_used)
        implicit_parts.extend(bullet.text for bullet in item.bullets)
        for bullet in item.bullets:
            implicit_parts.extend(bullet.skills_used)
    implicit_parts.extend(resume.projects)
    implicit_parts.extend(resume.work_experience)
    implicit_parts.append(raw_text or "")
    joined = " ".join(str(part) for part in [*explicit, *implicit_parts]).lower()
    matched = [keyword for keyword in SKILL_KEYWORDS if keyword.lower() in joined]
    return _dedupe([*explicit, *matched])


def _extract_resume_keywords(resume: ResumeStructuredData, raw_text: str | None) -> list[str]:
    candidates = [
        resume.basic_info.summary,
        *resume.education,
        *resume.projects,
        *resume.work_experience,
        raw_text or "",
    ]
    for item in resume.work_experience_items:
        candidates.extend(bullet.text for bullet in item.bullets)
    for item in resume.project_items:
        candidates.append(item.summary)
        candidates.extend(bullet.text for bullet in item.bullets)
    joined = " ".join(candidates).lower()
    detected = [keyword for keyword in KEYWORD_PHRASES if keyword.lower() in joined]
    return _dedupe(detected)


def _extract_resume_locations(resume: ResumeStructuredData, raw_text: str | None) -> list[str]:
    joined = " ".join(
        [
            resume.basic_info.location,
            resume.basic_info.summary,
            raw_text or "",
            *resume.work_experience,
            *resume.projects,
        ]
    ).lower()
    return [keyword for keyword in LOCATION_KEYWORDS if keyword.lower() in joined]


def _extract_resume_education_level(
    resume: ResumeStructuredData, raw_text: str | None
) -> tuple[int | None, str | None]:
    joined = " ".join(
        [
            *resume.education,
            *(item.degree for item in resume.education_items),
            raw_text or "",
        ]
    ).lower()
    for label, level in sorted(EDUCATION_ORDER.items(), key=lambda item: item[1], reverse=True):
        if label.lower() in joined:
            return level, label
    return None, None


def _estimate_years_from_text(text: str) -> float:
    total_years = 0.0
    for start, end in EXPERIENCE_SPAN_PATTERN.findall(text):
        end_year = datetime.now(UTC).year if end.lower() in {"至今", "present", "now", "current"} else int(end)
        total_years += max(0, end_year - int(start))
    return total_years


def _estimate_resume_years(resume: ResumeStructuredData, raw_text: str | None) -> float:
    item_text = " ".join(
        [
            *resume.work_experience,
            *resume.projects,
            *[
                " ".join([item.start_date, item.end_date])
                for item in resume.work_experience_items
            ],
            *[
                " ".join([item.start_date, item.end_date])
                for item in resume.project_items
            ],
            raw_text or "",
        ]
    )
    total_years = _estimate_years_from_text(item_text)
    if isclose(total_years, 0.0):
        work_count = len([item for item in resume.work_experience if item.strip()])
        if work_count == 0:
            return 0.0
        if work_count == 1:
            return 1.5
        if work_count == 2:
            return 3.0
        return min(10.0, 4.0 + (work_count - 3) * 1.5)
    return min(15.0, total_years)


def _build_snippet_text_for_work_item(item: ResumeWorkExperienceItem) -> str:
    parts = [
        item.company,
        item.title,
        item.location,
        item.start_date,
        item.end_date,
        *[bullet.text for bullet in item.bullets],
    ]
    return _normalize_text(" ".join(part for part in parts if part))


def _build_snippet_text_for_project_item(item: ResumeProjectItem) -> str:
    parts = [
        item.name,
        item.role,
        item.start_date,
        item.end_date,
        item.summary,
        *[bullet.text for bullet in item.bullets],
    ]
    return _normalize_text(" ".join(part for part in parts if part))


def _build_evidence_snippets(
    resume: ResumeStructuredData,
    raw_text: str | None,
) -> list[EvidenceSnippet]:
    snippets: list[EvidenceSnippet] = []

    if resume.basic_info.summary:
        snippets.append(
            EvidenceSnippet(
                snippet_id="summary",
                source_type="summary",
                source_label="职业摘要",
                text=resume.basic_info.summary,
                skills=_dedupe(
                    [
                        skill
                        for skill in (*resume.skills.technical, *resume.skills.tools)
                        if skill and skill.lower() in resume.basic_info.summary.lower()
                    ]
                ),
                keywords=[
                    keyword
                    for keyword in KEYWORD_PHRASES
                    if keyword.lower() in resume.basic_info.summary.lower()
                ],
            )
        )

    if resume.work_experience_items:
        for index, item in enumerate(resume.work_experience_items, start=1):
            combined_text = _build_snippet_text_for_work_item(item)
            if combined_text:
                snippets.append(
                    EvidenceSnippet(
                        snippet_id=item.id or f"work_{index}",
                        source_type="work_experience",
                        source_label=_normalize_text(" ".join(part for part in [item.company, item.title] if part))
                        or f"工作经历 {index}",
                        text=combined_text,
                        skills=_dedupe(
                            [
                                *[skill for bullet in item.bullets for skill in bullet.skills_used],
                                *[
                                    skill
                                    for skill in SKILL_KEYWORDS
                                    if skill.lower() in combined_text.lower()
                                ],
                            ]
                        ),
                        keywords=_dedupe(
                            [
                                keyword
                                for keyword in KEYWORD_PHRASES
                                if keyword.lower() in combined_text.lower()
                            ]
                        ),
                    )
                )
            for bullet_index, bullet in enumerate(item.bullets, start=1):
                bullet_text = _normalize_text(bullet.text)
                if not bullet_text:
                    continue
                snippets.append(
                    EvidenceSnippet(
                        snippet_id=bullet.id or f"{item.id or f'work_{index}'}_b{bullet_index}",
                        source_type="work_experience",
                        source_label=_normalize_text(
                            " ".join(part for part in [item.company, item.title] if part)
                        )
                        or f"工作经历 {index}",
                        text=bullet_text,
                        skills=_dedupe(
                            [
                                *bullet.skills_used,
                                *[
                                    skill
                                    for skill in SKILL_KEYWORDS
                                    if skill.lower() in bullet_text.lower()
                                ],
                            ]
                        ),
                        keywords=_dedupe(
                            [
                                keyword
                                for keyword in KEYWORD_PHRASES
                                if keyword.lower() in bullet_text.lower()
                            ]
                        ),
                    )
                )

    if resume.project_items:
        for index, item in enumerate(resume.project_items, start=1):
            combined_text = _build_snippet_text_for_project_item(item)
            if combined_text:
                snippets.append(
                    EvidenceSnippet(
                        snippet_id=item.id or f"proj_{index}",
                        source_type="project",
                        source_label=item.name or f"项目经历 {index}",
                        text=combined_text,
                        skills=_dedupe(
                            [
                                *item.skills_used,
                                *[
                                    skill
                                    for skill in SKILL_KEYWORDS
                                    if skill.lower() in combined_text.lower()
                                ],
                            ]
                        ),
                        keywords=_dedupe(
                            [
                                keyword
                                for keyword in KEYWORD_PHRASES
                                if keyword.lower() in combined_text.lower()
                            ]
                        ),
                    )
                )
            for bullet_index, bullet in enumerate(item.bullets, start=1):
                bullet_text = _normalize_text(bullet.text)
                if not bullet_text:
                    continue
                snippets.append(
                    EvidenceSnippet(
                        snippet_id=bullet.id or f"{item.id or f'proj_{index}'}_b{bullet_index}",
                        source_type="project",
                        source_label=item.name or f"项目经历 {index}",
                        text=bullet_text,
                        skills=_dedupe(
                            [
                                *item.skills_used,
                                *bullet.skills_used,
                                *[
                                    skill
                                    for skill in SKILL_KEYWORDS
                                    if skill.lower() in bullet_text.lower()
                                ],
                            ]
                        ),
                        keywords=_dedupe(
                            [
                                keyword
                                for keyword in KEYWORD_PHRASES
                                if keyword.lower() in bullet_text.lower()
                            ]
                        ),
                    )
                )

    if not snippets:
        for index, text in enumerate([*resume.work_experience, *resume.projects], start=1):
            normalized = _normalize_text(text)
            if not normalized:
                continue
            source_type = "work_experience" if index <= len(resume.work_experience) else "project"
            snippets.append(
                EvidenceSnippet(
                    snippet_id=f"legacy_{index}",
                    source_type=source_type,
                    source_label=f"简历片段 {index}",
                    text=normalized,
                    skills=_dedupe(
                        [skill for skill in SKILL_KEYWORDS if skill.lower() in normalized.lower()]
                    ),
                    keywords=_dedupe(
                        [keyword for keyword in KEYWORD_PHRASES if keyword.lower() in normalized.lower()]
                    ),
                )
            )

    if raw_text and raw_text.strip():
        snippets.append(
            EvidenceSnippet(
                snippet_id="raw_text",
                source_type="raw_text",
                source_label="原始简历文本",
                text=_normalize_text(raw_text)[:800],
                skills=[],
                keywords=[],
            )
        )

    return snippets


def _coverage_score(required: list[str], matched: list[str], *, weight: float) -> float:
    if not required:
        return weight
    matched_lower = {item.lower() for item in matched}
    required_lower = [item.lower() for item in required]
    hit_count = sum(1 for item in required_lower if item in matched_lower)
    return round(weight * (hit_count / len(required_lower)), 2)


def _ratio_score(numerator: float, denominator: float, *, weight: float) -> float:
    if denominator <= 0:
        return weight
    return round(weight * min(max(numerator, 0.0) / denominator, 1.0), 2)


def _jaccard_score(left: str, right: str) -> float:
    left_tokens = set(_tokenize_text(left))
    right_tokens = set(_tokenize_text(right))
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    if union == 0:
        return 0.0
    return intersection / union


def _contains_requirement(requirement: str, text: str) -> bool:
    return requirement.lower() in text.lower()


def _score_requirement_against_snippet(requirement: str, snippet: EvidenceSnippet) -> float:
    if _contains_requirement(requirement, snippet.text):
        return 1.0
    if any(requirement.lower() == skill.lower() for skill in snippet.skills):
        return 0.95
    lexical = _jaccard_score(requirement, snippet.text)
    keyword_bonus = 0.15 if any(token.lower() == requirement.lower() for token in snippet.keywords) else 0.0
    return min(0.92, lexical + keyword_bonus)


def _best_requirement_match(
    requirement: str,
    snippets: list[EvidenceSnippet],
) -> tuple[EvidenceSnippet | None, float]:
    best_snippet: EvidenceSnippet | None = None
    best_score = 0.0
    for snippet in snippets:
        score = _score_requirement_against_snippet(requirement, snippet)
        if score > best_score:
            best_score = score
            best_snippet = snippet
    return best_snippet, round(best_score, 4)


def _fit_band_from_score(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 72:
        return "strong"
    if score >= 55:
        return "partial"
    return "weak"


def _build_requirement_groups(job: JobStructuredData) -> dict[str, list[str]]:
    return {
        "required_skills": _dedupe(job.requirements.required_skills)[:10],
        "preferred_skills": _dedupe([*job.requirements.preferred_skills, *job.nice_to_have])[:8],
        "responsibilities": _dedupe(job.responsibilities)[:8],
        "domain_keywords": _dedupe(job.domain_context.keywords)[:8],
        "must_have": _dedupe(job.must_have)[:8],
    }


def build_resume_evidence_profile(
    *,
    resume: ResumeStructuredData,
    resume_raw_text: str | None,
) -> ResumeEvidenceProfile:
    resume_skills = _extract_resume_skills(resume, resume_raw_text)
    resume_keywords = _extract_resume_keywords(resume, resume_raw_text)
    resume_locations = _extract_resume_locations(resume, resume_raw_text)
    resume_years = _estimate_resume_years(resume, resume_raw_text)
    resume_education_level, resume_education_label = _extract_resume_education_level(
        resume,
        resume_raw_text,
    )
    evidence_snippets = _build_evidence_snippets(resume, resume_raw_text)
    return ResumeEvidenceProfile(
        skills=resume_skills,
        keywords=resume_keywords,
        locations=resume_locations,
        education_level=resume_education_level,
        education_label=resume_education_label,
        estimated_years=resume_years,
        summary=resume.basic_info.summary,
        experience_evidence=[item for item in resume.work_experience if item.strip()],
        project_evidence=[item for item in resume.projects if item.strip()],
        evidence_snippets=evidence_snippets,
    )


def build_rule_match_result(
    *,
    resume: ResumeStructuredData,
    resume_raw_text: str | None,
    job: JobStructuredData,
) -> RuleMatchResult:
    profile = build_resume_evidence_profile(resume=resume, resume_raw_text=resume_raw_text)
    requirement_groups = _build_requirement_groups(job)

    required_skill_score = _coverage_score(
        job.requirements.required_skills,
        profile.skills,
        weight=RULE_DIMENSION_WEIGHTS["required_skills"],
    )
    preferred_skill_score = _coverage_score(
        job.requirements.preferred_skills,
        profile.skills,
        weight=RULE_DIMENSION_WEIGHTS["preferred_skills"],
    )
    responsibility_score = _coverage_score(
        job.responsibilities,
        [
            *profile.keywords,
            *profile.skills,
            *profile.experience_evidence,
            *profile.project_evidence,
        ],
        weight=RULE_DIMENSION_WEIGHTS["responsibilities"],
    )
    domain_keyword_score = _coverage_score(
        job.domain_context.keywords,
        [*profile.keywords, *profile.skills, *profile.experience_evidence, *profile.project_evidence],
        weight=RULE_DIMENSION_WEIGHTS["domain_keywords"],
    )

    required_years = float(job.requirements.experience_min_years or 0)
    experience_score = _ratio_score(
        profile.estimated_years,
        required_years,
        weight=RULE_DIMENSION_WEIGHTS["experience_years"],
    )

    required_education = EDUCATION_ORDER.get(job.requirements.education or "", 0)
    education_score = _ratio_score(
        float(profile.education_level or 0),
        float(required_education),
        weight=RULE_DIMENSION_WEIGHTS["education"],
    )

    location_score = RULE_DIMENSION_WEIGHTS["location"]
    if job.basic.job_city:
        location_score = (
            RULE_DIMENSION_WEIGHTS["location"]
            if any(job.basic.job_city.lower() in item.lower() for item in profile.locations)
            else 0.0
        )

    dimension_scores = {
        "required_skills": required_skill_score,
        "preferred_skills": preferred_skill_score,
        "responsibilities": responsibility_score,
        "domain_keywords": domain_keyword_score,
        "experience_years": experience_score,
        "education": education_score,
        "location": round(location_score, 2),
    }
    rule_score = round(sum(dimension_scores.values()), 2)

    requirement_matches: list[dict[str, object]] = []
    semantic_dimension_details: dict[str, list[float]] = {key: [] for key in SEMANTIC_DIMENSION_WEIGHTS}
    matched_resume_skills: list[str] = []
    matched_projects: list[str] = []
    matched_work_experience: list[str] = []
    missing_items: list[str] = []

    for category, requirements in requirement_groups.items():
        if not requirements:
            continue
        for requirement in requirements:
            snippet, score = _best_requirement_match(requirement, profile.evidence_snippets)
            is_matched = score >= 0.45
            semantic_dimension_details[category].append(score)
            if not is_matched:
                missing_items.append(requirement)
            else:
                if requirement in job.requirements.required_skills or requirement in job.requirements.preferred_skills:
                    matched_resume_skills.append(requirement)
                if snippet is not None and snippet.source_type == "project":
                    matched_projects.append(snippet.text)
                if snippet is not None and snippet.source_type == "work_experience":
                    matched_work_experience.append(snippet.text)

            requirement_matches.append(
                {
                    "requirement": requirement,
                    "category": category,
                    "matched": is_matched,
                    "similarity": round(score, 2),
                    "source_type": snippet.source_type if snippet is not None else None,
                    "source_label": snippet.source_label if snippet is not None else None,
                    "evidence_snippet_id": snippet.snippet_id if snippet is not None else None,
                    "evidence_snippet": snippet.text if snippet is not None else None,
                }
            )

    semantic_components: dict[str, float] = {}
    for category, weight_ratio in SEMANTIC_DIMENSION_WEIGHTS.items():
        scores = semantic_dimension_details[category]
        component = 1.0 if not scores else (sum(scores) / len(scores))
        semantic_components[category] = round(component * 100.0, 2)
    semantic_score = round(
        sum(semantic_components[key] * weight for key, weight in SEMANTIC_DIMENSION_WEIGHTS.items()),
        2,
    )

    matched_required_skills = [
        skill for skill in job.requirements.required_skills if skill.lower() in {item.lower() for item in profile.skills}
    ]
    matched_keywords = [
        keyword for keyword in job.domain_context.keywords if keyword.lower() in {item.lower() for item in profile.keywords}
    ]
    strengths = [
        {
            "label": item["requirement"],
            "reason": (
                f"JD 要求可定位到简历证据：{item['source_label'] or '简历片段'}"
                if item.get("matched")
                else "JD 要求在简历中存在部分相关表述。"
            ),
            "severity": "high" if item["category"] in {"required_skills", "responsibilities"} else "medium",
        }
        for item in sorted(
            [match for match in requirement_matches if match["matched"]],
            key=lambda value: float(value["similarity"]),
            reverse=True,
        )[:5]
    ]
    gaps = []
    for item in requirement_matches:
        if item["matched"]:
            continue
        label = str(item["requirement"])
        reason = "JD 明确要求，但当前简历中缺少可直接引用的证据片段。"
        if item["category"] == "experience_years":
            reason = "岗位要求的经验年限高于当前简历可感知的经验强度。"
        gaps.append(
            {
                "label": label,
                "reason": reason,
                "severity": "high" if item["category"] in {"required_skills", "must_have"} else "medium",
            }
        )
    if required_years > 0 and profile.estimated_years < required_years:
        gaps.append(
            {
                "label": f"{int(required_years)}年以上经验",
                "reason": "岗位对经验年限有明确要求，当前简历的年限信号偏弱。",
                "severity": "high",
            }
        )
    if required_education > 0 and (profile.education_level or 0) < required_education:
        gaps.append(
            {
                "label": job.requirements.education or "学历要求",
                "reason": "岗位对学历有明确要求，当前简历未体现足够匹配的学历信号。",
                "severity": "medium",
            }
        )
    gaps = _dedupe_gap_items(gaps)[:6]

    actions: list[dict[str, object]] = []
    for priority, gap in enumerate(gaps[:4], start=1):
        target_section = "projects" if "项目" in gap["label"] or "系统" in gap["label"] else "work_experience"
        actions.append(
            {
                "priority": priority,
                "title": f"补强 {gap['label']} 的证据表达",
                "description": f"围绕 {gap['label']} 补充具体场景、方法、结果和量化影响，避免只保留关键词。",
                "target_section": target_section,
            }
        )
    if not actions:
        actions.append(
            {
                "priority": 1,
                "title": "强化核心结果量化",
                "description": "把最相关经历补充为“场景-动作-结果”的表述，增加指标、规模和业务影响。",
                "target_section": "work_experience",
            }
        )

    candidate_profile = {
        "skills": profile.skills[:12],
        "keywords": profile.keywords[:10],
        "estimated_years": round(profile.estimated_years, 2),
        "education_level": profile.education_label,
        "locations": profile.locations[:4],
    }
    evidence_map = {
        "matched_resume_fields": {
            "skills": _dedupe(matched_required_skills + matched_resume_skills)[:8],
            "projects": _dedupe(matched_projects)[:4],
            "work_experience": _dedupe(matched_work_experience)[:4],
        },
        "matched_jd_fields": {
            "required_skills": matched_required_skills[:8],
            "preferred_skills": [
                item
                for item in job.requirements.preferred_skills
                if item.lower() in {skill.lower() for skill in profile.skills}
            ][:6],
            "required_keywords": matched_keywords[:8],
            "responsibilities": [
                item["requirement"]
                for item in requirement_matches
                if item["category"] == "responsibilities" and item["matched"]
            ][:5],
        },
        "missing_items": _dedupe(missing_items)[:8],
        "notes": [
            "rule_score 基于技能、职责、领域关键词、经验、学历和地点覆盖率。",
            "semantic_score 基于 JD 要求与具体简历片段的轻量文本相似匹配。",
        ],
        "candidate_profile": candidate_profile,
        "requirement_matches": requirement_matches[:16],
    }
    evidence = {
        "candidate_profile": candidate_profile,
        "evidence_snippets": [asdict(item) for item in profile.evidence_snippets[:16]],
        "rule_breakdown": dimension_scores,
        "semantic_breakdown": semantic_components,
        "fit_band_hint": _fit_band_from_score((rule_score + semantic_score) / 2),
    }

    return RuleMatchResult(
        overall_score=rule_score,
        rule_score=rule_score,
        semantic_score=semantic_score,
        dimension_scores=dimension_scores,
        strengths=strengths,
        gaps=gaps,
        actions=actions,
        evidence=evidence,
        evidence_map=evidence_map,
    )


def _dedupe_gap_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        label = str(item.get("label", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if not label or not reason:
            continue
        key = (label.lower(), reason.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "label": label,
                "reason": reason,
                "severity": str(item.get("severity", "medium")).strip() or "medium",
            }
        )
    return result
