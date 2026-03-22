# Career Pilot 安装与配置指南

[English](SETUP.md) | [Español](SETUP.es.md) | [**简体中文**](SETUP.zh-CN.md) | [日本語](SETUP.ja.md)

欢迎！本指南将带你在本地完成 Career Pilot 的安装与配置。Career Pilot 是一个面向中高级开发者的智能求职工作台，通过 AI 赋能实现简历智能解析、岗位精准匹配、能力短板分析与简历优化建议生成。

无论你是想参与开发，还是只想在本机运行应用，都可以按本文档完成上手。

---

## 目录

- [前置条件](#prerequisites)
- [快速开始](#quick-start)
- [逐步安装](#step-by-step-setup)
  - [1. 克隆仓库](#1-clone-the-repository)
  - [2. 后端配置](#2-backend-setup)
  - [3. 前端配置](#3-frontend-setup)
- [配置 AI 提供商](#configuring-your-ai-provider)
  - [选项 A：云端提供商](#option-a-cloud-providers)
  - [选项 B：使用本地大模型代理](#option-b-local-ai-proxy)
- [Docker 部署](#docker-deployment)
- [访问应用](#accessing-the-application)
- [常用命令速查](#common-commands-reference)
- [故障排查](#troubleshooting)
- [项目结构概览](#project-structure-overview)
- [获取帮助](#getting-help)

---

<a id="prerequisites"></a>

## 前置条件

开始前请确保系统已安装以下工具：

| 工具        | 最低版本 | 如何检查           | 安装                                                                    |
| ----------- | -------- | ------------------ | ----------------------------------------------------------------------- |
| **Python**  | 3.11.15  | `python --version` | [python.org](https://python.org)                                        |
| **Node.js** | 20+      | `node --version`   | [nodejs.org](https://nodejs.org)                                        |
| **npm**     | 10+      | `npm --version`    | 随 Node.js 一起安装                                                     |
| **uv**      | 最新     | `uv --version`     | [astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| **Git**     | 任意     | `git --version`    | [git-scm.com](https://git-scm.com)                                      |

### 安装 uv（Python 包管理器）

Career Pilot 使用 `uv` 来实现更快、更稳定的 Python 依赖管理。可通过以下方式安装：

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或通过 pip
pip install uv
```

---

<a id="quick-start"></a>

## 快速开始

如果你对开发工具比较熟悉，想快速跑起来：

```bash
# 1. 克隆仓库
git clone https://gitee.com/zwz050418/career-pilot.git
cd career-pilot

# 2. 启动依赖服务（PostgreSQL、Redis、MinIO）
docker compose -f docker-compose.yml up -d postgres redis minio

# 3. 启动后端（终端 1）
cd apps/backend
cp .env.example .env        # 从模板创建配置
uv sync                      # 安装 Python 依赖
uv run alembic upgrade head  # 执行数据库迁移
uv run uvicorn app.main:app --reload --port 8000

# 4. 启动前端（终端 2）
cd apps/frontend
npm install                  # 安装 Node.js 依赖
npm run dev                  # 启动开发服务器
```

浏览器打开 **<http://localhost:3000>** 即可。

> **注意：** 使用应用前需要先配置 AI 提供商。见下方 [配置 AI 提供商](#configuring-your-ai-provider)。

---

<a id="step-by-step-setup"></a>

## 逐步安装

<a id="1-clone-the-repository"></a>

### 1. 克隆仓库

先把代码拉到本机：

```bash
git clone https://gitee.com/zwz050418/career-pilot.git
cd career-pilot
```

<a id="2-backend-setup"></a>

### 2. 后端配置

后端是 Python FastAPI 应用，负责 AI 调用、简历解析、岗位匹配以及数据存储。

#### 进入后端目录

```bash
cd apps/backend
```

#### 创建环境变量文件

```bash
cp .env.example .env
```

#### 使用你偏好的编辑器编辑 `.env`

```bash
# macOS/Linux
nano .env

# 或使用任意编辑器
code .env   # VS Code
```

关键配置项说明：

```env
# 数据库（PostgreSQL）
DATABASE_URL=postgresql+asyncpg://career:career@localhost:5432/career_pilot
ALEMBIC_DATABASE_URL=postgresql+psycopg://career:career@localhost:5432/career_pilot

# Redis（缓存、Token Blocklist）
REDIS_URL=redis://localhost:6380/0

# 对象存储（MinIO，用于存储简历 PDF）
STORAGE_PROVIDER=minio
STORAGE_ENDPOINT=localhost:9000
STORAGE_ACCESS_KEY=careerpilot
STORAGE_SECRET_KEY=careerpilot123
STORAGE_BUCKET_NAME=career-pilot-resumes

# JWT 认证
JWT_SECRET_KEY=replace-this-with-a-very-long-dev-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS
CORS_ORIGINS=http://localhost:3000

# AI 服务配置（简历解析与校正）
RESUME_AI_PROVIDER=minimax
RESUME_AI_BASE_URL=https://api.minimaxi.com/anthropic
RESUME_AI_API_KEY=your_api_key_here
RESUME_AI_MODEL=MiniMax-M2.5
RESUME_AI_TIMEOUT_SECONDS=30

# AI 服务配置（岗位匹配）
MATCH_AI_PROVIDER=minimax
MATCH_AI_BASE_URL=https://api.minimaxi.com/anthropic
MATCH_AI_API_KEY=your_api_key_here
MATCH_AI_MODEL=MiniMax-M2.5
MATCH_AI_TIMEOUT_SECONDS=90
```

#### 安装 Python 依赖

```bash
uv sync
```

该命令会创建虚拟环境并安装所有必需依赖，包括：

- FastAPI（Web 框架）
- SQLAlchemy（ORM）
- Alembic（数据库迁移）
- MinIO（对象存储客户端）
- Pypdf（PDF 解析）
- Anthropic（AI 客户端）

#### 启动数据库迁移

```bash
uv run alembic upgrade head
```

该命令会创建或更新数据库表结构。

#### 启动后端服务

```bash
uv run uvicorn app.main:app --reload --port 8000
```

你会看到类似输出：

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**保持该终端运行**，然后为前端另开一个终端窗口。

<a id="3-frontend-setup"></a>

### 3. 前端配置

前端是 Next.js 应用，提供用户界面。

#### 进入前端目录

```bash
cd apps/frontend
```

#### （可选）创建前端环境变量文件

仅当你的后端运行在不同端口时需要：

```bash
cp .env.example .env.local
```

#### 安装 Node.js 依赖

```bash
npm install
```

该命令会安装所有必需依赖，包括：

- Next.js 16（SSR/静态生成框架）
- React 19（UI 框架）
- TypeScript（类型安全）
- Tailwind CSS 4（原子化 CSS）
- shadcn/ui（组件库）

#### 启动开发服务器

```bash
npm run dev
```

你会看到：

```
▲ Next.js 16.1.6 (Turbopack)
- Local:        http://localhost:3000
- Network:      http://192.168.x.x:3000
```

浏览器打开 **<http://localhost:3000>**，你应该能看到 Career Pilot 的界面。

---

<a id="configuring-your-ai-provider"></a>

## 配置 AI 提供商

Career Pilot 支持多种 AI 提供商。你可以在应用的设置页面中配置，也可以直接编辑后端的 `.env` 文件。

<a id="option-a-cloud-providers"></a>

### 选项 A：云端提供商

| 提供商         | 配置方式                                                          | 获取 API Key                                                |
| -------------- | ----------------------------------------------------------------- | ----------------------------------------------------------- |
| **Anthropic**  | `RESUME_AI_PROVIDER=anthropic`<br>`MATCH_AI_PROVIDER=anthropic`   | [console.anthropic.com](https://console.anthropic.com/)     |
| **OpenAI**     | `RESUME_AI_PROVIDER=openai`<br>`MATCH_AI_PROVIDER=openai`         | [platform.openai.com](https://platform.openai.com/api-keys) |
| **MiniMax**    | `RESUME_AI_PROVIDER=minimax`<br>`MATCH_AI_PROVIDER=minimax`       | [api.minimaxi.com](https://api.minimaxi.com/)               |
| **DeepSeek**   | `RESUME_AI_PROVIDER=deepseek`<br>`MATCH_AI_PROVIDER=deepseek`     | [platform.deepseek.com](https://platform.deepseek.com/)     |
| **OpenRouter** | `RESUME_AI_PROVIDER=openrouter`<br>`MATCH_AI_PROVIDER=openrouter` | [openrouter.ai](https://openrouter.ai/keys)                 |

Anthropic 的 `.env` 示例：

```env
RESUME_AI_PROVIDER=anthropic
RESUME_AI_BASE_URL=https://api.anthropic.com/v1
RESUME_AI_API_KEY=sk-ant-your-key-here
RESUME_AI_MODEL=claude-3-5-sonnet-20241022
RESUME_AI_TIMEOUT_SECONDS=30

MATCH_AI_PROVIDER=anthropic
MATCH_AI_BASE_URL=https://api.anthropic.com/v1
MATCH_AI_API_KEY=sk-ant-your-key-here
MATCH_AI_MODEL=claude-3-5-sonnet-20241022
MATCH_AI_TIMEOUT_SECONDS=90
```

<a id="option-b-local-ai-proxy"></a>

### 选项 B：使用本地大模型代理（免费）

想在本机运行模型、避免 API 费用？可以使用 `scripts/codex2gpt/` 代理本地大模型。

#### 第 1 步：启动本地大模型代理

```bash
# 确保代理脚本可执行
python scripts/codex2gpt/server.py
```

#### 第 2 步：配置 `.env`

```env
RESUME_AI_PROVIDER=openai-compatible
RESUME_AI_BASE_URL=http://localhost:8001/v1
RESUME_AI_API_KEY=dummy-key
RESUME_AI_MODEL=local-model-name
RESUME_AI_TIMEOUT_SECONDS=30

MATCH_AI_PROVIDER=openai-compatible
MATCH_AI_BASE_URL=http://localhost:8001/v1
MATCH_AI_API_KEY=dummy-key
MATCH_AI_MODEL=local-model-name
MATCH_AI_TIMEOUT_SECONDS=90
```

#### 第 3 步：确保代理正在运行

```bash
curl http://localhost:8001/models
```

你应该能看到可用的模型列表。

---

<a id="docker-deployment"></a>

## Docker 部署

如果你更喜欢容器化部署，Career Pilot 已提供完整的 Docker 支持。

### 使用 Docker Compose（推荐）

```bash
# 构建并启动所有服务
docker compose -f docker-compose.yml up -d

# 查看服务状态
docker compose -f docker-compose.yml ps

# 查看日志
docker compose -f docker-compose.yml logs -f
```

### Docker 重要说明

- **环境变量通过 `.env` 文件配置**：编辑 `apps/backend/.env` 文件
- **数据库持久化**：数据保存在 Docker volume 中（`career-pilot-postgres-data`）
- **MinIO 控制台**：访问 http://localhost:9001 查看对象存储
- **服务依赖**：后端会等待 PostgreSQL、Redis、MinIO 启动完成后再启动

### 停止容器

```bash
docker compose -f docker-compose.yml down
```

### 重新构建镜像

```bash
docker compose -f docker-compose.yml up -d --build
```

---

<a id="accessing-the-application"></a>

## 访问应用

当后端与前端都启动后，可通过以下地址访问：

| URL                                | 说明                |
| ---------------------------------- | ------------------- |
| **<http://localhost:3000>**        | 主应用（Dashboard） |
| **<http://localhost:8000>**        | 后端 API 根路径     |
| **<http://localhost:8000/docs>**   | 可交互的 API 文档   |
| **<http://localhost:8000/health>** | 后端健康检查        |
| **<http://localhost:9001>**        | MinIO 控制台        |

### 首次配置检查清单

1. 打开 <http://localhost:3000>
2. 点击顶部导航的 "简历" 进入简历管理页面
3. 上传你的第一份 PDF 简历
4. 等待解析完成（可在后端日志中查看进度）
5. 查看解析结果并进行编辑

---

<a id="common-commands-reference"></a>

## 常用命令速查

### 后端命令

```bash
cd apps/backend

# 启动开发服务器（自动热重载）
uv run uvicorn app.main:app --reload --port 8000

# 启动生产服务器
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 安装依赖
uv sync

# 安装开发依赖（用于测试）
uv sync --group dev

# 运行测试
uv run pytest

# 运行特定测试文件
uv run pytest tests/test_resume.py
uv run pytest tests/test_match_reports.py

# 代码检查
uv run ruff check .
uv run ruff format .

# 数据库迁移
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"

# 查看服务状态
docker compose -f ../docker-compose.yml ps
```

### 前端命令

```bash
cd apps/frontend

# 启动开发服务器（Turbopack 快速刷新）
npm run dev

# 生产构建
npm run build

# 启动生产服务器
npm run start

# 运行 linter
npm run lint

# 指定其他端口运行
npm run dev -- -p 3001
```

### Docker 命令

```bash
# 查看所有服务状态
docker compose -f docker-compose.yml ps

# 查看特定服务日志
docker compose -f docker-compose.yml logs -f backend
docker compose -f docker-compose.yml logs -f frontend

# 停止所有服务
docker compose -f docker-compose.yml down

# 停止并删除数据卷
docker compose -f docker-compose.yml down -v

# 重新构建镜像
docker compose -f docker-compose.yml up -d --build
```

---

<a id="troubleshooting"></a>

## 故障排查

### 后端无法启动

**错误：** `ModuleNotFoundError`

确认使用 `uv` 启动：

```bash
uv run uvicorn app.main:app --reload
```

**错误：** `Database connection failed`

检查 PostgreSQL 是否运行：

```bash
docker compose -f docker-compose.yml ps postgres
docker compose -f docker-compose.yml logs postgres
```

**错误：** `Redis connection failed`

检查 Redis 是否运行：

```bash
docker compose -f docker-compose.yml ps redis
docker compose -f docker-compose.yml logs redis
```

**错误：** `MinIO connection failed`

检查 MinIO 是否运行：

```bash
docker compose -f docker-compose.yml ps minio
docker compose -f docker-compose.yml logs minio
```

**错误：** `JWT_SECRET_KEY not configured`

检查 `.env` 文件中的 `JWT_SECRET_KEY` 是否已配置：

```env
JWT_SECRET_KEY=your-very-long-secret-key-here
```

### 前端无法启动

**错误：** 页面加载时报 `ECONNREFUSED`

后端未运行，请先启动后端：

```bash
cd apps/backend && uv run uvicorn app.main:app --reload
```

**错误：** 构建或 TypeScript 报错

清理 Next.js 缓存：

```bash
rm -rf apps/frontend/.next
npm run dev
```

### PDF 解析失败

**错误：** `Failed to extract text from PDF`

1. 检查 PDF 文件是否损坏
2. 确认 MinIO 正在运行
3. 查看后端日志中的详细错误信息

**错误：** `AI correction failed`

1. 检查 AI 提供商配置是否正确
2. 确认 API Key 有效
3. 查看后端日志中的详细错误信息

### 数据库迁移失败

**错误：** `Revision not found`

尝试回滚到最新迁移：

```bash
uv run alembic downgrade base
uv run alembic upgrade head
```

**错误：** `Duplicate column name`

检查迁移文件是否已应用：

```bash
uv run alembic current
```

### MinIO 访问失败

**错误：** `Connection refused to localhost:9000`

1. 确认 MinIO 在运行：`docker compose -f docker-compose.yml ps minio`
2. 检查 MinIO 日志：`docker compose -f docker-compose.yml logs minio`
3. 确认环境变量中的 `STORAGE_ENDPOINT` 与 MinIO 端口一致

---

<a id="project-structure-overview"></a>

## 项目结构概览

```text
career-pilot/
├── apps/
│   ├── backend/                      # FastAPI 后端服务
│   │   ├── app/
│   │   │   ├── core/                 # 核心配置
│   │   │   │   ├── config.py         # 配置管理
│   │   │   │   ├── errors.py         # 错误处理
│   │   │   │   ├── logging.py        # 日志配置
│   │   │   │   ├── responses.py      # 统一响应格式
│   │   │   │   └── security.py       # 安全工具（JWT、密码哈希）
│   │   │   ├── db/                   # 数据库层
│   │   │   │   ├── base.py           # SQLAlchemy 基础配置
│   │   │   │   └── session.py        # 数据库会话管理
│   │   │   ├── models/               # SQLAlchemy 数据模型
│   │   │   │   ├── user.py           # 用户模型
│   │   │   │   ├── user_profile.py   # 用户资料模型
│   │   │   │   ├── resume.py         # 简历模型
│   │   │   │   ├── resume_parse_job.py    # 简历解析任务
│   │   │   │   ├── job_description.py      # 岗位描述模型
│   │   │   │   ├── job_parse_job.py        # 岗位解析任务
│   │   │   │   ├── job_readiness_event.py  # 岗位准备事件
│   │   │   │   ├── match_report.py         # 匹配报告模型
│   │   │   │   ├── mock_interview_session.py  # 模拟面试会话
│   │   │   │   ├── mock_interview_turn.py     # 模拟面试轮次
│   │   │   │   ├── resume_optimization_session.py # 简历优化会话
│   │   │   │   └── mixins.py         # 公共模型混入
│   │   │   ├── routers/              # API 路由
│   │   │   │   ├── auth.py           # 认证路由
│   │   │   │   ├── deps.py           # 依赖注入
│   │   │   │   ├── health.py         # 健康检查
│   │   │   │   ├── profile.py        # 用户资料路由
│   │   │   │   ├── resumes.py        # 简历管理路由
│   │   │   │   ├── tailored_resumes.py    # 定制化简历路由
│   │   │   │   ├── resume_optimization.py # 简历优化路由
│   │   │   │   ├── jobs.py           # 岗位管理路由
│   │   │   │   ├── match_reports.py  # 匹配报告路由
│   │   │   │   └── mock_interviews.py     # 模拟面试路由
│   │   │   ├── schemas/              # Pydantic Schema
│   │   │   │   ├── auth.py           # 认证相关
│   │   │   │   ├── common.py         # 公共定义
│   │   │   │   ├── user.py           # 用户相关
│   │   │   │   ├── profile.py        # 资料相关
│   │   │   │   ├── resume.py         # 简历相关
│   │   │   │   ├── tailored_resume.py     # 定制化简历
│   │   │   │   ├── resume_optimization.py # 简历优化
│   │   │   │   ├── job.py            # 岗位相关
│   │   │   │   ├── match_report.py   # 匹配报告
│   │   │   │   ├── mock_interview.py # 模拟面试
│   │   │   │   └── system.py         # 系统信息
│   │   │   ├── services/             # 业务逻辑层
│   │   │   │   ├── ai_client.py      # AI 客户端统一封装
│   │   │   │   ├── auth.py           # 认证服务
│   │   │   │   ├── profile.py        # 用户资料服务
│   │   │   │   ├── resume.py         # 简历服务
│   │   │   │   ├── resume_parser.py  # 简历规则解析
│   │   │   │   ├── resume_ai.py      # AI 校正服务
│   │   │   │   ├── resume_markdown_renderer.py # Markdown 渲染
│   │   │   │   ├── tailored_resume.py          # 定制化简历服务
│   │   │   │   ├── tailored_resume_document_ai.py # 定制化文档 AI
│   │   │   │   ├── tailored_resume_grammar.py     # 定制化语法检查
│   │   │   │   ├── tailored_resume_polish.py      # 定制化润色
│   │   │   │   ├── resume_optimizer.py         # 简历优化服务
│   │   │   │   ├── resume_optimizer_ai.py      # 简历优化 AI
│   │   │   │   ├── job.py            # 岗位服务
│   │   │   │   ├── job_parser.py     # 岗位规则解析
│   │   │   │   ├── match_report.py   # 匹配报告服务
│   │   │   │   ├── match_engine.py   # 规则匹配引擎
│   │   │   │   ├── match_ai.py       # AI 匹配服务
│   │   │   │   ├── match_support.py  # 匹配支持工具
│   │   │   │   ├── mock_interview.py         # 模拟面试服务
│   │   │   │   ├── mock_interview_ai.py      # 模拟面试 AI
│   │   │   │   ├── storage.py        # 对象存储服务
│   │   │   │   └── token_blocklist.py        # Token 黑名单
│   │   │   ├── prompts/              # AI Prompt 模板
│   │   │   │   ├── resume/           # 简历解析 Prompt
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── import_extraction.txt
│   │   │   │   │   └── structure_correction.txt
│   │   │   │   ├── tailored_resume/  # 定制化简历 Prompt
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── full_document.txt
│   │   │   │   │   ├── rewrite_only.txt
│   │   │   │   │   ├── grammar_check.txt
│   │   │   │   │   └── polish_markdown.txt
│   │   │   │   ├── match/            # 匹配 Prompt
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── report_generation.txt
│   │   │   │   │   └── report_repair.txt
│   │   │   │   ├── mock_interview/   # 模拟面试 Prompt
│   │   │   │   │   ├── interview_final_review.txt
│   │   │   │   │   ├── interview_followup_decider.txt
│   │   │   │   │   ├── interview_plan_system.txt
│   │   │   │   │   ├── interview_turn_evaluator.txt
│   │   │   │   │   └── json_repair.txt
│   │   │   │   ├── __init__.py
│   │   │   │   ├── enrichment.py     # 内容增强
│   │   │   │   ├── mock_interview.py # 模拟面试系统提示
│   │   │   │   ├── refinement.py     # 内容精炼
│   │   │   │   └── templates.py      # Prompt 模板
│   │   │   └── main.py               # 应用入口
│   │   ├── alembic/                  # 数据库迁移
│   │   │   ├── env.py                # Alembic 配置
│   │   │   ├── script.py.mako        # 迁移文件模板
│   │   │   └── versions/             # 迁移历史
│   │   │       ├── 20260314_0001_create_users_table.py
│   │   │       ├── 20260314_0002_create_user_profiles_table.py
│   │   │       ├── 20260314_0003_create_resumes_tables.py
│   │   │       ├── 20260315_0004_create_jobs_and_match_reports_tables.py
│   │   │       ├── 20260316_0005_expand_job_matching_workflow.py
│   │   │       ├── 20260317_0006_create_resume_optimization_sessions_table.py
│   │   │       ├── 20260317_0007_add_ai_fields_to_resume_parse_jobs.py
│   │   │       ├── 20260318_0008_create_mock_interview_tables.py
│   │   │       ├── 20260320_0009_add_parse_artifacts_to_resumes.py
│   │   │       ├── 20260320_0010_expand_resume_optimization_sessions_outputs.py
│   │   │       └── 20260321_0011_add_tailored_resume_documents_to_sessions.py
│   │   ├── tests/                    # 测试用例
│   │   │   ├── conftest.py           # 测试配置
│   │   │   ├── test_resume_parser.py
│   │   │   ├── test_resume_ai.py
│   │   │   ├── test_resume_parse_flow.py
│   │   │   ├── test_resume.py
│   │   │   ├── test_resume_markdown_renderer.py
│   │   │   ├── test_tailored_resume_document_ai.py
│   │   │   ├── test_tailored_resume_grammar.py
│   │   │   ├── test_tailored_resume_polish.py
│   │   │   ├── test_tailored_resume_flow.py
│   │   │   ├── test_resume_optimizer_flow.py
│   │   │   ├── test_jobs_match_flow.py
│   │   │   ├── test_mock_interview_flow.py
│   │   │   ├── test_ai_client_json_parse.py
│   │   │   ├── test_jobs.py
│   │   │   └── test_match_reports.py
│   │   ├── .env.example              # 环境变量模板
│   │   ├── .gitignore
│   │   ├── Dockerfile
│   │   ├── alembic.ini
│   │   └── pyproject.toml            # Python 依赖配置
│   │
│   ├── frontend/                     # Next.js 前端
│   │   ├── src/
│   │   │   ├── app/                  # Next.js App Router
│   │   │   │   ├── (dashboard)/      # 仪表盘路由（带认证保护）
│   │   │   │   │   ├── dashboard/    # 各功能模块
│   │   │   │   │   │   ├── page.tsx  # 仪表盘首页
│   │   │   │   │   │   ├── overview/ # 概览
│   │   │   │   │   │   ├── resume/   # 简历管理
│   │   │   │   │   │   ├── jobs/     # 岗位管理
│   │   │   │   │   │   ├── optimizer/# 简历优化
│   │   │   │   │   │   ├── profile/  # 用户资料
│   │   │   │   │   │   ├── setting/  # 设置
│   │   │   │   │   │   ├── interviews/ # 模拟面试
│   │   │   │   │   │   └── applications/ # 投递管理
│   │   │   │   │   ├── layout.tsx    # 仪表盘布局
│   │   │   │   │   ├── loading.tsx   # 加载状态
│   │   │   │   │   ├── error.tsx     # 错误处理
│   │   │   │   ├── login/            # 登录页面
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── register/         # 注册页面
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── layout.tsx        # 根布局
│   │   │   │   ├── page.tsx          # 首页
│   │   │   │   ├── globals.css       # 全局样式
│   │   │   │   └── favicon.ico
│   │   │   ├── components/           # UI 组件
│   │   │   │   ├── guards/           # 路由守卫
│   │   │   │   │   ├── guest-route.tsx
│   │   │   │   │   └── protected-route.tsx
│   │   │   │   ├── layout/           # 布局组件
│   │   │   │   │   ├── app-sidebar.tsx
│   │   │   │   │   └── dashboard-top-nav.tsx
│   │   │   │   ├── brutalist/        # Brutalist 风格组件
│   │   │   │   │   ├── form-controls.tsx
│   │   │   │   │   └── page-shell.tsx
│   │   │   │   ├── dashboard/        # 仪表盘组件
│   │   │   │   │   └── dashboard-placeholder-page.tsx
│   │   │   │   ├── resume/           # 简历相关组件
│   │   │   │   │   ├── resume-structured-editor.tsx
│   │   │   │   │   └── status-meta.ts
│   │   │   │   ├── ui/               # UI 基础组件（shadcn/ui）
│   │   │   │   │   ├── alert.tsx
│   │   │   │   │   ├── badge.tsx
│   │   │   │   │   ├── button.tsx
│   │   │   │   │   ├── card.tsx
│   │   │   │   │   ├── input.tsx
│   │   │   │   │   ├── label.tsx
│   │   │   │   │   └── textarea.tsx
│   │   │   │   ├── auth-form.tsx
│   │   │   │   ├── auth-page.tsx
│   │   │   │   ├── auth-provider.tsx
│   │   │   │   └── page-state.tsx
│   │   │   ├── config/               # 配置文件
│   │   │   │   └── nav-config.ts
│   │   │   └── lib/                  # 工具库、API 客户端
│   │   │       ├── api/              # API 客户端
│   │   │       │   ├── client.ts
│   │   │       │   ├── contracts.ts
│   │   │       │   └── modules/      # 按模块划分的 API
│   │   │       │       ├── auth.ts
│   │   │       │       ├── profile.ts
│   │   │       │       ├── resume.ts
│   │   │       │       ├── jobs.ts
│   │   │       │       ├── optimizer.ts
│   │   │       │       ├── mock-interviews.ts
│   │   │       │       └── health.ts
│   │   │       ├── auth-storage.ts
│   │   │       └── utils.ts
│   │   ├── .env.example
│   │   ├── .gitignore
│   │   ├── Dockerfile
│   │   ├── components.json
│   │   ├── eslint.config.mjs
│   │   ├── next.config.ts
│   │   ├── package.json
│   │   ├── postcss.config.mjs
│   │   └── tsconfig.json
│   │
│   └── miniprogram/                  # 微信小程序
│       ├── pages/
│       │   └── index/
│       │       ├── index.js
│       │       ├── index.json
│       │       ├── index.wxml
│       │       └── index.wxss
│       ├── components/
│       │   └── navigation-bar/
│       │       ├── navigation-bar.js
│       │       ├── navigation-bar.json
│       │       ├── navigation-bar.wxml
│       │       └── navigation-bar.wxss
│       ├── app.js
│       ├── app.json
│       ├── app.wxss
│       ├── project.config.json
│       ├── project.private.config.json
│       ├── sitemap.json
│       └── .eslintrc.js
│
├── docker/                           # Docker 编排配置
│   └── start.sh                      # 本地开发启动脚本
│
├── monochrome/                       # Monochrome 主题配置
│   ├── monochrome-SKILL.md
│   ├── monochrome-globals.css
│   ├── monochrome-hard-prompt.md
│   ├── monochrome-meta.json
│   ├── monochrome-shadcn-theme.json
│   ├── monochrome-tailwind-preset.js
│   ├── monochrome-tokens.json
│   └── monochrome-variables.css
│
├── docker-compose.yml                # Docker Compose 配置
├── AGENTS.md                         # 代理工作规范
└── README.md                         # 项目说明
```

### 核心数据模型

| 模型                        | 说明                             |
| --------------------------- | -------------------------------- |
| `User`                      | 用户账户                         |
| `UserProfile`               | 用户资料（求职方向、目标城市等） |
| `Resume`                    | 简历（含解析结果）               |
| `ResumeParseJob`            | 简历解析任务                     |
| `JobDescription`            | 岗位描述                         |
| `JobParseJob`               | 岗位解析任务                     |
| `JobReadinessEvent`         | 岗位准备事件                     |
| `MatchReport`               | 匹配报告                         |
| `ResumeOptimizationSession` | 简历优化会话                     |
| `MockInterviewSession`      | 模拟面试会话                     |
| `MockInterviewTurn`         | 模拟面试轮次                     |

### API 路由

| 路由                       | 说明       |
| -------------------------- | ---------- |
| `/api/health`              | 健康检查   |
| `/api/auth/login`          | 登录       |
| `/api/auth/register`       | 注册       |
| `/api/auth/refresh`        | 刷新 Token |
| `/api/auth/logout`         | 登出       |
| `/api/profile`             | 用户资料   |
| `/api/resumes`             | 简历管理   |
| `/api/tailored-resumes`    | 定制化简历 |
| `/api/resume-optimization` | 简历优化   |
| `/api/jobs`                | 岗位管理   |
| `/api/match-reports`       | 匹配报告   |
| `/api/mock-interviews`     | 模拟面试   |

---
