from __future__ import annotations

import re
from typing import Callable

from .cleaner import clean_list_line, dedupe_preserve_order, normalize_lines
from .models import ParseDebugData, ParseResult, ResumeBasicInfo, ResumeSkills, ResumeStructuredData

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s-]{7,}\d)")
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
DATE_SPAN_PATTERN = re.compile(
    r"(?:(?:19|20)\d{2})(?:\s*[./-]\s*(?:0?[1-9]|1[0-2]))?\s*(?:-|~|–|—|至)\s*"
    r"(?:(?:19|20)\d{2}(?:\s*[./-]\s*(?:0?[1-9]|1[0-2]))?|至今|present|now|current)",
    re.IGNORECASE,
)
INLINE_DATE_PATTERN = re.compile(r"(?:19|20)\d{2}[./-](?:0?[1-9]|1[0-2])", re.IGNORECASE)

SECTION_PATTERNS = {
    "education": ["教育经历", "教育背景", "教育", "education", "academic background"],
    "work_experience": [
        "工作经历",
        "实习经历",
        "职业经历",
        "experience",
        "professional experience",
    ],
    "projects": ["项目经历", "项目经验", "项目背景", "projects", "project experience"],
    "skills": ["专业技能", "技能", "skills", "skill", "tech stack"],
    "certifications": ["证书奖项", "证书", "奖项", "certifications", "awards"],
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
    "GitLab CI",
    "GitHub Actions",
    "Hadoop",
    "Java",
    "JavaScript",
    "Kafka",
    "Kubernetes",
    "LangChain",
    "LangGraph",
    "Looker",
    "Machine Learning",
    "Milvus",
    "MongoDB",
    "MySQL",
    "Next.js",
    "NextJS",
    "NumPy",
    "Pandas",
    "PostgreSQL",
    "Power BI",
    "Prometheus",
    "Pinecone",
    "PyTorch",
    "Python",
    "Qwen",
    "React",
    "Redis",
    "RAG",
    "RocketMQ",
    "scikit-learn",
    "Spark",
    "Spring Boot",
    "SQL",
    "Tableau",
    "TensorFlow",
    "TypeScript",
    "Vue",
    "实验分析",
    "数据分析",
    "数据建模",
    "指标体系",
    "用户增长",
]
TOOL_KEYWORDS = [
    "Docker",
    "Figma",
    "Git",
    "GitLab CI",
    "GitHub Actions",
    "Grafana",
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
    "Nginx",
    "ELK",
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
LOCATION_KEYWORDS = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "苏州", "南京", "remote"]
INVALID_NAME_CANDIDATES = {"简历", "个人简历", "resume", "curriculum vitae", "frontend engineer"}

EDUCATION_HINTS = ("大学", "学院", "university", "college", "school", "本科", "硕士", "博士", "gpa")
WORK_HINTS = (
    "有限公司",
    "公司",
    "科技",
    "集团",
    "实习",
    "实习生",
    "工程师",
    "经理",
    "分析师",
    "产品",
    "运营",
    "研发",
    "intern",
)
PROJECT_HINTS = ("项目", "平台", "系统", "课题", "project", "上线", "重构")
SKILL_HINTS = ("技能", "熟悉", "掌握", "技术栈", "skill", "stack", "tool", "工具")
CERTIFICATION_HINTS = (
    "证书",
    "证照",
    "certification",
    "award",
    "奖学金",
    "获奖",
    "荣誉",
    "竞赛",
    "软件著作权",
    "专利",
    "论文",
    "科研成果",
    "cfa",
    "pmp",
    "cpa",
    "cet",
)
ACTION_HINTS = ("负责", "主导", "参与", "实现", "优化", "搭建", "协同", "推动", "完成", "设计", "落地")
PROFILE_METADATA_PREFIXES = (
    "电话",
    "手机",
    "邮箱",
    "当前状态",
    "求职岗位",
    "到岗时间",
    "所在城市",
    "实习时间",
    "期望薪资",
    "期望岗位",
    "求职意向",
    "出生年月",
    "年龄",
    "性别",
    "政治面貌",
)
PROJECT_CONTINUATION_PREFIXES = (
    "技术栈",
    "项目成果",
    "项目描述",
    "核心功能",
    "核心功能落地与优化",
    "工程化交付与扩展",
    "技术整合与创新",
    "项目亮点",
)
SUPPLEMENTARY_CREDENTIAL_PREFIXES = (
    "竞赛获奖",
    "获奖情况",
    "荣誉奖项",
    "科研成果",
    "论文成果",
    "软件著作权",
    "专利",
)


def parse_resume_text(raw_text: str) -> ParseResult:
    lines = normalize_lines(raw_text)
    sections = _split_sections(lines)
    education_lines, supplementary_credential_lines = _split_education_supporting_lines(
        sections["education"]
    )

    education = _assemble_items("education", education_lines)
    work_experience = _assemble_items("work_experience", sections["work_experience"])
    projects = _assemble_items("projects", sections["projects"])
    certifications = _assemble_items(
        "certifications",
        [*sections["certifications"], *supplementary_credential_lines],
    )

    if not education:
        education = _fallback_section_lines(lines=lines, predicate=_looks_like_education_line, limit=4)
    if not work_experience:
        work_experience = _fallback_section_lines(
            lines=lines,
            predicate=_looks_like_work_experience_fallback_line,
            limit=6,
        )
    if not projects:
        projects = _fallback_section_lines(lines=lines, predicate=_looks_like_project_line, limit=6)
    if not certifications:
        certifications = _fallback_section_lines(
            lines=lines, predicate=_looks_like_certification_line, limit=4
        )

    skill_lines = dedupe_preserve_order(
        [
            *sections["skills"],
            *_fallback_section_lines(lines=lines, predicate=_looks_like_skill_line, limit=6),
        ]
    )

    basic_info, confidence = _build_basic_info(lines, raw_text)
    structured_data = ResumeStructuredData(
        basic_info=basic_info,
        education=education,
        work_experience=work_experience,
        projects=projects,
        skills=ResumeSkills(
            technical=_extract_keyword_tags(skill_lines, raw_text, TECHNICAL_KEYWORDS),
            tools=_extract_keyword_tags(skill_lines, raw_text, TOOL_KEYWORDS),
            languages=_extract_keyword_tags(skill_lines, raw_text, LANGUAGE_KEYWORDS),
        ),
        certifications=certifications,
    )

    debug = ParseDebugData(
        cleaned_lines=lines,
        sections={
            "education": education,
            "work_experience": work_experience,
            "projects": projects,
            "skills": skill_lines,
            "certifications": certifications,
        },
        field_confidence=confidence,
    )
    return ParseResult(structured_data=structured_data, raw_text=raw_text, debug=debug)


def _build_basic_info(lines: list[str], raw_text: str) -> tuple[ResumeBasicInfo, dict[str, float]]:
    email = _find_first_match(EMAIL_PATTERN, lines, raw_text, strip_spaces=True)
    phone = _find_first_match(PHONE_PATTERN, lines, raw_text, strip_spaces=True)
    location = _detect_location(lines)
    name = _guess_name(lines)
    summary = _guess_summary(lines)

    return (
        ResumeBasicInfo(
            name=name,
            email=email,
            phone=phone,
            location=location,
            summary=summary,
        ),
        {
            "name": 0.85 if name else 0.0,
            "email": 0.99 if email else 0.0,
            "phone": 0.95 if phone else 0.0,
            "location": 0.7 if location else 0.0,
            "summary": 0.65 if summary else 0.0,
        },
    )


def _find_first_match(
    pattern: re.Pattern[str],
    lines: list[str],
    raw_text: str,
    *,
    strip_spaces: bool = False,
) -> str:
    for chunk in [*lines, raw_text]:
        match = pattern.search(chunk)
        if match:
            value = match.group(0).strip()
            return value.replace(" ", "") if strip_spaces else value
    return ""


def _detect_location(lines: list[str]) -> str:
    joined = " ".join(lines).casefold()
    for keyword in LOCATION_KEYWORDS:
        if keyword.casefold() in joined:
            return keyword
    return ""


def _guess_name(lines: list[str]) -> str:
    for line in lines[:5]:
        lowered = line.casefold()
        if lowered in INVALID_NAME_CANDIDATES:
            continue
        if EMAIL_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue
        if _match_section(line) is not None:
            continue
        if _looks_like_education_line(line) or _looks_like_work_line(line) or _looks_like_project_line(line):
            continue
        if any(keyword.casefold() in lowered for keyword in LOCATION_KEYWORDS):
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
        if _looks_like_profile_metadata_line(line):
            continue
        if _looks_like_education_line(line) or _looks_like_work_line(line) or _looks_like_project_line(line):
            continue
        summary_lines.append(line)
    return " ".join(summary_lines[:3]).strip()


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
            sections[current_section].append(clean_list_line(line))

    return sections


def _assemble_items(section: str, lines: list[str]) -> list[str]:
    items: list[str] = []
    current: list[str] = []

    for raw_line in lines:
        line = clean_list_line(raw_line)
        if not line:
            continue
        if current and _is_new_item_start(section, line):
            items.append(" ".join(current).strip())
            current = [line]
            continue
        current.append(line)

    if current:
        items.append(" ".join(current).strip())
    return dedupe_preserve_order(items)


def _is_new_item_start(section: str, line: str) -> bool:
    if section == "projects" and _looks_like_project_continuation_line(line):
        return False
    if section == "certifications":
        return _looks_like_supplementary_credential_line(line)

    if DATE_SPAN_PATTERN.search(line) or INLINE_DATE_PATTERN.search(line):
        return True

    if section == "education":
        return _is_title_like(line) and _looks_like_education_line(line)
    if section == "work_experience":
        return _is_title_like(line) and _looks_like_work_anchor(line)
    if section == "projects":
        return _looks_like_project_anchor(line)
    return True


def _is_title_like(line: str) -> bool:
    return (
        len(line) <= 40
        and "。" not in line
        and "；" not in line
        and ";" not in line
        and not any(token in line for token in ACTION_HINTS)
    )


def _looks_like_education_line(line: str) -> bool:
    lowered = line.casefold()
    return any(token in lowered for token in EDUCATION_HINTS)


def _looks_like_work_line(line: str) -> bool:
    lowered = line.casefold()
    if _looks_like_profile_metadata_line(line) or _looks_like_education_line(line):
        return False
    return bool(DATE_SPAN_PATTERN.search(lowered)) or any(token in lowered for token in WORK_HINTS)


def _looks_like_project_line(line: str) -> bool:
    lowered = line.casefold()
    return any(token in lowered for token in PROJECT_HINTS)


def _looks_like_skill_line(line: str) -> bool:
    lowered = line.casefold()
    return any(token in lowered for token in SKILL_HINTS)


def _looks_like_certification_line(line: str) -> bool:
    lowered = line.casefold()
    return any(token in lowered for token in CERTIFICATION_HINTS)


def _looks_like_work_experience_fallback_line(line: str) -> bool:
    lowered = line.casefold()
    if _looks_like_profile_metadata_line(line) or _looks_like_education_line(line):
        return False
    has_work_hint = any(token in lowered for token in WORK_HINTS)
    has_date = bool(DATE_SPAN_PATTERN.search(line) or INLINE_DATE_PATTERN.search(line))
    return has_date and has_work_hint


def _looks_like_work_anchor(line: str) -> bool:
    lowered = line.casefold()
    if any(token in line for token in ACTION_HINTS):
        return False
    return any(token in lowered for token in WORK_HINTS) or "@" in line


def _looks_like_project_anchor(line: str) -> bool:
    if _looks_like_project_continuation_line(line):
        return False
    if "。" in line or "；" in line or ";" in line:
        return False
    if any(token in line for token in ACTION_HINTS):
        return False
    if URL_PATTERN.search(line) is not None:
        return True
    return _is_title_like(line) and (
        _looks_like_project_line(line) or (len(line) <= 36 and len(line.split()) <= 10)
    )


def _looks_like_project_continuation_line(line: str) -> bool:
    return _starts_with_any_prefix(line, PROJECT_CONTINUATION_PREFIXES)


def _looks_like_profile_metadata_line(line: str) -> bool:
    return _starts_with_any_prefix(line, PROFILE_METADATA_PREFIXES)


def _looks_like_supplementary_credential_line(line: str) -> bool:
    return _starts_with_any_prefix(line, SUPPLEMENTARY_CREDENTIAL_PREFIXES)


def _fallback_section_lines(
    *,
    lines: list[str],
    predicate: Callable[[str], bool],
    limit: int,
) -> list[str]:
    matches = [
        clean_list_line(line)
        for line in lines
        if line and _match_section(line) is None and predicate(line)
    ]
    return dedupe_preserve_order(matches[:limit])


def _extract_keyword_tags(lines: list[str], raw_text: str, keywords: list[str]) -> list[str]:
    joined = " ".join(lines).casefold()
    haystack = f"{joined} {raw_text.casefold()}"
    found: list[str] = []
    for keyword in keywords:
        if keyword.casefold() in haystack:
            found.append(keyword)
    return dedupe_preserve_order(found)


def _match_section(line: str) -> str | None:
    normalized = clean_list_line(line).strip()
    for section, headings in SECTION_PATTERNS.items():
        for heading in headings:
            if _section_heading_pattern(heading).match(normalized):
                return section
    return None


def _strip_section_heading(line: str, section: str) -> str:
    normalized = clean_list_line(line)
    for heading in SECTION_PATTERNS[section]:
        match = _section_heading_pattern(heading).match(normalized)
        if match:
            return normalized[match.end() :].strip()
    return ""


def _section_heading_pattern(heading: str) -> re.Pattern[str]:
    if any("\u4e00" <= char <= "\u9fff" for char in heading):
        body = r"\s*".join(re.escape(char) for char in heading)
    else:
        body = r"\s+".join(re.escape(part) for part in heading.split())
    return re.compile(rf"^{body}(?:\s*[:：]\s*|\s+|$)", re.IGNORECASE)


def _split_education_supporting_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    education_lines: list[str] = []
    supplementary_lines: list[str] = []
    in_supplementary_block = False

    for line in lines:
        if _looks_like_supplementary_credential_line(line):
            in_supplementary_block = True
            supplementary_lines.append(line)
            continue
        if in_supplementary_block:
            supplementary_lines.append(line)
            continue
        education_lines.append(line)
    return education_lines, supplementary_lines


def _starts_with_any_prefix(line: str, prefixes: tuple[str, ...]) -> bool:
    normalized = clean_list_line(line).casefold()
    for prefix in prefixes:
        prefix_normalized = prefix.casefold()
        if normalized == prefix_normalized:
            return True
        if normalized.startswith(f"{prefix_normalized}:") or normalized.startswith(
            f"{prefix_normalized}："
        ):
            return True
    return False
