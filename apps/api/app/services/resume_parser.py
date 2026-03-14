from __future__ import annotations

import re
import unicodedata
from io import BytesIO

from pypdf import PdfReader

from app.core.errors import ApiException, ErrorCode
from app.schemas.resume import ResumeStructuredData

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s-]{7,}\d)")

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
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "React",
    "Vue",
    "Next.js",
    "NextJS",
    "FastAPI",
    "Django",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "Redis",
    "Excel",
    "Power BI",
    "Tableau",
]
TOOL_KEYWORDS = [
    "Git",
    "Docker",
    "Figma",
    "Postman",
    "Jira",
    "Linux",
    "Photoshop",
]
LANGUAGE_KEYWORDS = [
    "英语",
    "英文",
    "日语",
    "韩语",
    "English",
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
    normalized = normalized.replace("\u3000", " ")
    return normalized.strip()


def _normalize_lines(raw_text: str) -> list[str]:
    return [
        _normalize_text(line)
        for line in raw_text.splitlines()
        if _normalize_text(line)
    ]


def _find_first_match(pattern: re.Pattern[str], lines: list[str]) -> str:
    for line in lines:
        match = pattern.search(line)
        if match:
            return match.group(0).strip()
    return ""


def _detect_location(lines: list[str]) -> str:
    joined = " ".join(lines).lower()
    for keyword in LOCATION_KEYWORDS:
        if keyword.lower() in joined:
            return keyword
    return ""


def _guess_name(lines: list[str]) -> str:
    for line in lines[:5]:
        if EMAIL_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue
        if len(line) <= 32:
            return line
    return ""


def _guess_summary(lines: list[str]) -> str:
    summary_lines: list[str] = []
    for line in lines[1:8]:
        normalized = line.lower()
        if any(
            heading in normalized
            for headings in SECTION_PATTERNS.values()
            for heading in headings
        ):
            break
        if EMAIL_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue
        summary_lines.append(line)
    return " ".join(summary_lines[:3]).strip()


def _match_section(line: str) -> str | None:
    normalized = line.strip().lower().rstrip(":：")
    for section, headings in SECTION_PATTERNS.items():
        if normalized in headings:
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
            continue
        if current_section is not None:
            sections[current_section].append(line)

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


def _extract_keyword_tags(lines: list[str], raw_text: str, keywords: list[str]) -> list[str]:
    joined = " ".join(lines).lower()
    haystack = f"{joined} {raw_text.lower()}"
    found: list[str] = []
    for keyword in keywords:
        if keyword.lower() in haystack:
            found.append(keyword)
    return _dedupe_preserve_order(found)


def build_structured_resume(raw_text: str) -> ResumeStructuredData:
    lines = _normalize_lines(raw_text)
    sections = _split_sections(lines)

    return ResumeStructuredData(
        basic_info={
            "name": _guess_name(lines),
            "email": _find_first_match(EMAIL_PATTERN, lines),
            "phone": _find_first_match(PHONE_PATTERN, lines),
            "location": _detect_location(lines),
            "summary": _guess_summary(lines),
        },
        education=_dedupe_preserve_order(sections["education"]),
        work_experience=_dedupe_preserve_order(sections["work_experience"]),
        projects=_dedupe_preserve_order(sections["projects"]),
        skills={
            "technical": _extract_keyword_tags(
                sections["skills"],
                raw_text,
                TECHNICAL_KEYWORDS,
            ),
            "tools": _extract_keyword_tags(
                sections["skills"],
                raw_text,
                TOOL_KEYWORDS,
            ),
            "languages": _extract_keyword_tags(
                sections["skills"],
                raw_text,
                LANGUAGE_KEYWORDS,
            ),
        },
        certifications=_dedupe_preserve_order(sections["certifications"]),
    )
