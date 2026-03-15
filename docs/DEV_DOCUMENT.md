# 📚 《职点迷津》开发文档

> **文档版本**：v0.1（第一版） | **最后更新**：2026-03-13 | **当前进度**：规划阶段 0/8

---

## 一、项目概览

| 字段 | 内容 |
|:----:|:----:|
| 项目名称 | 职点迷津 |
| 项目描述 | 一个面向求职者的 AI 求职提升平台，围绕“简历解析、岗位匹配、简历优化、模拟面试、项目话术、历史复盘”形成完整闭环。 |
| 开发类型 | 全栈 Web 应用 |
| 开始时间 | 2026-03-13 |
| 仓库地址 | https://gitee.com/zwz050418/career-pilot |

### 1.1 项目愿景

《职点迷津》不是一个“把大模型接进来就结束”的聊天工具，而是一个普通求职者打开就能直接用的场景化产品。用户无需理解 Prompt、RAG 或模型能力，只需要上传简历、输入目标岗位信息，就能获得结构化分析、模拟训练和持续复盘。

### 1.2 产品方法论

1. 场景化封装 AI：不要求用户会提问，系统用固定流程收集信息并输出结果。
2. 输出必须可执行：不仅给结论，还要给差距、优先级和下一步动作。
3. 强调持续使用：通过历史记录、复盘建议和多轮训练提高复访率。
4. 先验证闭环，再放大功能：优先跑通“上传简历 -> 匹配岗位 -> 模拟面试 -> 复盘改进”的完整链路。
5. 沉淀可复用底层能力：把解析、检索、评分、会话、评测等能力做成平台资产，后续可复制到其他垂类。

### 1.3 项目成功定义

V1 成功不以“功能数量”定义，而以以下结果定义：

- 用户首次使用能够在 10 分钟内跑完一条完整求职闭环。
- 六大模块全部可用，但优先保证主链路稳定与解释性。
- 匹配准确度、检索命中率、回答质量、评分逻辑四项指标均可量化验证。
- 项目能作为作品集展示 AI 工程能力，而不是停留在接口调用演示。

### 1.4 V1 范围边界

**V1 必须完成的功能**

- 用户注册登录
- 简历 PDF 上传、解析、结构化展示与人工校正
- JD 输入、匹配评分、差距说明
- 简历优化建议
- 多轮模拟面试、流式输出、会话状态管理
- 项目介绍话术生成
- 面试记录保存、评分、薄弱点分析
- 评测集与指标看板基础版本

**V1 暂不纳入的功能，不要开发**

- 支付与会员体系
- 社区分享与社交裂变
- 多语言支持
- 企业侧招聘后台

---

## 二、系统架构

### 2.1 整体架构图

```mermaid
flowchart TD
    U["求职用户"] --> W["Web 前端<br/>Next.js + TypeScript"]
    W --> G["API 网关/BFF 层"]
    G --> A["业务服务<br/>FastAPI"]
    A --> DB["PostgreSQL"]
    A --> V["pgvector"]
    A --> R["Redis"]
    A --> S["MinIO / S3"]
    A --> L["大模型适配层<br/>OpenAI-Compatible / 第三方模型"]
    A --> LG["LangGraph 会话编排"]
    A --> E["评测与日志层<br/>LangSmith / 自建评测"]

    S --> A
    DB --> E
    V --> E
```

### 2.2 目标仓库结构

```text
career-pilot/
├── apps/
│   ├── web/                 # Next.js 前端
│   └── api/                 # FastAPI 后端
├── packages/
│   ├── shared/              # 共用类型、常量、评分规则
│   └── prompts/             # Prompt 模板与版本管理
├── infra/
│   ├── docker/              # Docker Compose / Nginx / MinIO
│   └── sql/                 # 初始化 SQL / 迁移辅助脚本
├── docs/
│   ├── benchmarks/          # 评测集定义与标注说明
│   ├── decisions/           # 架构决策记录 ADR
│   └── api/                 # 补充接口说明
├── DEV_DOCUMENT.md
├── 职点迷津_API.md
└── 职点迷津_STYLE.md
```

### 2.3 技术栈全景

| 层级 | 技术 | 版本策略 | 用途 |
|------|------|----------|------|
| 前端框架 | Next.js | 稳定版 | 页面渲染、路由、前端交互 |
| 前端语言 | TypeScript | 稳定版 | 类型安全 |
| 样式系统 | Tailwind CSS | 稳定版 | 设计系统与页面样式 |
| 组件方案 | shadcn/ui | 稳定版 | 基础组件库 |
| 后端语言 | Python | 稳定版 | AI 编排、解析、RAG、评分 |
| 后端框架 | FastAPI | 稳定版 | API 服务、流式输出 |
| AI 工作流 | LangGraph | 稳定版 | 多轮会话编排、状态管理 |
| 数据库 | PostgreSQL | 16+ | 业务数据存储 |
| 向量检索 | pgvector | 稳定版 | RAG 检索 |
| 缓存/状态 | Redis | 7+ | 会话缓存、限流、任务状态 |
| 文件存储 | MinIO / S3 | 稳定版 | PDF 文件与报告存储 |
| 认证 | JWT + Refresh Token | 自定义实现 | 用户鉴权 |
| 观测与评测 | LangSmith / 自建评测脚本 | 稳定版 | Prompt、检索、回答质量评估 |
| 部署 | Docker Compose + 云服务器 | 稳定版 | 本地开发与生产部署 |

### 2.4 分层设计

- 表现层：负责上传、报告展示、流式对话、历史记录与分析图表。
- 业务层：负责简历解析、岗位匹配、优化建议、项目话术、面试评分。
- AI 编排层：负责 Prompt 管理、检索策略、多轮状态、模型适配。
- 数据层：负责业务库、向量库、日志与评测结果沉淀。
- 评测层：负责离线回归测试、指标统计、提示词版本对比。

### 2.5 核心架构原则

1. 规则先打骨架，模型再做解释，避免“裸打分”。
2. 所有 AI 输出都要可追踪：来源、Prompt 版本、命中文档、评分依据都要记录。
3. RAG 不做泛化大知识库，而是优先围绕用户简历、JD、历史记录和面试规则构建高相关知识库。
4. 流式输出和多轮记忆必须服务真实面试体验，而不是为了展示技术而展示技术。

---

## 三、数据库设计

### 3.1 ER 关系图

```mermaid
erDiagram
    USERS ||--o{ RESUMES : owns
    USERS ||--o{ JOB_DESCRIPTIONS : creates
    USERS ||--o{ INTERVIEW_SESSIONS : starts
    USERS ||--o{ PROJECT_SCRIPTS : owns
    RESUMES ||--o{ KNOWLEDGE_CHUNKS : splits
    JOB_DESCRIPTIONS ||--o{ KNOWLEDGE_CHUNKS : splits
    RESUMES ||--o{ MATCH_REPORTS : compares
    JOB_DESCRIPTIONS ||--o{ MATCH_REPORTS : compares
    MATCH_REPORTS ||--o{ OPTIMIZATION_REPORTS : derives
    INTERVIEW_SESSIONS ||--o{ INTERVIEW_TURNS : contains
    INTERVIEW_TURNS ||--o{ RETRIEVAL_LOGS : uses
    INTERVIEW_SESSIONS ||--|| INTERVIEW_EVALUATIONS : summarizes
    PROMPT_VERSIONS ||--o{ MATCH_REPORTS : powers
    PROMPT_VERSIONS ||--o{ OPTIMIZATION_REPORTS : powers
    PROMPT_VERSIONS ||--o{ INTERVIEW_EVALUATIONS : powers
    PROMPT_VERSIONS ||--o{ PROJECT_SCRIPTS : powers
    PROMPT_VERSIONS ||--o{ EVALUATION_RUNS : validates
```

### 3.2 数据表详细设计

#### 表：users（用户表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 用户 ID |
| email | VARCHAR(255) | NOT NULL, UNIQUE | — | 登录邮箱 |
| password_hash | VARCHAR(255) | NOT NULL | — | 密码哈希 |
| nickname | VARCHAR(80) | NULL | NULL | 用户昵称 |
| role | VARCHAR(20) | NOT NULL | user | admin / user |
| status | VARCHAR(20) | NOT NULL | active | active / disabled |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | now() | 更新时间 |

**索引：**

- `idx_users_email` ON (email)
- `idx_users_status` ON (status)

#### 表：resumes（简历表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 简历 ID |
| user_id | UUID | FK -> users.id | — | 所属用户 |
| file_name | VARCHAR(255) | NOT NULL | — | 原始文件名 |
| file_url | TEXT | NOT NULL | — | PDF 存储地址 |
| parse_status | VARCHAR(20) | NOT NULL | pending | pending / success / failed |
| raw_text | TEXT | NULL | NULL | 原始抽取文本 |
| structured_json | JSONB | NULL | NULL | 结构化简历结果 |
| latest_version | INTEGER | NOT NULL | 1 | 结构化版本 |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | now() | 更新时间 |

**索引：**

- `idx_resumes_user_id` ON (user_id)
- `idx_resumes_parse_status` ON (parse_status)

#### 表：job_descriptions（JD 表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | JD ID |
| user_id | UUID | FK -> users.id | — | 所属用户 |
| title | VARCHAR(255) | NOT NULL | — | 岗位标题 |
| company | VARCHAR(255) | NULL | NULL | 公司名称 |
| jd_text | TEXT | NOT NULL | — | 原始 JD 文本 |
| structured_json | JSONB | NULL | NULL | 结构化 JD |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | now() | 更新时间 |

**索引：**

- `idx_jds_user_id` ON (user_id)

#### 表：knowledge_chunks（知识分片表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 分片 ID |
| source_type | VARCHAR(30) | NOT NULL | — | resume / jd / interview_history / rubric |
| source_id | UUID | NOT NULL | — | 来源对象 ID |
| chunk_text | TEXT | NOT NULL | — | 分片文本 |
| chunk_meta | JSONB | NOT NULL | '{}' | 分片元数据 |
| embedding | VECTOR | NULL | NULL | 向量数据 |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |

**索引：**

- `idx_chunks_source` ON (source_type, source_id)

#### 表：match_reports（JD 匹配报告表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 报告 ID |
| user_id | UUID | FK -> users.id | — | 所属用户 |
| resume_id | UUID | FK -> resumes.id | — | 简历 ID |
| jd_id | UUID | FK -> job_descriptions.id | — | JD ID |
| overall_score | NUMERIC(5,2) | NOT NULL | 0 | 综合匹配分 |
| rule_score | NUMERIC(5,2) | NOT NULL | 0 | 规则骨架分 |
| model_score | NUMERIC(5,2) | NOT NULL | 0 | 模型修正分 |
| gap_json | JSONB | NOT NULL | '{}' | 差距项说明 |
| evidence_json | JSONB | NOT NULL | '{}' | 打分依据 |
| prompt_version_id | UUID | FK -> prompt_versions.id | — | Prompt 版本 |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |

**索引：**

- `idx_match_reports_user_id` ON (user_id)
- `idx_match_reports_resume_jd` ON (resume_id, jd_id)

#### 表：optimization_reports（简历优化建议表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 报告 ID |
| match_report_id | UUID | FK -> match_reports.id | — | 来源匹配报告 |
| advice_json | JSONB | NOT NULL | '{}' | 分模块建议 |
| priority_json | JSONB | NOT NULL | '{}' | 优先级排序 |
| prompt_version_id | UUID | FK -> prompt_versions.id | — | Prompt 版本 |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |

#### 表：project_scripts（项目话术表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 话术 ID |
| user_id | UUID | FK -> users.id | — | 所属用户 |
| resume_id | UUID | FK -> resumes.id | — | 来源简历 |
| script_type | VARCHAR(30) | NOT NULL | — | short / standard / deep_dive |
| content | TEXT | NOT NULL | — | 话术内容 |
| evidence_json | JSONB | NOT NULL | '{}' | 生成依据 |
| prompt_version_id | UUID | FK -> prompt_versions.id | — | Prompt 版本 |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |

#### 表：interview_sessions（面试会话表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 会话 ID |
| user_id | UUID | FK -> users.id | — | 所属用户 |
| resume_id | UUID | FK -> resumes.id | — | 使用简历 |
| jd_id | UUID | FK -> job_descriptions.id | — | 目标 JD |
| thread_id | VARCHAR(100) | NOT NULL, UNIQUE | — | LangGraph 线程 ID |
| status | VARCHAR(20) | NOT NULL | active | active / finished / abandoned |
| interview_mode | VARCHAR(30) | NOT NULL | mixed | hr / technical / mixed |
| started_at | TIMESTAMP | NOT NULL | now() | 开始时间 |
| ended_at | TIMESTAMP | NULL | NULL | 结束时间 |

**索引：**

- `idx_sessions_user_id` ON (user_id)
- `idx_sessions_status` ON (status)

#### 表：interview_turns（面试轮次表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 轮次 ID |
| session_id | UUID | FK -> interview_sessions.id | — | 会话 ID |
| turn_index | INTEGER | NOT NULL | — | 轮次序号 |
| role | VARCHAR(20) | NOT NULL | — | interviewer / candidate |
| content | TEXT | NOT NULL | — | 对话内容 |
| score_json | JSONB | NULL | NULL | 轮次评分 |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |

**索引：**

- `idx_turns_session_id` ON (session_id, turn_index)

#### 表：retrieval_logs（检索日志表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 日志 ID |
| turn_id | UUID | FK -> interview_turns.id | — | 所属轮次 |
| query_text | TEXT | NOT NULL | — | 检索查询 |
| hit_chunks_json | JSONB | NOT NULL | '[]' | 命中文档列表 |
| recall_label_json | JSONB | NULL | NULL | 评测标注结果 |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |

#### 表：interview_evaluations（面试总评表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 总评 ID |
| session_id | UUID | FK -> interview_sessions.id, UNIQUE | — | 会话 ID |
| total_score | NUMERIC(5,2) | NOT NULL | 0 | 总分 |
| dimension_scores | JSONB | NOT NULL | '{}' | 分维度得分 |
| weaknesses_json | JSONB | NOT NULL | '[]' | 薄弱点 |
| improvement_json | JSONB | NOT NULL | '[]' | 改进建议 |
| prompt_version_id | UUID | FK -> prompt_versions.id | — | Prompt 版本 |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |

#### 表：prompt_versions（Prompt 版本表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 版本 ID |
| module_name | VARCHAR(50) | NOT NULL | — | parse / match / optimize / interview / score |
| version_name | VARCHAR(50) | NOT NULL | — | 版本名 |
| template_text | TEXT | NOT NULL | — | Prompt 内容 |
| config_json | JSONB | NOT NULL | '{}' | 模型配置 |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |

#### 表：evaluation_runs（评测运行表）

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | UUID | PK | gen_random_uuid() | 评测 ID |
| module_name | VARCHAR(50) | NOT NULL | — | match / retrieval / answer / score |
| dataset_name | VARCHAR(100) | NOT NULL | — | 评测数据集名称 |
| prompt_version_id | UUID | FK -> prompt_versions.id | — | 版本 ID |
| metrics_json | JSONB | NOT NULL | '{}' | 指标结果 |
| notes | TEXT | NULL | NULL | 结果备注 |
| created_at | TIMESTAMP | NOT NULL | now() | 创建时间 |

### 3.3 数据库初始化 SQL（核心表第一版）

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  nickname VARCHAR(80),
  role VARCHAR(20) NOT NULL DEFAULT 'user',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE resumes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  file_name VARCHAR(255) NOT NULL,
  file_url TEXT NOT NULL,
  parse_status VARCHAR(20) NOT NULL DEFAULT 'pending',
  raw_text TEXT,
  structured_json JSONB,
  latest_version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE job_descriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  title VARCHAR(255) NOT NULL,
  company VARCHAR(255),
  jd_text TEXT NOT NULL,
  structured_json JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE knowledge_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type VARCHAR(30) NOT NULL,
  source_id UUID NOT NULL,
  chunk_text TEXT NOT NULL,
  chunk_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  embedding VECTOR(1536),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE prompt_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  module_name VARCHAR(50) NOT NULL,
  version_name VARCHAR(50) NOT NULL,
  template_text TEXT NOT NULL,
  config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE match_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  resume_id UUID NOT NULL REFERENCES resumes(id),
  jd_id UUID NOT NULL REFERENCES job_descriptions(id),
  overall_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  rule_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  model_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  gap_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  prompt_version_id UUID REFERENCES prompt_versions(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE optimization_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_report_id UUID NOT NULL REFERENCES match_reports(id),
  advice_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  priority_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  prompt_version_id UUID REFERENCES prompt_versions(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE project_scripts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  resume_id UUID NOT NULL REFERENCES resumes(id),
  script_type VARCHAR(30) NOT NULL,
  content TEXT NOT NULL,
  evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  prompt_version_id UUID REFERENCES prompt_versions(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE interview_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  resume_id UUID NOT NULL REFERENCES resumes(id),
  jd_id UUID NOT NULL REFERENCES job_descriptions(id),
  thread_id VARCHAR(100) NOT NULL UNIQUE,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  interview_mode VARCHAR(30) NOT NULL DEFAULT 'mixed',
  started_at TIMESTAMP NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMP
);

CREATE TABLE interview_turns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES interview_sessions(id),
  turn_index INTEGER NOT NULL,
  role VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  score_json JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE retrieval_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  turn_id UUID NOT NULL REFERENCES interview_turns(id),
  query_text TEXT NOT NULL,
  hit_chunks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  recall_label_json JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE interview_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL UNIQUE REFERENCES interview_sessions(id),
  total_score NUMERIC(5,2) NOT NULL DEFAULT 0,
  dimension_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
  weaknesses_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  improvement_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  prompt_version_id UUID REFERENCES prompt_versions(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE evaluation_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  module_name VARCHAR(50) NOT NULL,
  dataset_name VARCHAR(100) NOT NULL,
  prompt_version_id UUID REFERENCES prompt_versions(id),
  metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

## 四、核心业务流程

### 4.1 用户主链路流程

```text
用户注册/登录
    ↓
上传简历 PDF
    ↓
系统解析并抽取结构化信息
    ↓
用户手动修正解析结果
    ↓
输入目标岗位 JD
    ↓
生成匹配评分 + 差距说明 + 简历优化建议
    ↓
进入模拟面试
    ↓
系统结合简历/JD/历史记录连续追问
    ↓
生成项目话术 + 面试总评 + 薄弱点分析
    ↓
保存历史记录并进入下一轮改进
```

### 4.2 简历解析流程

```text
用户上传 PDF
    ↓
后端校验文件大小、类型、页数
    ↓
文本层抽取（优先）
    ↓
若文本质量差 -> OCR 兜底
    ↓
结构化抽取（教育、经历、项目、技能、证书）
    ↓
结果置信度检查
    ↓
写入 structured_json
    ↓
前端展示“待确认”结果
    ↓
用户修订后保存为当前简历版本
```

### 4.3 JD 匹配与优化流程

```text
输入 JD
    ↓
结构化抽取岗位要求
    ↓
规则引擎计算骨架分
    ↓
模型生成差距解释与证据引用
    ↓
输出综合评分
    ↓
派生简历优化建议
    ↓
记录 Prompt 版本、模型版本、评分依据
```

### 4.4 模拟面试流程

```text
用户选择面试模式
    ↓
系统创建会话 thread_id
    ↓
根据 JD / 简历 / 历史记录构造检索查询
    ↓
混合检索 + 重排
    ↓
面试官问题流式输出
    ↓
用户作答
    ↓
系统做追问、实时记录、局部评分
    ↓
达到结束条件后生成总评
    ↓
保存会话与可执行改进建议
```

---

## 五、API 时序图

### 5.1 简历上传与解析时序

```text
浏览器          前端应用           API 服务            文件存储          数据库
  │                │                  │                  │               │
  │──选择 PDF─────▶│                  │                  │               │
  │                │──上传请求───────▶│                  │               │
  │                │                  │──保存文件──────▶│               │
  │                │                  │◀──文件 URL──────│               │
  │                │                  │──解析 PDF/OCR    │               │
  │                │                  │──写入 resumes ──────────────────▶│
  │                │                  │◀──────────────保存成功───────────│
  │                │◀──结构化结果────│                  │               │
  │◀──展示可编辑结果│                  │                  │               │
```

### 5.2 流式模拟面试时序

```text
浏览器         前端应用          API 服务         检索层/pgvector      大模型
  │               │                 │                  │               │
  │──发送回答────▶│                 │                  │               │
  │               │──POST /chat────▶│                  │               │
  │               │                 │──构造检索查询───▶│               │
  │               │                 │◀──返回命中片段──│               │
  │               │                 │──组装上下文──────────────────────▶│
  │               │◀──SSE token────│                  │◀──流式输出────│
  │◀──逐字展示────│                 │                  │               │
  │               │                 │──保存轮次/日志───────────────────▶│
```

---

## 六、后端技术选型与本地开发落地评估

### 6.1 后端完整技术清单

| 技术层 | 技术方案 | 作用 | 选型原因 |
|------|------|------|------|
| Web API | FastAPI + Uvicorn | 提供 HTTP API、SSE、WebSocket | 适合异步接口、流式输出和 AI 场景 |
| 输入输出校验 | Pydantic | 请求响应模型定义 | 与 FastAPI 深度集成，便于结构化输出 |
| ORM / 迁移 | SQLAlchemy 2.x + Alembic | 数据访问与数据库迁移 | 适合复杂查询、日志、评测和报告类数据 |
| 主数据库 | PostgreSQL 16+ | 业务主库 | JSONB、事务和扩展生态成熟 |
| 向量检索 | pgvector | 向量存储与相似度检索 | 与 PostgreSQL 共栈，维护成本低 |
| 缓存 / 状态 | Redis | 会话缓存、限流、任务状态 | 适合多轮会话与高频请求保护 |
| PDF 文本提取 | PyMuPDF | 简历文本抽取 | 文本型 PDF 解析效率高 |
| OCR 兜底 | OCRmyPDF + Tesseract | 扫描版 PDF 识别 | 用于纯图片型简历补救 |
| AI 编排 | LangGraph | 多轮面试、状态持久化、节点编排 | 适合面试追问与会话管理 |
| 模型适配 | OpenAI-compatible client | 接入第三方大模型 API | 便于切换供应商，避免强绑定 |
| 检索增强 | 向量召回 + 全文检索 + 重排 | 提升 RAG 命中率 | JD / 简历场景单一向量检索不够稳 |
| 后台任务 | FastAPI BackgroundTasks（V1） | 轻量异步任务 | 先低复杂度落地，后续再升级任务队列 |
| 评测体系 | LangSmith / 自建评测脚本 | 跑四类核心指标 | 支撑效果回归与版本对比 |
| 日志观测 | Structured Logging + Request ID | 问题排查与链路追踪 | 保证模型调用、检索、评分可追踪 |

### 6.2 后端模块拆分建议

- `apps/api/app/api`：路由层，按 `auth / resumes / jobs / reports / interviews / evaluations` 拆分。
- `apps/api/app/services`：业务服务层，负责解析、匹配、优化、话术和评分。
- `apps/api/app/agents`：LangGraph 节点和多轮会话编排。
- `apps/api/app/retrieval`：分片、嵌入、召回、重排、证据引用整合。
- `apps/api/app/models`：SQLAlchemy 模型。
- `apps/api/app/schemas`：Pydantic 请求响应模型。
- `apps/api/app/clients`：模型、对象存储、OCR、评测平台等第三方适配器。
- `apps/api/app/tasks`：后台任务封装，V1 先接 FastAPI BackgroundTasks。

### 6.3 各模块技术说明

#### 6.3.1 鉴权与用户系统

- 采用 `JWT Access Token + Refresh Token`。
- 登录、刷新、登出、当前用户接口统一由 `auth` 模块管理。
- 密码哈希使用 `bcrypt` 或等效安全方案。
- 登录、上传、面试对话接口都需要限流。

#### 6.3.2 简历解析链路

- 第一层：使用 PyMuPDF 抽取 PDF 文本。
- 第二层：做文本质量判断，如字符密度、空白比例、字段命中率。
- 第三层：若判断为扫描版简历，则进入 OCRmyPDF / Tesseract。
- 第四层：将抽取文本送入结构化 Prompt，生成标准 JSON。
- 第五层：前端提供人工校正页，保证后续 JD 匹配和面试环节使用的是确认后的数据。

#### 6.3.3 JD 匹配与简历优化

- 先将 JD 结构化，提取技能要求、经验年限、职责和加分项。
- 评分采用“规则骨架分 + 模型解释分”双层设计。
- 差距项和优化建议都必须绑定证据字段。
- 所有报告都记录 Prompt 版本、模型版本和评分依据。

#### 6.3.4 RAG 与模拟面试

- 知识来源优先级：`用户简历 > 目标 JD > 历史面试记录 > 评分 rubric`。
- 检索链路采用 `召回 -> 重排 -> 引用 -> 生成`。
- 会话状态通过 LangGraph `thread_id` 持久化。
- 输出方式优先采用 SSE；若后续需要更复杂实时交互，再补 WebSocket。

#### 6.3.5 评分与评测

- 单轮评分与面试总评共享一套评分 rubric。
- 所有评分都要回指证据句，避免“黑箱打分”。
- 每次调整 Prompt、检索策略或评分规则后，都要跑离线评测。
- `evaluation_runs` 表负责留痕不同版本评测结果。

### 6.4 可参考项目与借鉴意义

| 参考项目 | 借鉴点 | 对《职点迷津》的意义 |
|------|------|------|
| agent-service-toolkit | LangGraph + FastAPI + 流式接口 + Docker | 可参考后端骨架与 AI 编排方式 |
| Onyx | 混合检索、知识库治理、RAG 工程化 | 可参考检索链路和 RAG 评测思路 |
| Open WebUI | 本地 RAG、会话管理、观测能力 | 可参考多轮交互和历史记录管理 |

### 6.5 本地开发电脑评估结果

**检查时间**：2026-03-13  
**检查对象**：当前开发机器MacBook Air M4

| 项目 | 结果 |
|------|------|
| 芯片架构 | Apple M4 / arm64 |
| 内存 | 16 GB |
| 系统版本 | macOS 15.7.3 |
| Node.js | v22.17.0 |
| npm | 10.9.2 |
| Python | 3.13.9 |
| Docker CLI | 已安装 |
| Docker daemon | 未启动 |
| uv | 未安装 |
| pnpm | 未安装 |
| Homebrew | 未安装 |
| psql | 未安装 |
| redis-server | 未安装 |

### 6.6 本机是否可以完整落地

结论：**可以完整开发、完整联调、完整演示，但建议采用“本地基础设施 + 云端主模型”的方案。**

#### 可以完成的内容

- 本地运行 FastAPI、Next.js、PostgreSQL、pgvector、Redis、MinIO
- 本地完成 PDF 上传、解析、RAG 检索、流式对话、评测回归
- 本地完成作品集演示和节点开发测试

#### 不建议作为主方案的内容

- 不建议长期把主聊天模型、嵌入模型、重排模型都本地化部署在 16GB Air 上
- 不建议在开发时同时跑重型本地模型、OCR、大量 Docker 服务和前后端全量 watch

#### 工程判断

- 对于远程大模型 API 方案，这台机器完全够用。
- 对于小模型实验，这台机器可以做，但应控制在轻量级实验范围。
- 对于正式开发主线，应优先把算力压力放在云端模型服务上，本地专注业务、检索、评测和交互链路。

### 6.7 本地落地推荐方案

#### 推荐方案 A：正式开发主方案

- 本地运行：`Next.js + FastAPI + PostgreSQL + pgvector + Redis + MinIO`
- 云端运行：`主聊天模型 + embedding + rerank`
- 适用场景：最稳、最适合长期开发

#### 推荐方案 B：半本地实验方案

- 本地运行：基础设施 + 前后端 + 小型本地模型
- 云端运行：较重模型或关键评测任务
- 适用场景：验证本地模型替代可行性

#### 不推荐方案 C：全本地重模型方案

- 原因：16GB 无风扇笔记本长期高负载体验差，开发效率和稳定性都会受影响

### 6.8 本地开工前必须补齐的环境

1. 启动 Docker Desktop，确保 daemon 可用。
2. 安装 `uv`，用于 Python 依赖管理。
3. 安装 `pnpm`，用于前端包管理。
4. 建议安装 Homebrew，便于补齐系统依赖。
5. 项目 Python 版本建议固定为 `3.11`，不要直接以系统 `3.13` 作为正式开发环境。

### 6.9 本节结论

《职点迷津》的后端技术路线已经具备完整落地条件。对当前这台 `MacBook Air M4` 而言，硬件不是主要障碍，真正的关键在于：

1. 采用正确的后端分层和统一模型适配设计。
2. 避免把所有算力工作都压在本地。
3. 尽快补齐 Docker、uv、pnpm 等开发环境。

因此，本项目完全适合在当前电脑上从 0 到 1 开发，并完成作品级交付。

---

## 七、环境配置

### 7.1 环境要求

| 软件 | 最低版本 | 推荐版本 | 说明 |
|------|----------|----------|------|
| Node.js | 20 | LTS | Web 前端运行环境 |
| pnpm | 9 | 最新稳定版 | 前端包管理器 |
| Python | 3.11 | 3.11+ | API 服务运行环境 |
| uv | 0.4+ | 最新稳定版 | Python 依赖管理 |
| PostgreSQL | 16 | 16+ | 主数据库 |
| Redis | 7 | 7+ | 缓存与限流 |
| Docker | 24 | 最新稳定版 | 本地基础服务与容器化 |
| MinIO | 最新稳定版 | 最新稳定版 | 本地对象存储 |

### 7.2 环境变量完整说明

```bash
# ================================
# 通用配置
# ================================
APP_ENV=development
APP_NAME=career-pilot
WEB_BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO

# ================================
# 数据库与缓存
# ================================
DATABASE_URL=postgresql://career:career@localhost:5432/career_pilot
REDIS_URL=redis://localhost:6379/0

# ================================
# 鉴权配置
# ================================
JWT_SECRET=change-this-to-a-random-64-byte-secret
JWT_EXPIRES_IN=7d
REFRESH_TOKEN_EXPIRES_IN=30d

# ================================
# 文件与对象存储
# ================================
STORAGE_PROVIDER=minio
STORAGE_ENDPOINT=http://localhost:9000
STORAGE_BUCKET=career-pilot
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin
MAX_PDF_SIZE_MB=10

# ================================
# 模型与嵌入
# ================================
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://your-provider.example.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-chat-model
EMBEDDING_MODEL=your-embedding-model
RERANK_MODEL=your-rerank-model

# ================================
# RAG 与评测
# ================================
TOP_K=5
RETRIEVAL_SCORE_THRESHOLD=0.65
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
EVAL_DATASET_DIR=./docs/benchmarks

# ================================
# OCR（按需）
# ================================
OCR_PROVIDER=local
OCR_LANG=zh,en

# ================================
# 风控与限流
# ================================
RATE_LIMIT_PER_MINUTE=60
LOGIN_MAX_RETRY=5
```

### 7.3 本地开发启动步骤（规划版）

```bash
# 1. 安装前端依赖
cd apps/web
pnpm install

# 2. 安装后端依赖
cd ../api
uv sync

# 3. 启动基础服务
cd ../../
docker compose up -d postgres redis minio

# 4. 配置环境变量
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local

# 5. 初始化数据库
cd apps/api
uv run alembic upgrade head

# 6. 启动 API
uv run fastapi dev app/main.py --host 0.0.0.0 --port 8000

# 7. 启动 Web
cd ../web
pnpm dev

# 8. 验证成功标志
# Web: http://localhost:3000
# API: http://localhost:8000/health 返回 {"status":"ok"}
```

---

## 八、第三方服务配置

### 8.1 大模型服务

**用途**：结构化抽取、差距解释、面试追问、项目话术生成、总评总结  
**建议策略**：

1. 设计统一 `LLMClient` 接口，便于切换供应商。
2. 至少准备 1 个主模型和 1 个降级模型。
3. 所有模型调用都记录模块名、Prompt 版本、耗时、token 成本。

### 8.2 对象存储

**用途**：保存原始简历 PDF、导出的分析报告  
**建议策略**：

1. 本地开发使用 MinIO。
2. 生产环境切换到兼容 S3 的云存储。
3. 文件 URL 不直接暴露公网真实路径，统一通过签名访问。

### 8.3 评测平台

**用途**：比较不同 Prompt、检索策略和评分逻辑的效果  
**建议策略**：

1. 可以接入 LangSmith 做评测追踪。
2. 若不接第三方，至少保留自建评测脚本与 `evaluation_runs` 表。
3. 每次更新核心 Prompt 都必须跑一次离线回归。

---

## 九、错误码对照表

| 错误码 | HTTP 状态 | 含义 | 前端处理建议 |
|--------|----------|------|-------------|
| 20000 | 200 | 成功 | 正常展示数据 |
| 40001 | 400 | 请求参数错误 | 标红错误字段并提示修正 |
| 40101 | 401 | 未登录或 Token 失效 | 清空登录态并跳转登录页 |
| 40301 | 403 | 权限不足 | 显示无权限提示 |
| 40401 | 404 | 资源不存在 | 显示资源不存在 |
| 40901 | 409 | 数据冲突 | 显示冲突原因，如邮箱已存在 |
| 41301 | 413 | PDF 文件过大 | 提示压缩文件或重新上传 |
| 42201 | 422 | 简历解析失败 | 提示用户改传清晰 PDF 或手动补充 |
| 42202 | 422 | JD 结构化失败 | 提示检查 JD 文本完整性 |
| 42901 | 429 | 请求过于频繁 | 提示稍后再试 |
| 50001 | 500 | 系统内部错误 | 展示通用错误，记录日志 |
| 50002 | 500 | 模型服务异常 | 提示稍后重试并切换降级模型 |
| 50003 | 500 | 检索服务异常 | 提示进入无 RAG 降级模式 |

---

## 十、性能预期与压测基准

### 10.1 V1 性能目标

- 登录接口 P95 < 500ms
- JD 匹配报告首屏返回 P95 < 8s
- 简历解析完成时间：文本型 PDF P95 < 12s，OCR 型 PDF P95 < 25s
- 模拟面试首 Token 延迟 P95 < 3s
- 单轮面试回答结束后总评生成 P95 < 10s
- 检索链路 P95 < 800ms
- 支持 50 个并发在线面试会话

### 10.2 压测基线

- 样本库：100 份简历、100 条 JD、300 条检索问题、100 场面试脚本
- 压测场景 1：20 用户同时上传 PDF
- 压测场景 2：50 用户同时发起面试对话
- 压测场景 3：批量跑 200 组离线匹配评测

---

## 十一、安全检查清单

```text
【认证安全】
✅/⬜ 密码使用 bcrypt 或等效安全哈希
✅/⬜ JWT Secret 长度足够
✅/⬜ Refresh Token 可吊销

【输入安全】
✅/⬜ 所有字段服务端校验
✅/⬜ PDF 类型和大小限制
✅/⬜ 富文本输出做 XSS 防护
✅/⬜ SQL 使用参数化查询

【AI 安全】
✅/⬜ Prompt 注入风险过滤
✅/⬜ 检索结果只允许来自可信来源
✅/⬜ 模型输出落地前做结构校验
✅/⬜ 敏感个人信息不写入训练或公开日志

【数据安全】
✅/⬜ 原始简历文件支持删除
✅/⬜ PII 字段脱敏展示
✅/⬜ 生产环境关闭调试模式
✅/⬜ 环境变量不提交 Git

【接口安全】
✅/⬜ 登录与聊天接口限流
✅/⬜ 文件上传鉴权
✅/⬜ 管理接口独立权限
✅/⬜ 错误日志不泄露模型密钥
```

---

## 十二、量化指标与评测方案

### 12.1 匹配准确度

- 指标定义：系统给出的岗位匹配结果与人工标注结果的一致程度。
- 评测集：200 组人工标注的“简历-JD”样本。
- 指标目标：
  - 四档匹配分类 `Accuracy >= 80%`
  - 0-100 匹配分 `MAE <= 8`
  - 差距项识别命中率 `>= 75%`

### 12.2 检索命中率

- 指标定义：RAG 检索到的文档是否覆盖标准答案所需上下文。
- 评测集：300 条检索问题，带标准命中片段标注。
- 指标目标：
  - `Recall@5 >= 85%`
  - `MRR >= 0.75`
  - 错误引用率 `< 10%`

### 12.3 回答质量

- 指标定义：面试问题回答是否相关、具体、结构清晰、贴合岗位。
- 评测集：100 场模拟面试，含标准问法与人工评分样本。
- 指标目标：
  - 平均质量分 `>= 4.2/5`
  - 跑题率 `< 8%`
  - 人工抽检通过率 `>= 85%`

### 12.4 评分逻辑

- 总分 `100`
- 维度建议：
  - 岗位理解 `20`
  - 经历相关性 `20`
  - 技术深度 `20`
  - 结果量化 `15`
  - 表达结构 `15`
  - 追问应对 `10`
- 要求：
  - 每一项必须有证据片段
  - 相同回答重复评分标准差 `<= 5`
  - 所有评分规则写入 `packages/shared` 并版本化

---

## 十三、模块开发规划

### 【第一阶段：基础架构】

- [ ] 节点 1：项目脚手架、目录结构、Docker、本地基础服务
- [ ] 节点 2：用户系统、JWT 鉴权、基础页面框架
- [ ] 节点 3：对象存储、PDF 上传、日志与监控基础设施

### 【第二阶段：核心闭环】

- [ ] 节点 4：简历 PDF 解析、结构化抽取、人工校正页
- [ ] 节点 5：JD 结构化、匹配评分、差距说明
- [ ] 节点 6：简历优化建议、项目话术生成

### 【第三阶段：AI 面试引擎】

- [ ] 节点 7：RAG 检索、会话状态、流式面试、多轮追问
- [ ] 节点 8：面试总评、历史记录、薄弱点分析、指标看板

### 节点验收总原则

1. 每个节点完成后必须补文档、补测试、补指标。
2. 任一 AI 模块上线前必须有离线评测结果。
3. 任一评分逻辑上线前必须能解释其依据。

---

## 十四、开发节点记录

### 节点 0：项目规划与第一版开发文档

| 字段 | 内容 |
|------|------|
| 完成时间 | 2026-03-13 |
| 负责 Agent | 主控 Agent |
| Git 提交 | N/A |
| 提交哈希 | N/A |
| 测试状态 | N/A |

**完成内容：**

- 明确《职点迷津》产品定位、V1 范围和量化指标
- 吸纳垂类 AI 产品方法论并转化为项目原则
- 产出第一版系统架构、数据模型、流程图和开发节点

**交付文件：**

```text
DEV_DOCUMENT.md
```

**遇到的问题：**

- 具体模型供应商尚未最终锁定
- 评测集标注样本仍需在开发前补齐

**解决方案：**

- 先采用统一模型适配层设计
- 在节点 4 前先补齐 50 组最小评测样本，再逐步扩充

---

## 十五、Git 提交历史

| 时间 | 提交信息 | 节点 | 负责 | 测试 |
|------|----------|------|------|------|
| 2026-03-13 | 文档初始化：输出《职点迷津》第一版开发文档 | 节点 0 | 主控 Agent | N/A |

---

## 十六、最终交付物

《职点迷津》的最终交付物 = 一个可上线演示的 AI 求职产品 + 一套可量化验证的 AI 能力体系 + 一份可复用扩展的工程资产。

可运行的产品本体
一个真正能用的 Web 网页应用
覆盖 6 大核心模块
支持注册登录、PDF 上传、流式面试、多轮会话、历史复盘
完整的 AI 业务闭环
从“上传简历”到“岗位匹配”到“模拟面试”到“复盘改进”全链路跑通
不是单点功能演示，而是用户真的能完成一次求职训练流程
可量化的评测结果
匹配准确度
检索命中率
回答质量
评分逻辑稳定性
这 4 项必须有数据、有样本集、有报告，证明系统不是“看起来能用”，而是“经验证可用”
完整工程文档
开发文档：DEV_DOCUMENT.md
API 文档
风格规范文档
部署说明
环境变量说明
