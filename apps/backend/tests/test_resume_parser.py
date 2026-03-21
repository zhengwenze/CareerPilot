from __future__ import annotations

from app.services.resume_parser import build_structured_resume


def test_build_structured_resume_parses_chinese_student_resume_blocks() -> None:
    raw_text = """
    郑文泽
    17590522997 | 2017160177@qq.com | 北京
    求职方向：AI 应用开发 | 立即到岗 | 可实习 6 个月
    教育背景
    新疆大学（211 / 双一流） 本科 / 软件工程 2023.09 – 2027.06
    GPA 3.73，专业排名 50/800
    • 竞赛获奖：百度之星省赛金奖；RoboCup 新疆一等奖；计算机设计大赛新疆区三等奖；全球校园 AI 算法精
    英大赛省赛三等奖；三维数字化创新设计大赛新疆赛区二等奖。
    • 科研成果：发表 RV-DANet 相关论文，围绕视网膜血管多尺度分割任务提出改进网络并提升分割精度。
    • 其他成果：《精灵 e 站软件》《运动健康智能监测系统》软件著作权；CET-4 538，CET-6 492。
    项目经历
    职点迷津 https://gitee.com/zwz050418/career-pilot.git
    智能求职工作台；React + Next.js + TypeScript + Python + FastAPI + PostgreSQL + Redis + MinIO
    • 负责简历解析、岗位匹配、优化建议生成等核心链路开发，完成“简历上传—结构化抽取—岗位对比—建议生
    成”闭环。
    • 基于 FastAPI + SQLAlchemy + PostgreSQL 设计简历、岗位、匹配报告等核心数据模型，封装业务接口与校验
    逻辑。
    • 接入 AI 能力实现 PDF 简历解析、JD 信息抽取、匹配评分与优化建议生成，完成规则逻辑与模型能力结合的
    业务落地。
    • 使用 Redis 实现高频缓存与 Token Blocklist，结合 MinIO 完成 PDF 对象存储，提升系统响应效率与文件管理
    能力。
    黑马点评 https://gitee.com/zwz050418/zwz-hmdp.git
    本地生活服务平台；Spring Boot + MySQL + Redis + RocketMQ + Vue 3
    • 负责用户认证、商铺查询、优惠券管理等核心模块开发，完成业务接口封装、数据交互与主流程落地。
    • 使用 Redis 优化热点数据访问与登录状态管理；在秒杀链路中基于 Lua 脚本实现库存扣减校验和一人一单原
    子控制。
    • 基于 RocketMQ 搭建异步下单机制，对秒杀请求削峰填谷，结合幂等处理与状态校验提升高并发场景稳定性。
    • 扩展达人探店内容模块，支持图文博客发布、点赞、点赞排行榜与关注流收件箱，基于 ZSet 实现高效排序查
    询。
    个人优势
    • 具备 AI 应用开发与后端开发能力，能够完成从需求分析、接口设计到功能落地的完整开发流程。
    • 熟悉 AI 编程协作方式，使用过 4 种 AI 工具（Trae、Cursor、Codex、OpenClaw），可熟练借助 AI 完成代码生
    成、调试排错、接口联调、数据处理、文档编写与项目重构。
    • 有 AI 能力接入与业务落地经验，能够结合规则逻辑与模型能力实现简历解析、信息抽取、匹配评分、优化
    建议生成等实际功能。
    专业技能
    • 编程语言：Python、Java、TypeScript、JavaScript
    • 后端开发：FastAPI、Spring Boot、RESTful API
    • 前端基础：React、Next.js、Vue 3
    • 数据库与中间件：PostgreSQL、MySQL、Redis、MinIO、RocketMQ
    • AI 应用：Prompt Engineering、简历解析、信息抽取、岗位匹配、优化建议生成、AI 能力接入与业务落地
    • 开发工具：Git、Linux、Trae、Cursor、Codex、OpenClaw
    """.strip()

    structured = build_structured_resume(raw_text)

    assert structured.basic_info.name == "郑文泽"
    assert structured.basic_info.email == "2017160177@qq.com"
    assert structured.basic_info.phone == "17590522997"
    assert structured.basic_info.location == "北京"
    assert "AI 应用开发" in structured.basic_info.summary

    assert len(structured.education_items) == 1
    education = structured.education_items[0]
    assert education.school == "新疆大学"
    assert education.degree == "本科"
    assert education.major == "软件工程"
    assert education.start_date == "2023.09"
    assert education.end_date == "2027.06"
    assert education.gpa == "3.73"
    assert "211" in education.honors
    assert "双一流" in education.honors
    assert "专业排名 50/800" in education.honors

    assert len(structured.project_items) == 2
    assert structured.project_items[0].name == "职点迷津"
    assert "智能求职工作台" in structured.project_items[0].summary
    assert len(structured.project_items[0].bullets) == 4
    assert "FastAPI" in structured.project_items[0].skills_used
    assert "Redis" in structured.project_items[0].skills_used
    assert structured.project_items[1].name == "黑马点评"
    assert "本地生活服务平台" in structured.project_items[1].summary
    assert len(structured.project_items[1].bullets) == 4
    assert all(item.name != "个人优势" for item in structured.project_items)

    assert "Python" in structured.skills.technical
    assert "Next.js" in structured.skills.technical
    assert "RocketMQ" in structured.projects[1]
    assert "Git" in structured.skills.tools
    assert "Linux" in structured.skills.tools

    assert any("百度之星省赛金奖" == item.name for item in structured.certification_items)
    assert any("发表 RV-DANet 相关论文" in item.name for item in structured.certification_items)
    assert any("CET-4 538，CET-6 492" in item.name for item in structured.certification_items)
