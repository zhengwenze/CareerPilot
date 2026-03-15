from __future__ import annotations

import re
import unicodedata

from app.schemas.job import JobStructuredData

SKILL_KEYWORDS = [
    "Python",
    "SQL",
    "Excel",
    "Power BI",
    "Tableau",
    "Looker",
    "A/B Testing",
    "Airflow",
    "Spark",
    "Hadoop",
    "Pandas",
    "NumPy",
    "scikit-learn",
    "Machine Learning",
    "Deep Learning",
    "TensorFlow",
    "PyTorch",
    "Java",
    "C++",
    "JavaScript",
    "TypeScript",
    "React",
    "Next.js",
    "Vue",
    "FastAPI",
    "Django",
    "MySQL",
    "PostgreSQL",
    "Redis",
    "Docker",
    "Kubernetes",
    "Figma",
    "Product Sense",
    "数据分析",
    "数据建模",
    "指标体系",
    "实验分析",
    "增长分析",
    "用户研究",
]

KEYWORD_PHRASES = [
    "指标体系",
    "实验分析",
    "增长分析",
    "用户增长",
    "商业分析",
    "数据建模",
    "数据治理",
    "报表建设",
    "看板建设",
    "埋点设计",
    "跨团队协作",
    "项目管理",
    "业务分析",
    "需求分析",
    "战略分析",
]

EDUCATION_KEYWORDS = [
    "博士及以上",
    "硕士及以上",
    "本科及以上",
    "本科",
    "专科及以上",
    "专科",
]

RESPONSIBILITY_HEADINGS = ("岗位职责", "工作职责", "职责描述", "你将负责", "你需要负责")
PREFERRED_MARKERS = ("加分", "优先", "bonus", "preferred", "plus")
BENEFIT_HEADINGS = ("福利", "待遇", "我们提供", "你将获得")
EXPERIENCE_PATTERN = re.compile(r"(\d+)\s*(?:\+)?\s*年")
BULLET_PREFIX = re.compile(r"^(?:[-*•·]|[0-9]+[.)、])\s*")


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\u3000", " ")
    return normalized.strip()


def _normalize_lines(raw_text: str) -> list[str]:
    return [_normalize_text(line) for line in raw_text.splitlines() if _normalize_text(line)]


def _extract_keywords(haystack: str, keywords: list[str]) -> list[str]:
    lowered = haystack.lower()
    found: list[str] = []
    for keyword in keywords:
        if keyword.lower() in lowered and keyword not in found:
            found.append(keyword)
    return found


def _extract_experience_years(raw_text: str) -> int | None:
    matches = [int(match.group(1)) for match in EXPERIENCE_PATTERN.finditer(raw_text)]
    if not matches:
        return None
    return max(matches)


def _extract_education(raw_text: str) -> str | None:
    lowered = raw_text.lower()
    for keyword in EDUCATION_KEYWORDS:
        if keyword.lower() in lowered:
            return keyword
    return None


def _collect_section_lines(lines: list[str], headings: tuple[str, ...]) -> list[str]:
    items: list[str] = []
    active = False
    lowered_headings = tuple(item.lower() for item in headings)

    for line in lines:
        lowered = line.lower().rstrip(":：")
        if lowered in lowered_headings:
            active = True
            continue
        if active and any(
            lowered.startswith(marker.lower())
            for marker in RESPONSIBILITY_HEADINGS + BENEFIT_HEADINGS
        ):
            break
        if active:
            cleaned = BULLET_PREFIX.sub("", line).strip()
            if cleaned:
                items.append(cleaned)
    return items


def _extract_responsibilities(lines: list[str]) -> list[str]:
    items = _collect_section_lines(lines, RESPONSIBILITY_HEADINGS)
    if items:
        return items[:6]
    fallback: list[str] = []
    for line in lines:
        cleaned = BULLET_PREFIX.sub("", line).strip()
        if len(cleaned) >= 8 and any(
            token in cleaned for token in ("负责", "推进", "支持", "分析", "建设", "协作")
        ):
            fallback.append(cleaned)
        if len(fallback) >= 6:
            break
    return fallback


def _extract_benefits(lines: list[str]) -> list[str]:
    items = _collect_section_lines(lines, BENEFIT_HEADINGS)
    if items:
        return items[:6]
    fallback: list[str] = []
    for line in lines:
        cleaned = BULLET_PREFIX.sub("", line).strip()
        if any(
            token in cleaned
            for token in ("双休", "弹性", "餐补", "年终", "福利", "带薪", "五险一金")
        ):
            fallback.append(cleaned)
    return fallback[:6]


def _extract_preferred_skills(lines: list[str]) -> list[str]:
    preferred_skills: list[str] = []
    for line in lines:
        lowered = line.lower()
        marker_positions = [
            lowered.find(marker) for marker in PREFERRED_MARKERS if marker in lowered
        ]
        if not marker_positions:
            continue
        marker_index = min(position for position in marker_positions if position >= 0)
        for skill in SKILL_KEYWORDS:
            skill_index = lowered.find(skill.lower())
            if skill_index == -1:
                continue
            if abs(skill_index - marker_index) <= 16 and skill not in preferred_skills:
                preferred_skills.append(skill)
    return preferred_skills


def _build_summary(title: str, required_skills: list[str], responsibilities: list[str]) -> str:
    summary_parts = [title]
    if required_skills:
        summary_parts.append(f"核心技能：{', '.join(required_skills[:4])}")
    if responsibilities:
        summary_parts.append(f"重点职责：{responsibilities[0]}")
    return "；".join(part for part in summary_parts if part)


def build_structured_job(
    *,
    title: str,
    company: str | None,
    job_city: str | None,
    employment_type: str | None,
    jd_text: str,
) -> JobStructuredData:
    normalized_text = _normalize_text(jd_text)
    lines = _normalize_lines(normalized_text)
    joined = " ".join(lines)

    preferred_skills = _extract_preferred_skills(lines)
    all_skills = _extract_keywords(joined, SKILL_KEYWORDS)
    required_skills = [skill for skill in all_skills if skill not in preferred_skills]
    responsibilities = _extract_responsibilities(lines)
    benefits = _extract_benefits(lines)

    return JobStructuredData(
        basic={
            "title": title,
            "company": company,
            "job_city": job_city,
            "employment_type": employment_type,
        },
        requirements={
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "required_keywords": _extract_keywords(joined, KEYWORD_PHRASES),
            "education": _extract_education(joined),
            "experience_min_years": _extract_experience_years(joined),
        },
        responsibilities=responsibilities,
        benefits=benefits,
        raw_summary=_build_summary(title, required_skills, responsibilities),
    )
