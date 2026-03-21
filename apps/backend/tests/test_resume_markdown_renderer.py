from __future__ import annotations

from app.schemas.resume import ResumeStructuredData
from app.services.resume_markdown_renderer import (
    render_resume_markdown,
    validate_resume_markdown_structure,
)


def test_render_resume_markdown_renders_header_and_contact_lines() -> None:
    markdown = render_resume_markdown(
        ResumeStructuredData(
            basic_info={
                "name": "郑文泽",
                "title": "高级前端工程师",
                "status": "立即到岗",
                "email": "zheng@example.com",
                "phone": "13800138000",
                "location": "北京",
                "links": ["https://github.com/example"],
            }
        )
    )

    assert markdown.startswith("# 郑文泽\n高级前端工程师｜立即到岗\n")
    assert "- 邮箱：zheng@example.com" in markdown
    assert "- 电话：13800138000" in markdown
    assert "- 所在地：北京" in markdown
    assert "- 链接：https://github.com/example" in markdown


def test_render_resume_markdown_groups_skills_into_sections() -> None:
    markdown = render_resume_markdown(
        ResumeStructuredData(
            skills={
                "technical": ["React", "TypeScript", "PostgreSQL"],
                "tools": ["Docker", "Figma"],
                "languages": [],
            }
        )
    )

    assert "## 专业技能" in markdown
    assert "### 前端框架" in markdown
    assert "- React" in markdown
    assert "### 开发语言" in markdown
    assert "- TypeScript" in markdown
    assert "### 数据库" in markdown
    assert "- PostgreSQL" in markdown
    assert "### 云 / 运维" in markdown
    assert "- Docker" in markdown
    assert "### 工具" in markdown
    assert "- Figma" in markdown


def test_render_resume_markdown_renders_experience_projects_education_and_custom_sections() -> None:
    markdown = render_resume_markdown(
        ResumeStructuredData(
            work_experience_items=[
                {
                    "company": "字节跳动",
                    "title": "高级前端工程师",
                    "start_date": "2021/07",
                    "end_date": "2024/12",
                    "bullets": [{"text": "负责增长平台建设"}, {"text": "主导指标体系重构"}],
                }
            ],
            project_items=[
                {
                    "name": "CareerPilot",
                    "role": "核心开发",
                    "start_date": "2024/01",
                    "end_date": "2024/12",
                    "summary": "智能求职工作台",
                    "bullets": [{"text": "实现简历解析工作流"}],
                    "skills_used": ["FastAPI"],
                },
                {
                    "name": "黑马点评",
                    "role": "后端开发",
                    "bullets": [{"text": "完成秒杀链路改造"}],
                },
            ],
            education_items=[
                {
                    "school": "新疆大学",
                    "major": "软件工程",
                    "degree": "本科",
                    "start_date": "2023/09",
                    "end_date": "2027/06",
                    "gpa": "3.73",
                    "honors": ["211", "双一流"],
                }
            ],
            custom_sections=[
                {
                    "title": "校园经历",
                    "items": [
                        {
                            "title": "学生会",
                            "subtitle": "技术部",
                            "years": "2022 - 2023",
                            "description": ["负责招新系统开发", "维护活动报名工具"],
                        }
                    ],
                }
            ],
        )
    )

    assert "## 工作经历" in markdown
    assert "### 字节跳动｜高级前端工程师" in markdown
    assert "2021/07 - 2024/12" in markdown
    assert "- 负责增长平台建设" in markdown
    assert "- 主导指标体系重构" in markdown

    assert "## 项目经历" in markdown
    assert "### CareerPilot｜核心开发" in markdown
    assert "2024/01 - 2024/12" in markdown
    assert "- 智能求职工作台" in markdown
    assert "- 实现简历解析工作流" in markdown
    assert "- 技术栈：FastAPI" in markdown
    assert "### 黑马点评｜后端开发" in markdown

    assert "## 教育经历" in markdown
    assert "### 新疆大学｜软件工程" in markdown
    assert "2023/09 - 2027/06" in markdown
    assert "- 本科" in markdown
    assert "- GPA：3.73" in markdown

    assert "## 校园经历" in markdown
    assert "### 学生会｜技术部" in markdown
    assert "2022 - 2023" in markdown
    assert "- 负责招新系统开发" in markdown


def test_render_resume_markdown_filters_empty_sections_and_is_stable() -> None:
    structured = ResumeStructuredData(
        basic_info={"name": "郑文泽"},
        awards=["百度之星金奖"],
        skills={"languages": ["English"]},
    )

    first = render_resume_markdown(structured)
    second = render_resume_markdown(structured)

    assert "## 工作经历" not in first
    assert "## 项目经历" not in first
    assert "## 奖项" in first
    assert "## 语言能力" in first
    assert first == second


def test_validate_resume_markdown_structure_rejects_plain_text_output() -> None:
    structured = ResumeStructuredData(
        basic_info={
            "name": "郑文泽",
            "email": "zheng@example.com",
            "phone": "13800138000",
        },
        work_experience_items=[
            {
                "company": "字节跳动",
                "title": "工程师",
                "bullets": [{"text": "负责平台建设"}],
            }
        ],
    )

    errors = validate_resume_markdown_structure(
        structured,
        "郑文泽\n字节跳动 工程师\n负责平台建设",
    )

    assert "first_line_must_be_h1" in errors
    assert "missing_h2_section" in errors
    assert "missing_bullet_list" in errors
    assert "missing_h3_for_work_items" in errors
    assert "missing_email_bullet" in errors
    assert "missing_phone_bullet" in errors
