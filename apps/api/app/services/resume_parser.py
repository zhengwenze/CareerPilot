from __future__ import annotations

import re
import unicodedata
from io import BytesIO

from pypdf import PdfReader

from app.core.errors import ApiException, ErrorCode
from app.schemas.resume import ResumeStructuredData

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s-]{7,}\d)")
CJK_SPACING_PATTERN = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")
SECTION_BREAK_PATTERN = re.compile(r"\s{2,}|[|｜]")
BULLET_PREFIX = re.compile(r"^(?:[-*•·●▪■◆]|[0-9]+[.)、])\s*")
DATE_SPAN_PATTERN = re.compile(
    r"(?:20\d{2}|19\d{2})\s*[./-]\s*(?:20\d{2}|19\d{2}|至今|present)",
    re.IGNORECASE,
)

SECTION_PATTERNS = {
    "education": [
        "教育",
        "教育经历",
        "教育背景",
        "education",
    ],
    "work_experience": [
        "工作经历",
        "实习经历",
        "experience",
        "professional experience",
    ],
    "projects": [
        "项目经历",
        "项目经验",
        "项目背景",
        "projects",
        "project experience",
    ],
    "skills": [
        "技能",
        "专业技能",
        "skills",
        "skill",
        "tech stack",
    ],
    "certifications": [
        "证书",
        "证书奖项",
        "certifications",
        "awards",
    ],
}

TECHNICAL_KEYWORDS = [
    "A/B Testing",
    "Airflow",
    "C++",
    "Django",
    "Docker",
    "Excel",
    "FastAPI",
    "Flask",
    "Git",
    "Hadoop",
    "Java",
    "Python",
    "JavaScript",
    "Kubernetes",
    "Looker",
    "Machine Learning",
    "MySQL",
    "Next.js",
    "NextJS",
    "NumPy",
    "Pandas",
    "Power BI",
    "PostgreSQL",
    "PyTorch",
    "React",
    "Redis",
    "scikit-learn",
    "Spark",
    "SQL",
    "Tableau",
    "TensorFlow",
    "TypeScript",
    "Vue",
    "数据分析",
    "数据建模",
    "实验分析",
    "指标体系",
    "用户增长",
]
TOOL_KEYWORDS = [
    "Docker",
    "Figma",
    "Git",
    "Jira",
    "Linux",
    "MATLAB",
    "Notion",
    "Photoshop",
    "Postman",
    "PRD",
    "SPSS",
    "Visio",
    "Xmind",
]
LANGUAGE_KEYWORDS = [
    "英语",
    "英文",
    "法语",
    "日语",
    "韩语",
    "粤语",
    "普通话",
    "English",
    "French",
    "Japanese",
    "Korean",
]
LOCATION_KEYWORDS = [
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "成都",
    "武汉",
    "苏州",
    "南京",
    "remote",
]
EDUCATION_HINTS = (
    "大学",
    "学院",
    "university",
    "college",
    "school",
    "本科",
    "硕士",
    "博士",
    "学历",
    "专业",
    "gpa",
)
WORK_HINTS = (
    "有限公司",
    "公司",
    "实习",
    "工程师",
    "经理",
    "分析师",
    "产品",
    "运营",
    "研发",
    "负责",
    "intern",
)
PROJECT_HINTS = (
    "项目",
    "平台",
    "系统",
    "课题",
    "project",
    "负责开发",
    "上线",
    "搭建",
    "重构",
)
SKILL_HINTS = (
    "技能",
    "熟悉",
    "掌握",
    "技术栈",
    "skill",
    "stack",
    "tool",
    "工具",
)
CERTIFICATION_HINTS = (
    "证书",
    "证照",
    "certification",
    "award",
    "奖学金",
    "cfa",
    "pmp",
    "cpa",
    "cet",
)


def extract_text_from_pdf_bytes(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Failed to read PDF file",
            details={"reason": str(exc)},
        ) from exc

    pages: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        cleaned = _normalize_text(extracted)
        if cleaned:
            pages.append(cleaned)

    raw_text = "\n\n".join(pages).strip()
    if not raw_text:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="No extractable text found in PDF. Scanned PDFs are not supported yet.",
        )
    return raw_text


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\u3000", " ").replace("\r", "\n")
    normalized = CJK_SPACING_PATTERN.sub("", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()


def _normalize_lines(raw_text: str) -> list[str]:
    lines: list[str] = []
    for block in raw_text.splitlines():
        normalized = _normalize_text(block)
        if not normalized:
            continue
        parts = [item.strip() for item in SECTION_BREAK_PATTERN.split(normalized) if item.strip()]
        lines.extend(parts or [normalized])
    return lines


def _find_first_match(pattern: re.Pattern[str], lines: list[str], raw_text: str) -> str:
    for chunk in [*lines, raw_text]:
        match = pattern.search(chunk)
        if match:
            return match.group(0).strip().replace(" ", "")
    return ""


def _detect_location(lines: list[str]) -> str:
    joined = " ".join(lines).lower()
    for keyword in LOCATION_KEYWORDS:
        if keyword.lower() in joined:
            return keyword
    return ""


def _guess_name(lines: list[str]) -> str:
    for line in lines[:5]:
        lowered = line.lower()
        if EMAIL_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue
        if _match_section(line) is not None:
            continue
        if _looks_like_education_line(line) or _looks_like_work_line(line) or _looks_like_project_line(line):
            continue
        if any(keyword.lower() in lowered for keyword in LOCATION_KEYWORDS):
            continue
        if len(line) <= 24 and len(line.split()) <= 4:
            return line
    return ""


def _guess_summary(lines: list[str]) -> str:
    summary_lines: list[str] = []
    for line in lines[1:8]:
        if _match_section(line) is not None:
            break
        if EMAIL_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue
        if _looks_like_education_line(line) or _looks_like_work_line(line) or _looks_like_project_line(line):
            continue
        summary_lines.append(line)
    return " ".join(summary_lines[:3]).strip()


def _match_section(line: str) -> str | None:
    normalized = BULLET_PREFIX.sub("", line.strip()).lower().rstrip(":：")
    for section, headings in SECTION_PATTERNS.items():
        for heading in sorted(headings, key=len, reverse=True):
            if normalized == heading:
                return section
            if normalized.startswith(f"{heading}:") or normalized.startswith(f"{heading}："):
                return section
            if normalized.startswith(f"{heading} "):
                return section
    return None


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections = {
        "education": [],
        "work_experience": [],
        "projects": [],
        "skills": [],
        "certifications": [],
    }
    current_section: str | None = None

    for line in lines:
        matched = _match_section(line)
        if matched is not None:
            current_section = matched
            remainder = _strip_section_heading(line, matched)
            if remainder:
                sections[current_section].append(remainder)
            continue
        if current_section is not None:
            sections[current_section].append(_clean_list_line(line))

    return sections


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
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


def _clean_list_line(line: str) -> str:
    return BULLET_PREFIX.sub("", line).strip()


def _strip_section_heading(line: str, section: str) -> str:
    normalized = _clean_list_line(line)
    for heading in sorted(SECTION_PATTERNS[section], key=len, reverse=True):
        pattern = re.compile(rf"^{re.escape(heading)}(?:\s*[:：]\s*|\s+)?", re.IGNORECASE)
        if pattern.match(normalized):
            return pattern.sub("", normalized, count=1).strip()
    return ""


def _extract_keyword_tags(lines: list[str], raw_text: str, keywords: list[str]) -> list[str]:
    joined = " ".join(lines).lower()
    haystack = f"{joined} {raw_text.lower()}"
    found: list[str] = []
    for keyword in keywords:
        if keyword.lower() in haystack:
            found.append(keyword)
    return _dedupe_preserve_order(found)


def _looks_like_education_line(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in EDUCATION_HINTS)


def _looks_like_work_line(line: str) -> bool:
    lowered = line.lower()
    return bool(DATE_SPAN_PATTERN.search(lowered)) or any(token in lowered for token in WORK_HINTS)


def _looks_like_project_line(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in PROJECT_HINTS)


def _looks_like_skill_line(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in SKILL_HINTS)


def _looks_like_certification_line(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in CERTIFICATION_HINTS)


def _fallback_section_lines(
    *,
    lines: list[str],
    predicate,
    limit: int,
) -> list[str]:
    matches = [
        _clean_list_line(line)
        for line in lines
        if line and _match_section(line) is None and predicate(line)
    ]
    return _dedupe_preserve_order(matches[:limit])


def _has_meaningful_content(structured: ResumeStructuredData) -> bool:
    basic = structured.basic_info
    return any(
        [
            basic.name,
            basic.email,
            basic.phone,
            basic.location,
            basic.summary,
            structured.education,
            structured.work_experience,
            structured.projects,
            structured.skills.technical,
            structured.skills.tools,
            structured.skills.languages,
            structured.certifications,
        ]
    )


def build_structured_resume(raw_text: str) -> ResumeStructuredData:
    lines = _normalize_lines(raw_text)
    sections = _split_sections(lines)
    education = _dedupe_preserve_order(sections["education"])
    work_experience = _dedupe_preserve_order(sections["work_experience"])
    projects = _dedupe_preserve_order(sections["projects"])
    certifications = _dedupe_preserve_order(sections["certifications"])

    if not education:
        education = _fallback_section_lines(
            lines=lines,
            predicate=_looks_like_education_line,
            limit=4,
        )

    if not work_experience:
        work_experience = _fallback_section_lines(
            lines=lines,
            predicate=_looks_like_work_line,
            limit=6,
        )

    if not projects:
        projects = _fallback_section_lines(
            lines=lines,
            predicate=_looks_like_project_line,
            limit=6,
        )

    skill_lines = _dedupe_preserve_order(
        [
            *sections["skills"],
            *_fallback_section_lines(
                lines=lines,
                predicate=_looks_like_skill_line,
                limit=6,
            ),
        ]
    )

    if not certifications:
        certifications = _fallback_section_lines(
            lines=lines,
            predicate=_looks_like_certification_line,
            limit=4,
        )

    structured = ResumeStructuredData(
        basic_info={
            "name": _guess_name(lines),
            "email": _find_first_match(EMAIL_PATTERN, lines, raw_text),
            "phone": _find_first_match(PHONE_PATTERN, lines, raw_text),
            "location": _detect_location(lines),
            "summary": _guess_summary(lines),
        },
        education=education,
        work_experience=work_experience,
        projects=projects,
        skills={
            "technical": _extract_keyword_tags(
                skill_lines,
                raw_text,
                TECHNICAL_KEYWORDS,
            ),
            "tools": _extract_keyword_tags(
                skill_lines,
                raw_text,
                TOOL_KEYWORDS,
            ),
            "languages": _extract_keyword_tags(
                skill_lines,
                raw_text,
                LANGUAGE_KEYWORDS,
            ),
        },
        certifications=certifications,
    )
    if not _has_meaningful_content(structured):
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Failed to extract structured resume fields from PDF text",
        )
    return structured
