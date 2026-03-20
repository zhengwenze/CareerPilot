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
    "数据库设计",
    "性能优化",
    "后端开发",
    "接口设计",
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
    "数据库设计",
    "性能优化",
    "服务治理",
    "接口设计",
    "后端开发",
]

DOMAIN_LEXICON = [
    "增长",
    "数据",
    "分析",
    "推荐",
    "风控",
    "商业化",
    "运营",
    "后端",
    "架构",
    "数据库",
    "平台",
    "服务",
    "策略",
    "实验",
    "推荐系统",
    "B端",
    "C端",
]

EDUCATION_KEYWORDS = [
    "博士及以上",
    "博士",
    "硕士及以上",
    "硕士",
    "本科及以上",
    "本科",
    "专科及以上",
    "专科",
]

RESPONSIBILITY_HEADINGS = (
    "岗位职责",
    "工作职责",
    "职责描述",
    "你将负责",
    "你需要负责",
    "工作内容",
)
REQUIREMENT_HEADINGS = (
    "任职要求",
    "职位要求",
    "岗位要求",
    "任职资格",
    "任职条件",
    "我们希望你",
    "我们期待你",
)
PREFERRED_MARKERS = ("加分", "优先", "bonus", "preferred", "plus", "更佳")
BENEFIT_HEADINGS = ("福利", "待遇", "我们提供", "你将获得")
COMPANY_PATTERNS = (
    re.compile(r"(?:公司|企业|Company)[:：]\s*([^\n]+)", re.IGNORECASE),
    re.compile(r"(?:关于我们|About Us)[:：]\s*([^\n]+)", re.IGNORECASE),
)
CITY_KEYWORDS = [
    "上海",
    "北京",
    "杭州",
    "深圳",
    "广州",
    "成都",
    "苏州",
    "南京",
    "武汉",
    "远程",
    "remote",
]
EMPLOYMENT_TYPE_KEYWORDS = ["全职", "兼职", "实习", "校招", "社招", "remote", "远程"]
EXPERIENCE_PATTERN = re.compile(r"(\d+)\s*(?:\+)?\s*年")
BULLET_PREFIX = re.compile(r"^(?:[-*•·]|[0-9]+[.)、])\s*")


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\u3000", " ")
    return normalized.strip()


def _normalize_lines(raw_text: str) -> list[str]:
    return [_normalize_text(line) for line in raw_text.splitlines() if _normalize_text(line)]


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(cleaned)
    return result


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


def _looks_like_heading(line: str) -> bool:
    normalized = line.lower().rstrip(":：")
    return normalized in {
        *(item.lower() for item in RESPONSIBILITY_HEADINGS),
        *(item.lower() for item in REQUIREMENT_HEADINGS),
        *(item.lower() for item in BENEFIT_HEADINGS),
    }


def _collect_section_lines(lines: list[str], headings: tuple[str, ...]) -> list[str]:
    items: list[str] = []
    active = False
    lowered_headings = {item.lower() for item in headings}

    for line in lines:
        lowered = line.lower().rstrip(":：")
        if lowered in lowered_headings:
            active = True
            continue
        if active and _looks_like_heading(line):
            break
        if active:
            cleaned = BULLET_PREFIX.sub("", line).strip()
            if cleaned:
                items.append(cleaned)
    return items


def _extract_list_lines(lines: list[str]) -> list[str]:
    items: list[str] = []
    for line in lines:
        cleaned = BULLET_PREFIX.sub("", line).strip()
        if not cleaned:
            continue
        parts = re.split(r"[；;]", cleaned)
        for part in parts:
            normalized = part.strip("。 ")
            if normalized:
                items.append(normalized)
    return _dedupe(items)


def _extract_responsibilities(lines: list[str]) -> list[str]:
    items = _extract_list_lines(_collect_section_lines(lines, RESPONSIBILITY_HEADINGS))
    if items:
        return items[:8]

    fallback: list[str] = []
    for line in lines:
        cleaned = BULLET_PREFIX.sub("", line).strip()
        if len(cleaned) >= 8 and any(
            token in cleaned
            for token in ("负责", "推进", "支持", "分析", "建设", "协作", "开发", "优化")
        ):
            fallback.append(cleaned)
        if len(fallback) >= 8:
            break
    return _dedupe(fallback)[:8]


def _extract_requirement_lines(lines: list[str]) -> list[str]:
    return _extract_list_lines(_collect_section_lines(lines, REQUIREMENT_HEADINGS))


def _extract_benefits(lines: list[str]) -> list[str]:
    items = _extract_list_lines(_collect_section_lines(lines, BENEFIT_HEADINGS))
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
    return _dedupe(fallback)[:6]


def _extract_preferred_skills(lines: list[str]) -> list[str]:
    preferred_skills: list[str] = []
    for line in lines:
        lowered = line.lower()
        if not any(marker in lowered for marker in PREFERRED_MARKERS):
            continue
        for skill in SKILL_KEYWORDS:
            if skill.lower() in lowered and skill not in preferred_skills:
                preferred_skills.append(skill)
    return preferred_skills


def _extract_preferred_lines(requirement_lines: list[str]) -> list[str]:
    return [
        line
        for line in requirement_lines
        if any(marker in line.lower() for marker in PREFERRED_MARKERS)
    ]


def _extract_required_lines(requirement_lines: list[str]) -> list[str]:
    return [
        line
        for line in requirement_lines
        if not any(marker in line.lower() for marker in PREFERRED_MARKERS)
    ]


def _extract_company(raw_text: str) -> str | None:
    for pattern in COMPANY_PATTERNS:
        match = pattern.search(raw_text)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _extract_city(raw_text: str) -> str | None:
    lowered = raw_text.lower()
    for item in CITY_KEYWORDS:
        if item.lower() in lowered:
            return item
    return None


def _extract_employment_type(raw_text: str) -> str | None:
    lowered = raw_text.lower()
    for item in EMPLOYMENT_TYPE_KEYWORDS:
        if item.lower() in lowered:
            return item
    return None


def _build_summary(title: str, required_skills: list[str], responsibilities: list[str]) -> str:
    summary_parts = [title]
    if required_skills:
        summary_parts.append(f"核心技能：{', '.join(required_skills[:4])}")
    if responsibilities:
        summary_parts.append(f"重点职责：{responsibilities[0]}")
    return "；".join(part for part in summary_parts if part)


def _build_responsibility_clusters(responsibilities: list[str]) -> list[dict[str, object]]:
    clusters: list[dict[str, object]] = []

    mapping = [
        ("分析与洞察", ("分析", "指标", "实验", "建模", "复盘")),
        ("协作与推进", ("协作", "推进", "对接", "沟通", "项目")),
        ("建设与交付", ("建设", "搭建", "优化", "负责", "支持", "开发")),
    ]
    for label, keywords in mapping:
        items = [item for item in responsibilities if any(keyword in item for keyword in keywords)]
        if items:
            clusters.append({"name": label, "items": items[:3]})

    if clusters:
        return clusters
    if responsibilities:
        return [{"name": "核心职责", "items": responsibilities[:4]}]
    return []


def _detect_seniority_hint(title: str, experience_years: int | None) -> str | None:
    lowered = title.lower()
    if any(token in lowered for token in ("高级", "senior", "资深")):
        return "senior"
    if any(token in lowered for token in ("专家", "lead", "负责人")):
        return "lead"
    if experience_years and experience_years >= 5:
        return "senior"
    if experience_years and experience_years >= 3:
        return "mid"
    return "junior" if experience_years is not None else None


def _build_domain_keywords(
    *,
    title: str,
    joined_text: str,
    responsibilities: list[str],
    requirement_lines: list[str],
) -> list[str]:
    keywords = _extract_keywords(joined_text, KEYWORD_PHRASES)
    title_and_requirements = " ".join([title, *responsibilities, *requirement_lines])
    for phrase in DOMAIN_LEXICON:
        if phrase.lower() in title_and_requirements.lower():
            keywords.append(phrase)
    return _dedupe(keywords)[:10]


def _build_must_have(
    *,
    required_skills: list[str],
    required_keywords: list[str],
    required_lines: list[str],
    experience_years: int | None,
    education: str | None,
) -> list[str]:
    items = [*required_skills, *required_keywords]
    if education:
        items.append(education)
    if experience_years:
        items.append(f"{experience_years}年以上经验")
    items.extend(required_lines[:6])
    return _dedupe(items)[:10]


def _build_nice_to_have(
    *,
    preferred_skills: list[str],
    preferred_lines: list[str],
) -> list[str]:
    return _dedupe([*preferred_skills, *preferred_lines])[:8]


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

    requirement_lines = _extract_requirement_lines(lines)
    preferred_lines = _extract_preferred_lines(requirement_lines)
    required_lines = _extract_required_lines(requirement_lines)
    preferred_skills = _extract_preferred_skills(lines)
    all_skills = _extract_keywords(joined, SKILL_KEYWORDS)
    required_skills = [skill for skill in all_skills if skill not in preferred_skills]
    responsibilities = _extract_responsibilities(lines)
    benefits = _extract_benefits(lines)
    experience_years = _extract_experience_years(joined)
    education = _extract_education(joined)
    required_keywords = _build_domain_keywords(
        title=title,
        joined_text=joined,
        responsibilities=responsibilities,
        requirement_lines=requirement_lines,
    )
    detected_company = company or _extract_company(jd_text)
    detected_city = job_city or _extract_city(jd_text)
    detected_employment_type = employment_type or _extract_employment_type(jd_text)

    return JobStructuredData(
        basic={
            "title": title,
            "company": detected_company,
            "job_city": detected_city,
            "employment_type": detected_employment_type,
        },
        must_have=_build_must_have(
            required_skills=required_skills,
            required_keywords=required_keywords,
            required_lines=required_lines,
            experience_years=experience_years,
            education=education,
        ),
        nice_to_have=_build_nice_to_have(
            preferred_skills=preferred_skills,
            preferred_lines=preferred_lines,
        ),
        responsibility_clusters=_build_responsibility_clusters(responsibilities),
        experience_constraints={
            "education": education,
            "experience_min_years": experience_years,
            "location": detected_city,
            "employment_type": detected_employment_type,
        },
        domain_context={
            "keywords": required_keywords,
            "seniority_hint": _detect_seniority_hint(title, experience_years),
            "summary": _build_summary(title, required_skills, responsibilities),
            "benefits": benefits,
        },
        requirements={
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "required_keywords": required_keywords,
            "education": education,
            "experience_min_years": experience_years,
        },
        responsibilities=responsibilities,
        benefits=benefits,
        raw_summary=_build_summary(title, required_skills, responsibilities),
    )
