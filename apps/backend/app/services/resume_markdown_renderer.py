from __future__ import annotations

from collections import OrderedDict
from typing import Any

from app.schemas.resume import (
    ResumeCustomSection,
    ResumeCustomSectionItem,
    ResumeExperienceBullet,
    ResumeStructuredData,
)

SKILL_GROUP_RULES = OrderedDict(
    [
        ("前端技术", ("react", "next.js", "nextjs", "vue", "nuxt", "angular")),
        ("后端技术", ("fastapi", "django", "flask", "spring", "spring boot", "express", "koa", "nestjs", "node.js")),
        ("开发语言", ("python", "java", "javascript", "typescript", "go", "c++", "c#")),
        ("测试工具", ("jest", "cypress", "playwright", "pytest", "testing library")),
        ("工程化", ("webpack", "vite", "rollup", "babel", "eslint", "git", "ci/cd")),
        ("数据库", ("mysql", "postgresql", "redis", "mongodb", "sqlite")),
        ("云 / 运维", ("docker", "kubernetes", "linux", "nginx", "minio")),
        ("工具", ("figma", "jira", "notion", "postman", "cursor", "codex")),
    ]
)
SECTION_BREAK_TOKENS = ("•", "●", "·", "▪", "■", "◆", ";", "；")


def _safe_validate_resume(data: dict[str, Any]) -> ResumeStructuredData:
    for key in ("education", "work_experience", "projects", "certifications"):
        if key in data and data[key]:
            fixed = []
            for item in data[key]:
                if isinstance(item, dict):
                    fixed.append(_dict_to_string(key, item))
                elif isinstance(item, str):
                    fixed.append(item)
            data = dict(data)
            data[key] = fixed
    return ResumeStructuredData.model_validate(data)


def _dict_to_string(key: str, item: dict) -> str:
    if key == "education":
        return "｜".join(
            filter(
                None,
                [
                    item.get("school", ""),
                    item.get("major", ""),
                    item.get("degree", ""),
                    item.get("start_date", ""),
                    item.get("end_date", ""),
                ],
            )
        )
    elif key == "work_experience":
        return "｜".join(
            filter(
                None,
                [
                    item.get("company", ""),
                    item.get("title", ""),
                    item.get("start_date", ""),
                    item.get("end_date", ""),
                ],
            )
        )
    elif key == "projects":
        return "｜".join(filter(None, [item.get("name", ""), item.get("role", "")]))
    elif key == "certifications":
        return "｜".join(
            filter(
                None,
                [item.get("name", ""), item.get("issuer", ""), item.get("date", "")],
            )
        )
    return str(item)


def render_resume_markdown(resume: ResumeStructuredData | dict[str, Any]) -> str:
    structured = (
        resume
        if isinstance(resume, ResumeStructuredData)
        else _safe_validate_resume(resume)
    )
    lines: list[str] = []
    lines.extend(_render_header(structured))
    lines.extend(_render_summary(structured))
    lines.extend(_render_skills(structured))
    lines.extend(_render_experience(structured))
    lines.extend(_render_projects(structured))
    lines.extend(_render_education(structured))
    lines.extend(
        _render_simple_list_section(
            title="证书",
            items=[
                _join_non_empty(
                    [item.name.strip(), item.issuer.strip(), item.date.strip()],
                    separator="｜",
                )
                for item in structured.certification_items
            ]
            or structured.certifications,
        )
    )
    lines.extend(_render_simple_list_section(title="奖项", items=structured.awards))
    lines.extend(
        _render_simple_list_section(title="语言能力", items=structured.skills.languages)
    )
    lines.extend(_render_custom_sections(structured.custom_sections))
    return _cleanup_markdown(lines)


def validate_resume_markdown_structure(
    resume: ResumeStructuredData | dict[str, Any],
    markdown: str,
) -> list[str]:
    structured = (
        resume
        if isinstance(resume, ResumeStructuredData)
        else _safe_validate_resume(resume)
    )
    errors: list[str] = []
    content = markdown.strip()
    if not content.startswith("# "):
        errors.append("first_line_must_be_h1")
    if "\n## " not in f"\n{content}":
        errors.append("missing_h2_section")
    if "\n- " not in f"\n{content}":
        errors.append("missing_bullet_list")
    if structured.work_experience_items and "\n### " not in f"\n{content}":
        errors.append("missing_h3_for_work_items")
    if structured.basic_info.email.strip() and "- 邮箱：" not in content:
        errors.append("missing_email_bullet")
    if structured.basic_info.phone.strip() and "- 电话：" not in content:
        errors.append("missing_phone_bullet")
    if (
        structured.work_experience_items
        and not any(
            bullet.text.strip()
            for item in structured.work_experience_items
            for bullet in item.bullets
        )
    ) is False and "- " not in content:
        errors.append("missing_description_bullets")
    return errors


def ensure_resume_markdown_structure(
    resume: ResumeStructuredData | dict[str, Any],
    markdown: str,
) -> str:
    errors = validate_resume_markdown_structure(resume, markdown)
    if errors:
        raise ValueError(
            "Canonical resume markdown failed structure validation: " + ",".join(errors)
        )
    return markdown


def _render_header(resume: ResumeStructuredData) -> list[str]:
    basic = resume.basic_info
    lines: list[str] = []
    name = _safe_text(basic.name)
    if name:
        lines.append(f"# {name}")

    title_line = _join_non_empty([basic.title, basic.status], separator="｜")
    if title_line:
        lines.append(title_line)

    contact_lines: list[str] = []
    if basic.email.strip():
        contact_lines.append(f"- 邮箱：{basic.email.strip()}")
    if basic.phone.strip():
        contact_lines.append(f"- 电话：{basic.phone.strip()}")
    if basic.location.strip():
        contact_lines.append(f"- 所在地：{basic.location.strip()}")
    for link in _normalize_bullets(basic.links):
        contact_lines.append(f"- 链接：{link}")

    if contact_lines:
        lines.append("")
        lines.extend(contact_lines)

    if lines:
        lines.append("")
    return lines


def _render_summary(resume: ResumeStructuredData) -> list[str]:
    summary = _safe_text(resume.basic_info.summary)
    if not summary:
        return []
    return ["## 个人简介", summary, ""]


def _render_skills(resume: ResumeStructuredData) -> list[str]:
    grouped = _normalize_and_group_skills(resume)
    if not grouped:
        return []

    lines = ["## 专业技能"]
    for group_name, items in grouped.items():
        if not items:
            continue
        lines.append(f"### {group_name}")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    return lines


def _render_experience(resume: ResumeStructuredData) -> list[str]:
    if not resume.work_experience_items:
        return []

    lines = ["## 工作经历"]
    for item in resume.work_experience_items:
        title = _join_non_empty([item.company, item.title], separator="｜")
        if title:
            lines.append(f"### {title}")

        date_line = _format_date_range(item.start_date, item.end_date)
        if date_line:
            lines.append(date_line)

        info_line = _join_non_empty(
            [
                item.department.strip(),
                item.location.strip(),
                item.employment_type.strip(),
            ],
            separator="｜",
        )
        if info_line:
            lines.append(info_line)

        for bullet in _normalize_experience_bullets(item.bullets):
            lines.append(f"- {bullet}")
        lines.append("")
    return lines


def _render_projects(resume: ResumeStructuredData) -> list[str]:
    if not resume.project_items:
        return []

    lines = ["## 项目经历"]
    for item in resume.project_items:
        title = _join_non_empty([item.name, item.role], separator="｜")
        if title:
            lines.append(f"### {title}")

        date_line = _format_date_range(item.start_date, item.end_date)
        if date_line:
            lines.append(date_line)

        if item.summary.strip():
            for bullet in _normalize_bullets(item.summary):
                lines.append(f"- {bullet}")

        for bullet in _normalize_experience_bullets(item.bullets):
            lines.append(f"- {bullet}")

        for skill in _normalize_bullets(item.skills_used):
            lines.append(f"- 技术栈：{skill}")
        lines.append("")
    return lines


def _render_education(resume: ResumeStructuredData) -> list[str]:
    if not resume.education_items:
        return []

    lines = ["## 教育经历"]
    for item in resume.education_items:
        title = _join_non_empty([item.school, item.major], separator="｜")
        if title:
            lines.append(f"### {title}")

        date_line = _format_date_range(item.start_date, item.end_date)
        if date_line:
            lines.append(date_line)

        if item.degree.strip():
            lines.append(f"- {item.degree.strip()}")
        if item.gpa.strip():
            lines.append(f"- GPA：{item.gpa.strip()}")
        for bullet in _normalize_bullets(item.honors):
            lines.append(f"- {bullet}")
        lines.append("")
    return lines


def _render_simple_list_section(*, title: str, items: list[str]) -> list[str]:
    values = _normalize_bullets(items)
    if not values:
        return []
    lines = [f"## {title}"]
    for value in values:
        lines.append(f"- {value}")
    lines.append("")
    return lines


def _render_custom_sections(custom_sections: list[ResumeCustomSection]) -> list[str]:
    lines: list[str] = []
    for section in custom_sections:
        section_title = _safe_text(section.title)
        if not section_title:
            continue
        lines.append(f"## {section_title}")
        for item in section.items:
            lines.extend(_render_custom_section_item(item))
        if lines and lines[-1] != "":
            lines.append("")
    return lines


def _render_custom_section_item(item: ResumeCustomSectionItem) -> list[str]:
    lines: list[str] = []
    heading = _join_non_empty([item.title, item.subtitle], separator="｜")
    if heading:
        lines.append(f"### {heading}")
    if item.years.strip():
        lines.append(item.years.strip())
    for bullet in _normalize_bullets(item.description):
        lines.append(f"- {bullet}")
    lines.append("")
    return lines


def _normalize_and_group_skills(
    resume: ResumeStructuredData,
) -> OrderedDict[str, list[str]]:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    technical = _normalize_bullets(resume.skills.technical)
    tools = _normalize_bullets(resume.skills.tools)

    ungrouped: list[str] = []
    for skill in technical + tools:
        matched_group = _match_skill_group(skill)
        if matched_group:
            grouped.setdefault(matched_group, [])
            if skill not in grouped[matched_group]:
                grouped[matched_group].append(skill)
            continue
        ungrouped.append(skill)

    if ungrouped:
        grouped["其他"] = []
        for item in ungrouped:
            if item not in grouped["其他"]:
                grouped["其他"].append(item)
    return grouped


def _match_skill_group(skill: str) -> str | None:
    lowered = skill.lower()
    for group_name, keywords in SKILL_GROUP_RULES.items():
        if any(keyword in lowered for keyword in keywords):
            return group_name
    return None


def _normalize_experience_bullets(bullets: list[ResumeExperienceBullet]) -> list[str]:
    result: list[str] = []
    for bullet in bullets:
        result.extend(_normalize_bullets(bullet.text))
    return result


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _format_date_range(start: str, end: str) -> str:
    start_value = _safe_text(start)
    end_value = _safe_text(end)
    if start_value and end_value:
        return f"{start_value} - {end_value}"
    return start_value or end_value


def _normalize_bullets(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    result: list[str] = []
    for item in values:
        text = _safe_text(item)
        if not text:
            continue
        split_items = [text]
        for token in SECTION_BREAK_TOKENS:
            next_items: list[str] = []
            for part in split_items:
                next_items.extend(part.split(token))
            split_items = next_items
        for part in split_items:
            cleaned = _safe_text(part).lstrip("-*•·●▪■◆").strip()
            if cleaned and cleaned not in result:
                result.append(cleaned)
    return result


def _join_non_empty(parts: list[str], *, separator: str) -> str:
    return separator.join(_safe_text(part) for part in parts if _safe_text(part))


def _cleanup_markdown(lines: list[str]) -> str:
    cleaned: list[str] = []
    prev_blank = False
    for line in lines:
        if line.strip():
            cleaned.append(line.rstrip())
            prev_blank = False
            continue
        if not prev_blank:
            cleaned.append("")
        prev_blank = True
    return "\n".join(cleaned).strip() + "\n"
