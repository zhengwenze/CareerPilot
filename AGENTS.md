# AGENTS.md

本文件为编码代理提供 CareerPilot 仓库中的工作约束、导航信息、验证要求与调试流程。

## Repository Overview

- **Monorepo root**: `.`
- **Backend**: `apps/api` (FastAPI + SQLAlchemy + PostgreSQL)
- **Frontend**: `apps/web` (Next.js 16 + React 19 + TypeScript)

## Code Navigation

- API routes: `apps/api/app/api/`
- DB models: `apps/api/app/models/`
- Resume parse pipeline / background jobs: `apps/api/app/jobs/`, `apps/api/app/services/`
- Tests: `apps/api/tests/`
- Upload / resume pages: `apps/web/app/`, `apps/web/src/pages/`
- Polling logic and client state: `apps/web/src/hooks/`, `apps/web/src/lib/`

## Environment

- **Node**: `>=20`
- **pnpm**: `>=9`
- **Python**: `3.11`
- **Required services** (via Docker):
  - PostgreSQL: `localhost:5432`
  - Redis: `localhost:6380`
  - MinIO: `http://localhost:9000`

启动服务：`docker compose -f docker-compose.middleware.yml up -d`

## Default Working Flow

收到任务后，默认按以下顺序执行：

1. 先阅读与任务直接相关的目录与文件，不要全仓扫描
2. 先复现问题，再修改代码；如果无法复现，说明缺失条件
3. 优先做最小修改，只修改与当前任务直接相关的文件
4. 改动后运行最小必要验证；若涉及解析链路，补充状态流转检查
5. 输出结果时说明：
   - 修改了哪些文件
   - 为什么这样改
   - 跑了哪些验证
   - 还有哪些风险或未验证项

## Validation Commands

### Backend-only changes

```bash
cd apps/api
uv run pytest
```

### Frontend-only changes

```bash
cd apps/web
npm run lint
```

### API contract / resume parse flow changes

```bash
cd apps/api
uv run pytest

cd ../web
npm run lint
```

不要默认运行全量耗时命令；优先运行与改动范围直接相关的最小验证。

## Resume Parse Workflow

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

## Resume Parse Troubleshooting

当 parse job 在 `pending` 或 `processing` 停留超过 120 秒时，按以下顺序检查：

1. 检查 Docker 依赖服务是否正常运行：`docker compose ps`
2. 检查后端日志中是否有 job 被消费/执行的记录
3. 检查数据库中的 `resume_parse_jobs` 状态是否发生流转
4. 检查 MinIO 中对应 PDF 是否上传成功
5. 检查解析结果写回是否成功：
   - `resume.raw_text`
   - `resume.structured_json`
   - `resume.parse_status`
   - `resume_parse_jobs.status`
   - `resume_parse_jobs.error_message`
6. 检查前端轮询是否在成功/失败后正确停止

## Rules for Code Changes

### 允许修改

- 业务代码
- 测试代码
- 前端页面与组件
- 轮询逻辑与客户端状态管理

### 慎改

- 解析 schema 定义
- 对象存储配置
- 状态机定义
- 解析脚本规则

### 禁止修改

- 历史迁移文件 (`alembic/versions/`)
- 基础设施编排文件（除非任务明确要求）
- 无关 package lock 文件
- `.env.example` 中的变量名（除非任务明确要求）

### 代码修改原则

- 除非任务明确要求，否则不要顺手重命名文件、抽象公共层、升级依赖或调整目录结构
- 在开始修改前，先用 3-5 行说明计划与改动范围
- 完成修改后，列出受影响文件，并说明每个文件为何需要改动

## Testing Requirements

- 新增接口时必须补充测试
- 修改解析流程时必须补后端集成测试或说明原因
- 修改前端轮询/编辑时必须给出手工验证步骤

## Secrets and Environment Safety

- 不要在代码、测试或提交说明中写入真实密钥
- 不要修改 `.env.example` 中变量名，除非任务明确要求
- 若新增环境变量，必须同时更新示例文件与说明

## Done Criteria

任务完成需满足：

- 测试通过，或明确说明未通过的原因
- Lint 通过，或明确说明未通过的原因
- 给出复现步骤、修复说明、验证结果
- 若本地环境缺依赖或外部服务不可用，必须明确写出：
  - 阻塞项
  - 已执行命令
  - 已完成验证
  - 尚未完成验证

## Output Format

完成任务后，按以下格式汇报：

1. Summary
2. Files Changed
3. Validation
4. Manual Verification
5. Risks / Follow-ups
