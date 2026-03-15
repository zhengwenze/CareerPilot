from __future__ import annotations

from app.services.resume_parser import build_structured_resume


def test_build_structured_resume_extracts_realistic_chinese_content() -> None:
    raw_text = """
    郑文泽
    zheng@example.com 13800138000 上海
    3年数据分析经验，负责指标体系建设、实验分析与跨团队协作。

    教育背景
    复旦大学 统计学 本科

    工作经历
    2023.06-至今 CareerPilot 数据分析师
    负责 Python、SQL、实验分析和增长分析项目。

    项目经历
    增长实验平台重构
    搭建 Tableau 看板并复盘 A/B Testing 结果。

    专业技能
    Python、SQL、Tableau、Docker、English

    证书奖项
    CET-6
    """

    structured = build_structured_resume(raw_text)

    assert structured.basic_info.name == "郑文泽"
    assert structured.basic_info.email == "zheng@example.com"
    assert structured.basic_info.phone == "13800138000"
    assert structured.basic_info.location == "上海"
    assert "复旦大学" in structured.education[0]
    assert "CareerPilot 数据分析师" in structured.work_experience[0]
    assert "增长实验平台重构" in structured.projects[0]
    assert "Python" in structured.skills.technical
    assert "Docker" in structured.skills.tools
    assert "English" in structured.skills.languages
    assert "CET-6" in structured.certifications[0]


def test_build_structured_resume_handles_spaced_headings_and_inline_sections() -> None:
    raw_text = """
    李四
    li@example.com 13900001111 北京
    教 育 经 历 上海交通大学 计算机硕士
    工 作 经 历 2022-至今 某科技公司 产品实习生
    项 目 经 历 智能简历平台
    技 能 Python / Excel / English
    """

    structured = build_structured_resume(raw_text)

    assert structured.basic_info.name == "李四"
    assert structured.basic_info.email == "li@example.com"
    assert structured.basic_info.phone == "13900001111"
    assert "上海交通大学" in structured.education[0]
    assert any("某科技公司" in item for item in structured.work_experience)
    assert any("智能简历平台" in item for item in structured.projects)
    assert "Python" in structured.skills.technical
    assert "Excel" in structured.skills.technical
    assert "English" in structured.skills.languages
