# AGENTS.md - CareerPilot 项目开发规范

## Project

- **Monorepo root**: `.`
- **Backend**: `apps/api` (FastAPI + SQLAlchemy + PostgreSQL)
- **Frontend**: `apps/web` (Next.js 16 + React 19 + TypeScript)

## Environment

- **Node**: `>=20`
- **pnpm**: `>=9`
- **Python**: `3.11`
- **Required services** (via Docker):
  - PostgreSQL: `localhost:5432`
  - Redis: `localhost:6380`
  - MinIO: `http://localhost:9000`

启动服务：`docker compose -f docker-compose.middleware.yml up -d`

## Core Workflow (Resume Feature)

1. 用户上传 PDF 简历
2. 后端存储 PDF 到 MinIO，创建 parse job (`pending`)
3. 后台任务解析 PDF，回写：
   - `resume.raw_text`
   - `resume.structured_json`
   - `resume.parse_status`
   - `resume_parse_jobs.status/error_message`
4. 前端轮询展示解析结果
5. 用户可手动校正并保存

**Expected status transition**:

- `pending -> processing -> success`
- `pending -> processing -> failed`
- **Bug**: 任何 job 卡在 `pending` 或 `processing` 超过 120 秒

## Commands

### 后端 (apps/api)

```bash
cd apps/api
cp .env.example .env                    # 首次启动
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
uv run pytest                           # 测试
```

### 前端 (apps/web)

```bash
cd apps/web
cp .env.example .env.local              # 首次启动
npm install
npm run dev                             # 开发
npm run lint                            # 检查
```

## .env 关键变量

### 后端 (apps/api/.env)

- `DATABASE_URL`: PostgreSQL 连接串
- `REDIS_URL`: Redis 连接串
- `STORAGE_ENDPOINT`: MinIO 地址
- `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY`: MinIO 凭证
- `JWT_SECRET_KEY`: JWT 密钥

### 前端 (apps/web/.env.local)

- `NEXT_PUBLIC_API_BASE_URL`: 后端地址 (默认 `http://127.0.0.1:8000`)

## Rules

### 代码修改

1. 优先做最小修改，不要顺手重构无关代码
2. 改动前先说明计划，改动后总结影响文件
3. 不要修改 `alembic/versions/` 迁移文件，除非明确要求

### 测试要求

1. 新增接口时必须补充测试
2. 修改解析流程时必须补后端集成测试或说明原因
3. 修改前端轮询/编辑时必须给出手工验证步骤

### 调试要求 (涉及简历解析)

必须检查：

- API 日志 (后端 uvicorn 输出)
- `parse_jobs` 表记录 (状态流转)
- MinIO 文件是否存在
- 前端轮询逻辑是否停止

### 禁止项

1. 不要随意改解析脚本规则和 schema，除非问题确实在解析逻辑本身
2. 不要新增基础设施依赖或大改架构，除非先说明原因
3. 不要默认问题在解析脚本，先检查任务调度、状态写回、前端轮询

## Done When

- ✅ 测试通过
- ✅ Lint 通过
- ✅ 说明复现步骤与验证结果
- ⚠️ 若本地缺依赖导致无法完整验证，必须明确写出：ß
  - 阻塞项
  - 已执行的命令
  - 未完成的验证项

## 调试清单 (Resume Parse 问题)

1. 检查 Docker 服务是否运行：`docker compose ps`
2. 检查后端日志是否有 parse job 执行记录
3. 检查数据库 `parse_jobs` 表状态流转
4. 检查 MinIO 是否有上传的 PDF 文件
5. 检查前端轮询间隔 (当前 5 秒) 和停止条件
