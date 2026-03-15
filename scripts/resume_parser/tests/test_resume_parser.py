from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.resume_parser.pipeline import parse_resume_file, parse_resume_text


def test_parse_resume_text_extracts_realistic_chinese_content() -> None:
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

    result = parse_resume_text(raw_text)
    structured = result.structured_data

    assert structured.basic_info.name == "郑文泽"
    assert structured.basic_info.email == "zheng@example.com"
    assert structured.basic_info.phone == "13800138000"
    assert structured.basic_info.location == "上海"
    assert "复旦大学" in structured.education[0]
    assert "CareerPilot 数据分析师" in structured.work_experience[0]
    assert "负责 Python、SQL" in structured.work_experience[0]
    assert "增长实验平台重构" in structured.projects[0]
    assert "Python" in structured.skills.technical
    assert "Docker" in structured.skills.tools
    assert "English" in structured.skills.languages
    assert "CET-6" in structured.certifications[0]


def test_parse_resume_text_handles_spaced_headings_and_inline_sections() -> None:
    raw_text = """
    李四
    li@example.com 13900001111 北京
    教 育 经 历 上海交通大学 计算机硕士
    工 作 经 历 2022-至今 某科技公司 产品实习生
    项 目 经 历 智能简历平台
    技 能 Python / Excel / English
    """

    structured = parse_resume_text(raw_text).structured_data

    assert structured.basic_info.name == "李四"
    assert structured.basic_info.email == "li@example.com"
    assert structured.basic_info.phone == "13900001111"
    assert "上海交通大学" in structured.education[0]
    assert any("某科技公司" in item for item in structured.work_experience)
    assert any("智能简历平台" in item for item in structured.projects)
    assert "Python" in structured.skills.technical
    assert "Excel" in structured.skills.technical
    assert "English" in structured.skills.languages


def test_parse_resume_text_groups_multiline_entries() -> None:
    raw_text = """
    王五
    wangwu@example.com 13800138001 杭州

    工作经历
    2021.03-2023.12 某互联网公司 数据分析师
    负责搭建 SQL 指标体系，沉淀日报与周报。
    主导 A/B Testing 平台分析流程优化。
    2020.01-2021.02 某咨询公司 商业分析师
    参与客户增长项目，输出 Tableau 看板。

    项目经历
    增长看板平台
    搭建多业务线指标看板，服务运营和产品团队。
    用户分层重构
    负责用户标签分层与实验复盘。
    """

    structured = parse_resume_text(raw_text).structured_data

    assert len(structured.work_experience) == 2
    assert "主导 A/B Testing 平台分析流程优化" in structured.work_experience[0]
    assert len(structured.projects) == 2
    assert "服务运营和产品团队" in structured.projects[0]


def test_parse_resume_file_supports_plain_text_input(tmp_path: Path) -> None:
    input_path = tmp_path / "resume.txt"
    input_path.write_text(
        "\n".join(
            [
                "赵六",
                "zhaoliu@example.com 13900001112 深圳",
                "教育经历",
                "中山大学 软件工程 本科",
            ]
        ),
        encoding="utf-8",
    )

    result = parse_resume_file(input_path)

    assert result.source_file == input_path.resolve()
    assert result.structured_data.basic_info.name == "赵六"
    assert "中山大学" in result.structured_data.education[0]


def test_parse_resume_text_avoids_false_work_entries_and_merges_projects() -> None:
    raw_text = """
    郑文泽
    电话:17590522997
    邮箱:2017160177@qq.com
    当前状态:在校生
    求职岗位:AI应用开发
    到岗时间:立即到岗
    所在城市:北京
    实习时间:3个月

    教育背景
    本科 - 新疆大学 - 软件工程(2023.09 至 2027.06) 211 双一流
    竞赛获奖:百度之星金奖
    机器人区域赛一等奖
    科研成果:发表 RV-DANet 模型论文
    提升了分割精度
    软件著作权:《精灵e站软件》软著

    项目经验
    黑马点评 https://gitee.com/zwz050418/shopping-system
    技术栈:Java、Kafka、MySQL、RocketMQ
    项目成果:
    完成高可用秒杀系统从0到1的架构设计与实现。
    保证核心交易链路的数据一致性。
    可溯源代码库智能助手 https://gitee.com/zwz050418/code-rag-lab
    技术栈:Python、LangChain、FastAPI、MySQL
    项目成果:
    独立设计并实现了一套基于RAG技术的智能代码问答系统。
    显著提升开发者调试与代码理解效率。

    专业技能
    技术框架:熟练使用LangChain构建AI Agent;了解LangGraph、AutoGen等框架
    系统架构:精通分布式系统(Redis、Kafka、RocketMQ)、容器化技术(Docker、Kubernetes/K8s)
    数据库:MySQL、PostgreSQL、MongoDB;熟练使用SQL
    """

    structured = parse_resume_text(raw_text).structured_data

    assert structured.basic_info.summary == ""
    assert structured.work_experience == []
    assert len(structured.projects) == 2
    assert "完成高可用秒杀系统从0到1的架构设计与实现" in structured.projects[0]
    assert "保证核心交易链路的数据一致性" in structured.projects[0]
    assert "独立设计并实现了一套基于RAG技术的智能代码问答系统" in structured.projects[1]
    assert "显著提升开发者调试与代码理解效率" in structured.projects[1]
    assert "机器人区域赛一等奖" not in structured.education[0]
    assert any("竞赛获奖" in item for item in structured.certifications)
    assert any("机器人区域赛一等奖" in item for item in structured.certifications)
    assert any("软件著作权" in item for item in structured.certifications)
    assert len(structured.certifications) == 3
    assert "Kafka" in structured.skills.technical
    assert "LangChain" in structured.skills.technical
    assert "MongoDB" in structured.skills.technical
