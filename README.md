# CareerPilot

CareerPilot 是一个 AI 驱动的求职工作台，当前仓库已经包含：

- `apps/api`：FastAPI 后端，负责注册、登录、登出、当前用户等接口
- `apps/web`：Next.js 前端，已接入登录态与 `shadcn/ui`
- `docker-compose.middleware.yml`：本地基础服务，包含 PostgreSQL、Redis、MinIO

如果你现在的目标是“把整个项目在本地完整跑起来”，只看这份 README 就够了。

## 项目结构

```text
career-pilot/
├── apps/
│   ├── api/                    # FastAPI 后端
│   └── web/                    # Next.js 前端
├── docker-compose.middleware.yml
├── infra/
│   └── sql/
│       └── init.sql            # 仅本地引导参考，不再作为长期建表方案
└── docs/                       # 项目文档
    ├── DEV_DOCUMENT.md         # 产品/架构文档
    ├── 本地环境安装清单.md     # 本地环境安装指南
    ├── 简历解析与管理模块开发清单.md
    ├── 岗位匹配模块开发清单.md
    └── 3.14开发记录.md
```

## 环境要求

启动当前项目，建议本机至少具备下面这些环境：

- `Docker Desktop` 已安装并已启动
- `uv` 可用
- `Python 3.11.15`
- `Node.js 22+`
- `npm 10+`

可用下面命令快速检查：

```bash
docker info
uv --version
python3 --version
node --version
npm --version
```

## 一次性初始化

第一次拉下项目时，建议按下面顺序初始化。

### 1. 启动基础服务

在项目根目录执行：

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d
```

这会启动 3 个本地服务：

- PostgreSQL：`localhost:5432`
- Redis：`localhost:6380`
- MinIO API：`http://localhost:9000`
- MinIO Console：`http://localhost:9001`

MinIO 默认账号：

- 用户名：`careerpilot`
- 密码：`careerpilot123`

查看服务状态：

```bash
docker compose -f docker-compose.middleware.yml ps
```

### 2. 初始化后端

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/api
cp .env.example .env
uv sync --group dev
uv run alembic upgrade head
```

说明：

- `.env` 会读取数据库、Redis、JWT 等配置
- `alembic upgrade head` 会创建当前后端需要的表
- 现在数据库结构的长期来源是 `apps/api/alembic/versions/`，不是 `infra/sql/init.sql`

### 3. 初始化前端

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
cp .env.example .env.local
npm install
```

说明：

- `.env.local` 里目前最关键的是 `NEXT_PUBLIC_API_BASE_URL`
- 默认已经指向本地后端：`http://127.0.0.1:8000`

## 全量启动方法

推荐你开 3 个终端窗口，分别运行基础服务、后端、前端。

### 终端 1：基础服务

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d
```

### 终端 2：后端 API

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/api
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

后端启动后可验证：

```bash
curl http://127.0.0.1:8000/health
```

预期返回：

```json
{ "status": "ok" }
```

### 终端 3：前端 Web

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
npm run dev
```

启动后访问：

- 首页：<http://localhost:3000>
- 登录页：<http://localhost:3000/login>
- 注册页：<http://localhost:3000/register>

## 按模块分别启动

如果你不是每次都要启动全部内容，可以按下面方式单独启动。

### 只启动数据库和 Redis

当前登录注册模块只依赖 PostgreSQL 和 Redis，最小启动命令：

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d postgres redis
```

### 只启动 MinIO

如果你后面开始做简历上传，可以单独补启动 MinIO：

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d minio
```

### 只启动后端

前提是基础服务已经在运行：

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/api
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 只启动前端

前提是后端已经启动：

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
npm run dev
```

## 当前登录注册链路怎么工作

目前前后端已经打通下面这些接口和页面：

### 后端接口

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /health`

### 前端页面

- `/register`
- `/login`
- `/`

### 登录态机制

- 注册成功后，前端会保存 JWT
- 登录成功后，前端会保存 JWT
- 刷新页面时，前端会自动调用 `/auth/me` 恢复当前用户
- 退出时，前端会调用 `/auth/logout`

## 常用开发命令

### 后端

安装依赖：

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/api
uv sync --group dev
```

执行迁移：

```bash
uv run alembic upgrade head
```

运行测试：

```bash
uv run pytest
```

运行静态检查：

```bash
uv run ruff check .
```

### 前端

安装依赖：

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
npm install
```

本地开发：

```bash
npm run dev
```

代码检查：

```bash
npm run lint
```

生产构建检查：

```bash
npm run build
```

## 停止项目

### 停止前端

在前端终端里按：

```bash
Ctrl + C
```

### 停止后端

在后端终端里按：

```bash
Ctrl + C
```

### 停止基础服务

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml down
```

如果你想连容器卷一起删掉：

```bash
docker compose -f docker-compose.middleware.yml down -v
```

## 常见问题

### 1. `docker info` 报错

说明 Docker Desktop 没有启动。先打开 Docker Desktop，再重试。

### 2. 前端能打开，但注册/登录失败

优先检查：

```bash
curl http://127.0.0.1:8000/health
```

如果这个接口不通，说明后端没启动成功。

### 3. 数据库连不上

确认 PostgreSQL 是否已启动：

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml ps
```

### 4. 改了表结构之后怎么办

不要再去手改 `infra/sql/init.sql` 当正式方案。正确做法是：

1. 在 `apps/api/alembic/versions/` 新增迁移
2. 执行 `uv run alembic upgrade head`

## 当前推荐启动顺序

如果你想最稳地跑起来，请直接照这个顺序执行：

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d

cd apps/api
cp .env.example .env
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

cd ../web
cp .env.example .env.local
npm install
npm run dev
```

跑起来以后，先打开：

- <http://localhost:3000/register>

先注册一个测试账号，再去验证登录、退出和登录态恢复流程。

12:50
用户 0862960367

.gitignore .python-version 3.14 开发记录.md 本地环境安装清单.md 岗位匹配模块开发清单.md DEV_DOCUMENT.md docker-compose.middleware.yml LICENSE README.en.md README.md apps docs infra packages Workspace 仔细阅读本项目全部的文件，告诉我这个项目的核心功能是什么？？？

Builder

参考了 10 个上下文

根据我对项目文件的详细阅读,这个项目的核心功能是:

## 🎯 项目核心功能

职点迷津(CareerPilot) 是一个面向求职者的 AI 求职提升平台,围绕以下六大核心场景形成完整闭环:

### 1. 简历解析与管理

- PDF 简历上传与自动解析
- 结构化简历数据展示
- 人工校正功能
- 多版本管理

### 2. 岗位匹配与分析

- JD(职位描述)手动录入与结构化
- 简历与岗位的智能匹配评分
- 可解释的匹配报告(总分、维度分、优势/短板/建议)
- 规则引擎 + AI 修正的混合评分机制

### 3. 简历优化建议

- 基于匹配报告生成优化建议
- 优先级排序
- 具体改进措施

### 4. 模拟面试

- 多轮对话式面试模拟
- 流式输出
- 会话状态管理
- 面试评分与反馈

### 5. 项目话术生成

- 基于简历生成项目介绍话术
- 支持不同深度版本(short/standard/deep_dive)
- 生成依据可追溯

### 6. 历史复盘与评测

- 面试记录保存
- 薄弱点分析
- 评测集与指标看板
