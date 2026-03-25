from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.resume import (
    ResumeBasicInfo,
    ResumeCertificationItem,
    ResumeCustomSection,
    ResumeCustomSectionItem,
    ResumeEducationItem,
    ResumeExperienceBullet,
    ResumeMeta,
    ResumeProjectItem,
    ResumeSkills,
    ResumeStructuredData,
    ResumeWorkExperienceItem,
)

CONTACT_LINE_SPLIT = re.compile(r"\s+\|\s+")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s-]{6,}\d)")
SECTION_TITLE_MAP = {
    "个人简介": "summary",
    "summary": "summary",
    "专业技能": "skills",
    "技能": "skills",
    "skills": "skills",
    "工作经历": "experience",
    "work experience": "experience",
    "experience": "experience",
    "项目经历": "projects",
    "projects": "projects",
    "教育经历": "education",
    "教育背景": "education",
    "education": "education",
    "证书": "certificates",
    "certificates": "certificates",
    "奖项": "awards",
    "awards": "awards",
    "语言能力": "languages",
    "语言": "languages",
    "languages": "languages",
    "个人优势": "custom",
}
SKILL_LABEL_TO_GROUP = {
    "编程语言": "languages",
    "语言": "languages",
    "开发语言": "languages",
    "语言能力": "languages",
    "工具": "tools",
    "开发工具": "tools",
}


@dataclass(slots=True)
class MarkdownSubsection:
    heading: str
    lines: list[str]


@dataclass(slots=True)
class MarkdownSection:
    title: str
    key: str
    lines: list[str]
    subsections: list[MarkdownSubsection]


def parse_resume_markdown(markdown: str) -> ResumeStructuredData:
    normalized = markdown.replace("\r\n", "\n").strip()
    if not normalized:
        raise ValueError("Resume markdown cannot be empty")

    lines = [line.rstrip() for line in normalized.split("\n")]
    name, intro_lines, section_lines = _split_resume_markdown(lines)
    sections = _parse_sections(section_lines)

    basic_info = _parse_basic_info(name=name, intro_lines=intro_lines)
    summary = _parse_summary(sections)
    if summary:
        basic_info.summary = summary

    education_items = _parse_education_items(sections)
    work_items = _parse_work_experience_items(sections)
    project_items = _parse_project_items(sections)
    skills = _parse_skills(sections)
    certification_items = _parse_certification_items(sections)
    awards = _parse_simple_list_section(sections, "awards")
    languages = _parse_simple_list_section(sections, "languages")
    if languages:
        skills.languages = _dedupe_strings([*skills.languages, *languages])
    custom_sections = _parse_custom_sections(sections)

    structured = ResumeStructuredData(
        meta=ResumeMeta(source_type="markdown", parser_version="resume-markdown-parser-v1"),
        basic_info=basic_info,
        education_items=education_items,
        work_experience_items=work_items,
        project_items=project_items,
        skills=skills,
        certification_items=certification_items,
        awards=awards,
        custom_sections=custom_sections,
    )

    if not _has_resume_signal(structured):
        raise ValueError(
            "Markdown 缺少可识别的简历结构，至少需要姓名和一个有效 section（如工作经历、项目经历、教育经历或专业技能）。"
        )
    return structured


def _split_resume_markdown(lines: list[str]) -> tuple[str, list[str], list[str]]:
    name = ""
    intro_lines: list[str] = []
    section_start = len(lines)
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# ") and not name:
            name = line.removeprefix("# ").strip()
            continue
        if line.startswith("## "):
            section_start = index
            break
        intro_lines.append(line)
    return name, intro_lines, lines[section_start:]


def _parse_sections(lines: list[str]) -> list[MarkdownSection]:
    sections: list[MarkdownSection] = []
    current: MarkdownSection | None = None
    current_subsection: MarkdownSubsection | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("## "):
            title = line.removeprefix("## ").strip()
            current = MarkdownSection(
                title=title,
                key=SECTION_TITLE_MAP.get(title.lower(), "custom"),
                lines=[],
                subsections=[],
            )
            sections.append(current)
            current_subsection = None
            continue
        if current is None:
            continue
        if line.startswith("### "):
            current_subsection = MarkdownSubsection(
                heading=line.removeprefix("### ").strip(),
                lines=[],
            )
            current.subsections.append(current_subsection)
            continue
        current.lines.append(line)
        if current_subsection is not None:
            current_subsection.lines.append(line)
    return sections


def _parse_basic_info(*, name: str, intro_lines: list[str]) -> ResumeBasicInfo:
    basic = ResumeBasicInfo(name=name)
    for line in intro_lines:
        if line.startswith("- "):
            _apply_header_bullet(basic, line.removeprefix("- ").strip())
            continue
        for token in CONTACT_LINE_SPLIT.split(line):
            _apply_contact_token(basic, token)
    return basic


def _apply_header_bullet(basic: ResumeBasicInfo, bullet: str) -> None:
    for prefix, field_name in (
        ("邮箱：", "email"),
        ("电话：", "phone"),
        ("手机号：", "phone"),
        ("手机：", "phone"),
        ("所在地：", "location"),
        ("链接：", "links"),
        ("求职方向：", "summary"),
        ("状态：", "status"),
    ):
        if bullet.startswith(prefix):
            value = bullet.removeprefix(prefix).strip()
            if field_name == "links":
                basic.links = _dedupe_strings([*basic.links, value])
            else:
                setattr(basic, field_name, value)
            return
    _apply_contact_token(basic, bullet)


def _apply_contact_token(basic: ResumeBasicInfo, token: str) -> None:
    value = token.strip().strip("-").strip()
    if not value:
        return
    if "：" in value:
        label, rest = value.split("：", 1)
        normalized_label = label.strip()
        normalized_value = rest.strip()
        if normalized_label in {"邮箱", "Email"}:
            basic.email = normalized_value
            return
        if normalized_label in {"电话", "手机"}:
            basic.phone = normalized_value
            return
        if normalized_label in {"所在地", "城市"}:
            basic.location = normalized_value
            return
        if normalized_label in {"求职方向", "摘要", "目标岗位"} and not basic.summary:
            basic.summary = normalized_value
            return
        if normalized_label in {"链接", "仓库", "主页"}:
            basic.links = _dedupe_strings([*basic.links, normalized_value])
            return
    if EMAIL_RE.search(value):
        basic.email = EMAIL_RE.search(value).group(0)
        return
    if value.startswith("http://") or value.startswith("https://"):
        basic.links = _dedupe_strings([*basic.links, value])
        return
    phone_match = PHONE_RE.search(value)
    if phone_match:
        basic.phone = phone_match.group(0).strip()
        return
    if not basic.location and len(value) <= 20:
        basic.location = value


def _parse_summary(sections: list[MarkdownSection]) -> str:
    section = _get_section(sections, "summary")
    if section is None:
        return ""
    lines = [line for line in section.lines if line and not line.startswith("### ")]
    return "\n".join(lines).strip()


def _parse_education_items(sections: list[MarkdownSection]) -> list[ResumeEducationItem]:
    section = _get_section(sections, "education")
    if section is None:
        return []
    items: list[ResumeEducationItem] = []
    if section.subsections:
        for index, subsection in enumerate(section.subsections, start=1):
            school, major = _split_header_pair(subsection.heading)
            degree = ""
            start_date = ""
            end_date = ""
            gpa = ""
            honors: list[str] = []
            for line in subsection.lines:
                if not line:
                    continue
                if line.startswith("- "):
                    content = _strip_bullet_prefix(line)
                    if content.upper().startswith("GPA"):
                        gpa = content.removeprefix("GPA").lstrip("：: ").strip()
                    elif not degree and content in {"本科", "硕士", "博士", "大专"}:
                        degree = content
                    else:
                        honors.extend(_split_multi_value(content))
                    continue
                degree_candidate, start_date, end_date, gpa_candidate = _parse_education_meta_line(line)
                if degree_candidate and not degree:
                    degree = degree_candidate
                if gpa_candidate and not gpa:
                    gpa = gpa_candidate
            items.append(
                ResumeEducationItem(
                    id=f"edu_{index}",
                    school=school or subsection.heading,
                    major=major,
                    degree=degree,
                    start_date=start_date,
                    end_date=end_date,
                    gpa=gpa,
                    honors=_dedupe_strings(honors),
                    source_refs=[f"edu_{index}"],
                )
            )
    else:
        values = _parse_simple_list_section(sections, "education")
        for index, value in enumerate(values, start=1):
            items.append(
                ResumeEducationItem(
                    id=f"edu_{index}",
                    school=value,
                    source_refs=[f"edu_{index}"],
                )
            )
    return items


def _parse_work_experience_items(sections: list[MarkdownSection]) -> list[ResumeWorkExperienceItem]:
    section = _get_section(sections, "experience")
    if section is None:
        return []
    items: list[ResumeWorkExperienceItem] = []
    for index, subsection in enumerate(section.subsections, start=1):
        company, title = _split_header_pair(subsection.heading)
        start_date = ""
        end_date = ""
        bullets: list[ResumeExperienceBullet] = []
        for line in subsection.lines:
            if not line:
                continue
            if line.startswith("- "):
                bullets.append(
                    ResumeExperienceBullet(
                        id=f"work_{index}_b{len(bullets) + 1}",
                        text=_strip_bullet_prefix(line),
                        source_refs=[f"work_{index}"],
                    )
                )
                continue
            if not start_date and _looks_like_date_line(line):
                start_date, end_date = _parse_date_range(line)
                continue
        items.append(
            ResumeWorkExperienceItem(
                id=f"work_{index}",
                company=company or subsection.heading,
                title=title,
                start_date=start_date,
                end_date=end_date,
                bullets=bullets,
                source_refs=[f"work_{index}"],
            )
        )
    return items


def _parse_project_items(sections: list[MarkdownSection]) -> list[ResumeProjectItem]:
    section = _get_section(sections, "projects")
    if section is None:
        return []
    items: list[ResumeProjectItem] = []
    for index, subsection in enumerate(section.subsections, start=1):
        name, role = _split_header_pair(subsection.heading)
        link = ""
        start_date = ""
        end_date = ""
        summary = ""
        bullets: list[ResumeExperienceBullet] = []
        skills_used: list[str] = []
        for line in subsection.lines:
            if not line:
                continue
            if line.startswith("http://") or line.startswith("https://"):
                link = line.strip()
                continue
            if line.startswith("- "):
                content = _strip_bullet_prefix(line)
                if content.startswith("技术栈："):
                    skills_used.extend(_split_multi_value(content.removeprefix("技术栈：").strip()))
                elif not summary:
                    summary = content
                    bullets.append(
                        ResumeExperienceBullet(
                            id=f"proj_{index}_b{len(bullets) + 1}",
                            text=content,
                            source_refs=[f"proj_{index}"],
                        )
                    )
                else:
                    bullets.append(
                        ResumeExperienceBullet(
                            id=f"proj_{index}_b{len(bullets) + 1}",
                            text=content,
                            source_refs=[f"proj_{index}"],
                        )
                    )
                continue
            if not start_date and _looks_like_date_line(line):
                start_date, end_date = _parse_date_range(line)
                continue
            if not role:
                role = line.strip()
            elif not summary:
                summary = line.strip()
        items.append(
            ResumeProjectItem(
                id=f"proj_{index}",
                name=name or subsection.heading,
                role=role,
                start_date=start_date,
                end_date=end_date,
                summary=summary,
                bullets=bullets,
                skills_used=_dedupe_strings(skills_used),
                source_refs=[f"proj_{index}"],
            )
        )
    return items


def _parse_skills(sections: list[MarkdownSection]) -> ResumeSkills:
    section = _get_section(sections, "skills")
    if section is None:
        return ResumeSkills()
    technical: list[str] = []
    tools: list[str] = []
    languages: list[str] = []

    if section.subsections:
        for subsection in section.subsections:
            group = _resolve_skill_group(subsection.heading)
            values = _collect_bullet_values(subsection.lines)
            if group == "languages":
                languages.extend(values)
            elif group == "tools":
                tools.extend(values)
            else:
                technical.extend(values)
    else:
        for line in section.lines:
            if not line.startswith("- "):
                continue
            content = _strip_bullet_prefix(line)
            label, values = _parse_labeled_skill_line(content)
            group = _resolve_skill_group(label)
            if group == "languages":
                languages.extend(values)
            elif group == "tools":
                tools.extend(values)
            else:
                technical.extend(values)

    return ResumeSkills(
        technical=_dedupe_strings(technical),
        tools=_dedupe_strings(tools),
        languages=_dedupe_strings(languages),
    )


def _parse_certification_items(sections: list[MarkdownSection]) -> list[ResumeCertificationItem]:
    values = _parse_simple_list_section(sections, "certificates")
    return [
        ResumeCertificationItem(
            id=f"cert_{index}",
            name=value,
            source_refs=[f"cert_{index}"],
        )
        for index, value in enumerate(values, start=1)
    ]


def _parse_simple_list_section(sections: list[MarkdownSection], key: str) -> list[str]:
    section = _get_section(sections, key)
    if section is None:
        return []
    return _collect_bullet_values(section.lines)


def _parse_custom_sections(sections: list[MarkdownSection]) -> list[ResumeCustomSection]:
    custom_sections: list[ResumeCustomSection] = []
    for index, section in enumerate(sections, start=1):
        if section.key in {"summary", "skills", "experience", "projects", "education", "certificates", "awards", "languages"}:
            continue
        items: list[ResumeCustomSectionItem] = []
        if section.subsections:
            for item_index, subsection in enumerate(section.subsections, start=1):
                title, subtitle = _split_header_pair(subsection.heading)
                description = _collect_bullet_values(subsection.lines)
                items.append(
                    ResumeCustomSectionItem(
                        id=f"custom_{index}_{item_index}",
                        title=title or subsection.heading,
                        subtitle=subtitle,
                        description=description,
                        source_refs=[f"custom_{index}_{item_index}"],
                    )
                )
        else:
            description = _collect_bullet_values(section.lines)
            if description:
                items.append(
                    ResumeCustomSectionItem(
                        id=f"custom_{index}_1",
                        title=section.title,
                        description=description,
                        source_refs=[f"custom_{index}_1"],
                    )
                )
        if items:
            custom_sections.append(
                ResumeCustomSection(
                    id=f"custom_{index}",
                    title=section.title,
                    items=items,
                )
            )
    return custom_sections


def _parse_education_meta_line(line: str) -> tuple[str, str, str, str]:
    degree = ""
    start_date = ""
    end_date = ""
    gpa = ""
    parts = [part.strip() for part in line.split("|") if part.strip()]
    for part in parts:
        if _looks_like_date_line(part):
            start_date, end_date = _parse_date_range(part)
        elif "GPA" in part.upper():
            gpa = part.replace("GPA", "").lstrip("：: ").strip()
        elif any(token in part for token in ("本科", "硕士", "博士", "大专")) and not degree:
            degree = part.split("/", 1)[0].strip()
    return degree, start_date, end_date, gpa


def _split_header_pair(value: str) -> tuple[str, str]:
    for separator in ("｜", "|"):
        if separator in value:
            left, right = value.split(separator, 1)
            return left.strip(), right.strip()
    return value.strip(), ""


def _looks_like_date_line(value: str) -> bool:
    lowered = value.lower()
    return bool(
        re.search(r"\d{4}", value)
        and any(token in value for token in ("-", "–", "—", ".", "/", "至今", "Present", "present"))
    ) or "至今" in lowered


def _parse_date_range(value: str) -> tuple[str, str]:
    normalized = value.replace("—", "-").replace("–", "-").replace("至今", "至今").strip()
    if " - " in normalized:
        start, end = normalized.split(" - ", 1)
    elif "-" in normalized:
        start, end = normalized.split("-", 1)
    else:
        return normalized, ""
    return start.strip(), end.strip()


def _parse_labeled_skill_line(content: str) -> tuple[str, list[str]]:
    normalized = re.sub(r"^\*\*(.+?)\*\*$", r"\1", content).strip()
    if "：" in normalized:
        label, values = normalized.split("：", 1)
        return label.strip(), _split_multi_value(values)
    return "", _split_multi_value(normalized)


def _resolve_skill_group(label: str) -> str:
    normalized = label.strip()
    if not normalized:
        return "technical"
    return SKILL_LABEL_TO_GROUP.get(normalized, "technical")


def _collect_bullet_values(lines: list[str]) -> list[str]:
    values: list[str] = []
    for line in lines:
        if not line.startswith("- "):
            continue
        values.extend(_split_multi_value(_strip_bullet_prefix(line)))
    return _dedupe_strings(values)


def _strip_bullet_prefix(line: str) -> str:
    content = line.removeprefix("- ").strip()
    content = re.sub(r"^\*\*(.+?)\*\*\s*", r"\1 ", content)
    return content.strip()


def _split_multi_value(value: str) -> list[str]:
    normalized = value.strip().strip("：:").strip()
    if not normalized:
        return []
    parts = re.split(r"[、,，;；]\s*", normalized)
    return [part.strip() for part in parts if part.strip()]


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _has_resume_signal(structured: ResumeStructuredData) -> bool:
    return bool(
        structured.basic_info.name.strip()
        and (
            structured.basic_info.summary.strip()
            or structured.education_items
            or structured.work_experience_items
            or structured.project_items
            or structured.skills.technical
            or structured.skills.tools
            or structured.skills.languages
        )
    )


def _get_section(sections: list[MarkdownSection], key: str) -> MarkdownSection | None:
    for section in sections:
        if section.key == key:
            return section
    return None
