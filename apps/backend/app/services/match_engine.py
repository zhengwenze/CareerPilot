from __future__ import annotations

import re
from dataclasses import dataclass
from math import isclose

from app.schemas.job import JobStructuredData
from app.schemas.resume import ResumeStructuredData
from app.services.job_parser import KEYWORD_PHRASES, SKILL_KEYWORDS

EXPERIENCE_SPAN_PATTERN = re.compile(r"(20\d{2})\s*[./-]\s*(20\d{2}|至今|present)", re.IGNORECASE)
LOCATION_KEYWORDS = ["上海", "北京", "杭州", "深圳", "广州", "成都", "苏州", "南京", "remote"]
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
DIMENSION_WEIGHTS = {
    "required_skills": 35.0,
    "preferred_skills": 15.0,
    "responsibility_keywords": 20.0,
    "experience_level": 15.0,
    "education_and_location": 15.0,
}


@dataclass(slots=True)
class RuleMatchResult:
    overall_score: float
    dimension_scores: dict[str, float]
    strengths: list[dict[str, object]]
    gaps: list[dict[str, object]]
    actions: list[dict[str, object]]
    evidence: dict[str, object]


@dataclass(slots=True)
class ResumeEvidenceProfile:
    skills: list[str]
    keywords: list[str]
    locations: list[str]
    education_level: int | None
    estimated_years: float
    experience_evidence: list[str]
    project_evidence: list[str]


def _normalize_text(value: str) -> str:
    return value.strip().lower()


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(normalized)
    return result


def _extract_resume_skills(resume: ResumeStructuredData, raw_text: str | None) -> list[str]:
    candidates = [
        *resume.skills.technical,
        *resume.skills.tools,
        *resume.skills.languages,
        *resume.projects,
        *resume.work_experience,
        raw_text or "",
    ]
    joined = " ".join(candidates).lower()
    return _dedupe([keyword for keyword in SKILL_KEYWORDS if keyword.lower() in joined])


def _extract_resume_keywords(resume: ResumeStructuredData, raw_text: str | None) -> list[str]:
    candidates = [
        *resume.projects,
        *resume.work_experience,
        resume.basic_info.summary,
        raw_text or "",
    ]
    joined = " ".join(candidates).lower()
    return _dedupe([keyword for keyword in KEYWORD_PHRASES if keyword.lower() in joined])


def _extract_resume_locations(resume: ResumeStructuredData, raw_text: str | None) -> list[str]:
    joined = " ".join(
        [
            resume.basic_info.location,
            resume.basic_info.summary,
            raw_text or "",
        ]
    ).lower()
    return [keyword for keyword in LOCATION_KEYWORDS if keyword.lower() in joined]


def _extract_resume_education_level(
    resume: ResumeStructuredData, raw_text: str | None
) -> int | None:
    joined = " ".join([*resume.education, raw_text or ""]).lower()
    for label, level in sorted(EDUCATION_ORDER.items(), key=lambda item: item[1], reverse=True):
        if label.lower() in joined:
            return level
    return None


def _estimate_resume_years(resume: ResumeStructuredData, raw_text: str | None) -> float:
    total_years = 0.0
    if raw_text:
        for start, end in EXPERIENCE_SPAN_PATTERN.findall(raw_text):
            end_year = 2026 if end.lower() in {"至今", "present"} else int(end)
            total_years += max(0, end_year - int(start))

    if isclose(total_years, 0.0):
        work_count = len([item for item in resume.work_experience if item.strip()])
        if work_count == 0:
            return 0.0
        if work_count == 1:
            return 1.5
        if work_count == 2:
            return 3.0
        return min(8.0, 4.0 + (work_count - 3) * 1.5)

    return min(12.0, total_years)


def _coverage_score(required: list[str], matched: list[str], *, weight: float) -> float:
    if not required:
        return weight
    matched_lower = {item.lower() for item in matched}
    required_lower = [item.lower() for item in required]
    hit_count = sum(1 for item in required_lower if item in matched_lower)
    return round(weight * (hit_count / len(required_lower)), 2)


def build_resume_evidence_profile(
    *,
    resume: ResumeStructuredData,
    resume_raw_text: str | None,
) -> ResumeEvidenceProfile:
    resume_skills = _extract_resume_skills(resume, resume_raw_text)
    resume_keywords = _extract_resume_keywords(resume, resume_raw_text)
    resume_locations = _extract_resume_locations(resume, resume_raw_text)
    resume_years = _estimate_resume_years(resume, resume_raw_text)
    resume_education_level = _extract_resume_education_level(resume, resume_raw_text)
    return ResumeEvidenceProfile(
        skills=resume_skills,
        keywords=resume_keywords,
        locations=resume_locations,
        education_level=resume_education_level,
        estimated_years=resume_years,
        experience_evidence=[item for item in resume.work_experience if item.strip()],
        project_evidence=[item for item in resume.projects if item.strip()],
    )


def build_rule_match_result(
    *,
    resume: ResumeStructuredData,
    resume_raw_text: str | None,
    job: JobStructuredData,
) -> RuleMatchResult:
    profile = build_resume_evidence_profile(resume=resume, resume_raw_text=resume_raw_text)
    resume_skills = profile.skills
    resume_keywords = profile.keywords
    resume_locations = profile.locations
    resume_years = profile.estimated_years
    resume_education_level = profile.education_level

    required_skill_score = _coverage_score(
        job.requirements.required_skills,
        resume_skills,
        weight=DIMENSION_WEIGHTS["required_skills"],
    )
    preferred_skill_score = _coverage_score(
        job.requirements.preferred_skills,
        resume_skills,
        weight=DIMENSION_WEIGHTS["preferred_skills"],
    )

    jd_keywords = _dedupe([*job.requirements.required_keywords, *job.responsibilities])
    responsibility_score = _coverage_score(
        jd_keywords,
        resume_keywords + resume_skills + resume.work_experience + resume.projects,
        weight=DIMENSION_WEIGHTS["responsibility_keywords"],
    )

    required_years = float(job.requirements.experience_min_years or 0)
    if required_years <= 0:
        experience_score = DIMENSION_WEIGHTS["experience_level"]
    else:
        experience_score = round(
            DIMENSION_WEIGHTS["experience_level"] * min(resume_years / required_years, 1.0),
            2,
        )

    education_score = DIMENSION_WEIGHTS["education_and_location"] / 2
    required_education = EDUCATION_ORDER.get(job.requirements.education or "", 0)
    if required_education > 0:
        education_score = round(
            (DIMENSION_WEIGHTS["education_and_location"] / 2)
            * min((resume_education_level or 0) / required_education, 1.0),
            2,
        )

    location_score = DIMENSION_WEIGHTS["education_and_location"] / 2
    if job.basic.job_city:
        location_score = (
            DIMENSION_WEIGHTS["education_and_location"] / 2
            if any(job.basic.job_city.lower() in item.lower() for item in resume_locations)
            else 0.0
        )

    dimension_scores = {
        "required_skills": required_skill_score,
        "preferred_skills": preferred_skill_score,
        "responsibility_keywords": responsibility_score,
        "experience_level": experience_score,
        "education_and_location": round(education_score + location_score, 2),
    }
    overall_score = round(sum(dimension_scores.values()), 2)

    matched_required_skills = [
        skill
        for skill in job.requirements.required_skills
        if skill.lower() in {item.lower() for item in resume_skills}
    ]
    missing_required_skills = [
        skill
        for skill in job.requirements.required_skills
        if skill.lower() not in {item.lower() for item in resume_skills}
    ]
    matched_keywords = [
        keyword
        for keyword in job.requirements.required_keywords
        if keyword.lower() in {item.lower() for item in resume_keywords}
    ]
    missing_keywords = [
        keyword
        for keyword in job.requirements.required_keywords
        if keyword.lower() not in {item.lower() for item in resume_keywords}
    ]

    strengths = [
        {
            "label": item,
            "reason": "JD 关键能力在简历技能或经历中存在直接证据",
            "severity": "high",
        }
        for item in _dedupe(matched_required_skills + matched_keywords)[:4]
    ]
    gaps = [
        {
            "label": item,
            "reason": "JD 明确要求，但当前简历中缺少直接证据",
            "severity": "high" if item in missing_required_skills else "medium",
        }
        for item in _dedupe(missing_required_skills + missing_keywords)[:5]
    ]

    actions: list[dict[str, object]] = []
    priority = 1
    for item in missing_required_skills[:3]:
        actions.append(
            {
                "priority": priority,
                "title": f"补强 {item} 相关证据",
                "description": f"在项目经历或工作经历中补充 {item} 的实际场景、结果和指标。",
            }
        )
        priority += 1
    if (
        job.requirements.experience_min_years
        and resume_years < job.requirements.experience_min_years
    ):
        actions.append(
            {
                "priority": priority,
                "title": "补充更高阶经历表述",
                "description": (
                    "将复杂项目、跨团队协作和业务影响写得更具体，"
                    "以弥补经验年限感知不足。"
                ),
            }
        )
        priority += 1
    if not actions:
        actions.append(
            {
                "priority": 1,
                "title": "强化结果量化",
                "description": "在简历中增加指标变化、业务结果和个人贡献占比，让匹配优势更稳定。",
            }
        )

    evidence = {
        "candidate_profile": {
            "skills": resume_skills[:8],
            "keywords": resume_keywords[:8],
            "estimated_years": resume_years,
            "locations": resume_locations[:4],
        },
        "matched_resume_fields": {
            "skills": matched_required_skills[:5],
            "projects": [
                item
                for item in profile.project_evidence
                if any(term.lower() in item.lower() for term in matched_keywords[:3])
            ][:3],
            "work_experience": [
                item
                for item in profile.experience_evidence
                if any(
                    term.lower() in item.lower()
                    for term in matched_required_skills[:3] + matched_keywords[:3]
                )
            ][:3],
        },
        "matched_jd_fields": {
            "required_skills": matched_required_skills[:5],
            "required_keywords": matched_keywords[:5],
            "must_have": job.must_have[:5],
            "responsibility_clusters": [cluster.name for cluster in job.responsibility_clusters[:3]],
        },
        "missing_items": _dedupe(missing_required_skills + missing_keywords)[:6],
        "missing_must_have": missing_required_skills[:5],
        "responsibility_alignment": {
            "matched": [
                item
                for item in job.responsibilities[:5]
                if any(keyword.lower() in " ".join(profile.keywords).lower() for keyword in item.split())
            ][:3],
            "unmatched": [
                item
                for item in job.responsibilities[:5]
                if item
                not in [
                    matched_item
                    for matched_item in job.responsibilities[:5]
                    if any(
                        keyword.lower() in " ".join(profile.keywords).lower()
                        for keyword in matched_item.split()
                    )
                ]
            ][:3],
        },
        "notes": [
            "规则分基于技能覆盖、关键词覆盖、职责匹配、经验等级和教育地点五个维度。",
        ],
        "ai_correction": {
            "provider": "disabled",
            "model": None,
            "status": "skipped",
            "delta": 0,
            "reasoning": "AI correction is disabled",
        },
    }

    return RuleMatchResult(
        overall_score=overall_score,
        dimension_scores=dimension_scores,
        strengths=strengths,
        gaps=gaps,
        actions=actions,
        evidence=evidence,
    )
