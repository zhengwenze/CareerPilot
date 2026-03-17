# AGENTS.md

本文件为编码代理提供 CareerPilot 仓库中的工作约束、导航信息、验证要求与调试流程。

## Scope and Precedence

- 本文件适用于仓库根目录及所有未被子目录 AGENTS.md 覆盖的目录。
- 若子目录存在更具体的 AGENTS.md（或工具支持的 override 文件），以子目录规则为准。
- 若用户在当前任务中给出明确指令，优先遵循用户指令；若与本文件冲突，需在结果中说明偏离原因。

## Repository Overview

- **Monorepo root**: `.`
- **Backend**: `apps/api` (FastAPI + SQLAlchemy + PostgreSQL)
- **Frontend**: `apps/web` (Next.js 16 + React 19 + TypeScript)
- **中间件服务**: PostgreSQL (5432), Redis (6380), MinIO (9000/9001)

### 代理最常见的任务类型

- 新增/修改 API 接口
- 修改数据模型或数据库迁移
- 调试简历解析/岗位匹配/简历优化等核心业务链路
- 前端页面开发与状态管理
- 后台任务调试与日志排查

## Task-oriented Navigation

根据任务类型快速定位相关代码：

- **新增/修改 API**：先看 `apps/api/app/api/`
- **修改数据模型**：先看 `apps/api/app/models/`
- **解析任务/后台链路**：先看 `apps/api/app/services/`
- **前端上传与简历页面**：先看 `apps/web/src/app/(dashboard)/dashboard/resume/`
- **前端岗位匹配页面**：先看 `apps/web/src/app/(dashboard)/dashboard/jobs/`
- **前端简历优化页面**：先看 `apps/web/src/app/(dashboard)/dashboard/optimizer/`
- **轮询与客户端状态**：先看 `apps/web/src/hooks/` 和 `apps/web/src/lib/`
- **后端测试**：`apps/api/tests/`

## Environment and Services

### 依赖服务启动命令

```bash
# 检查依赖服务状态
docker compose -f docker-compose.middleware.yml ps

# 启动依赖服务
docker compose -f docker-compose.middleware.yml up -d

# 停止依赖服务
docker compose -f docker-compose.middleware.yml down
```

### 后端启动命令

```bash
cd apps/api
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 前端启动命令

```bash
cd apps/web
npm run dev
```

### 前端 Apple 风格 UI 规则

- 前端默认采用苹果Apple官网风格：白色背景、黑色文字、蓝色主按钮，不使用杂乱配色和深色主题
- 导航优先放顶部，布局居中，对齐整齐，留白充足，桌面端优先再适配移动端
- 组件视觉保持克制：大圆角、细边框、轻阴影，不使用复杂渐变、厚重毛玻璃或炫技动画
- 页面优先展示真实功能与真实数据，删除无实际作用的占位卡片、解释性文案和假内容
- 文案简短直接，信息层级清楚；一个区域只表达一个核心目的，避免界面拥挤

### 不要做什么

- 不要默认重装依赖（优先使用 `uv sync` / `npm install`）
- 不要默认跑全量测试（优先运行与改动范围直接相关的最小验证）
- 不要无任务目的地扫描整个仓库

## Default Work Loop

收到任务后，默认按以下顺序执行：

1. 先阅读与任务直接相关的文件，避免全仓扫描
2. 优先复现问题；不能复现则明确缺失条件
3. 先定位第一个偏离预期的状态节点，再决定修改点
4. 仅做与当前问题直接相关的最小修改
5. 修改后运行最小必要验证
6. 输出修改说明、验证结果、风险与未验证项

## Verification Matrix

根据改动类型选择最小必要验证：

| 改动类型                             | 验证命令                                                                                                                    | 验证要点                |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| Backend-only changes                 | `cd apps/api && uv run pytest`                                                                                              | 后端测试通过            |
| Frontend-only changes                | `cd apps/web && npm run lint`                                                                                               | ESLint 通过             |
| API contract changes                 | `cd apps/api && uv run pytest`<br>`cd ../web && npm run lint`                                                               | 后端测试 + 前端 lint    |
| Resume parse workflow changes        | `cd apps/api && uv run pytest`<br>验证状态流转：`pending -> processing -> success\|failed`<br>检查前端轮询在成功/失败后停止 | 状态流转正确 + 轮询停止 |
| Polling / client state changes       | `cd apps/web && npm run lint`<br>手工验证：上传、轮询、成功/失败、停止轮询                                                  | 轮询逻辑正确            |
| Match report workflow changes        | `cd apps/api && uv run pytest`<br>验证岗位画像生成 → 匹配评分 → 报告生成                                                    | 匹配报告正确生成        |
| Resume optimization workflow changes | `cd apps/api && uv run pytest`<br>验证会话创建 → 草案生成 → 应用到简历                                                      | 优化建议正确应用        |

## Critical Workflow: Resume Parse

### Primary records

- `resume`：简历主表
- `resume_parse_jobs`：解析任务表

### Key fields

- `resume.raw_text`：抽取的原始文本
- `resume.structured_json`：结构化数据（教育、工作经历、项目经验等）
- `resume.parse_status`：解析状态（`pending` / `processing` / `success` / `failed`）
- `resume_parse_jobs.status`：任务状态
- `resume_parse_jobs.error_message`：错误信息（失败时）

### Expected status transition

- `pending -> processing -> success`
- `pending -> processing -> failed`
- **Bug**: 任何 job 卡在 `pending` 或 `processing` 超过 120 秒

### Success criteria

- PDF 已上传到 MinIO
- job 状态完成流转（`pending -> processing -> success`）
- 解析结果已写回（`raw_text`、`structured_json`、`parse_status`）
- 前端展示正确且轮询停止

### Common failure points

1. Docker 依赖服务未启动（PostgreSQL/Redis/MinIO）
2. 后台任务未被消费（检查后端日志）
3. 解析结果写回失败（检查数据库字段）
4. 前端轮询未停止（检查成功/失败后的轮询终止逻辑）

## Critical Workflow: Match Report

### Primary records

- `job_descriptions`：岗位描述主表
- `match_reports`：匹配报告表

### Key fields

- `job_descriptions.structured_json`：岗位画像（必备能力、加分项、职责语义簇等）
- `match_reports.status`：报告状态（`pending` / `processing` / `success`）
- `match_reports.fit_band`：匹配度（`excellent` / `strong` / `partial` / `weak`）
- `match_reports.tailoring_plan`：改写任务清单
- `match_reports.interview_blueprint`：面试蓝图

### Expected flow

1. 录入 JD → 异步结构化 → 生成岗位画像
2. 选择简历 → 生成匹配报告 → 保存历史
3. 匹配报告包含：评分卡、改写任务、面试蓝图

### Success criteria

- 岗位画像生成成功
- 匹配报告包含可执行的改写任务
- 报告可被简历优化模块消费

## Critical Workflow: Resume Optimization

### Primary records

- `resume_optimization_sessions`：优化会话表

### Key fields

- `draft_sections`：草案区块（教育、工作经历、项目经验等）
- `selected_tasks`：选中的改写任务
- `suggestions`：AI 生成的改写建议
- `applied_resume_version`：应用后的简历版本号
- `is_stale`：是否过期（匹配快照过期时为 `true`）

### Expected flow

1. 从岗位匹配页进入 → 创建优化会话
2. 选择改写任务 → 生成草案
3. 编辑草案 → 应用到简历 → 提升简历版本
4. 原岗位快照自动标记为 `stale`

### Success criteria

- 草案可编辑且可保存
- 应用后简历版本正确提升
- 岗位快照正确标记为过期

## Troubleshooting Playbooks

### A. 页面无响应类

当 UI 出现无响应时，按以下顺序排查：

1. 检查浏览器 Network 面板，请求是否发出
2. 检查对应后端接口是否收到（查看后端日志）
3. 检查后端是否报错（查看完整 stack trace）
4. 检查依赖服务状态（`docker compose ps`）
5. 检查状态是否回写前端（检查数据库字段更新）

### B. 后台任务卡住类

当后台任务卡住时，按以下分类排查：

- **创建失败**：检查请求是否到达、参数是否校验通过、记录是否创建
- **调度失败**：检查任务调度逻辑、外部依赖调用是否成功
- **执行失败**：检查后台任务日志、外部依赖调用前后日志
- **写回失败**：检查数据库字段更新、事务是否提交
- **前端感知失败**：检查前端轮询逻辑、成功/失败后的处理

### C. 状态不流转类

当状态一直不变时：

1. 确认任务是否已创建
2. 确认是否进入下一状态
3. 若未进入，失败点是在调度前、调度时还是状态更新时
4. 若已进入，失败点是在依赖调用、业务处理还是结果写回

## Logging Contract

### 必须打日志的场景

- 收到请求（带 `request_id`、`user_id`、业务主键）
- 参数校验通过/失败
- 创建或更新业务记录（带业务主键、当前状态）
- 状态流转前后（带 previous status / next status）
- 调用数据库、Redis、MinIO、AI 服务、第三方 API 前后
- 后台任务开始、结束、失败

### 日志最少包含字段

- `request_id`
- `user_id`
- 业务主键（`resume_id`、`job_id`、`task_id`、`session_id` 等）
- 当前状态值（`status`、`parse_status` 等）

### 绝对禁止输出

- 明文密码
- 完整 token
- 真实密钥
- 身份证号、手机号、邮箱原文的大量明文
- 大段简历全文、用户隐私内容或第三方敏感响应

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

### 必须停下的场景

如果任务需要修改禁止区域，或无法复现且缺输入，或外部依赖不可用，或验证无法完成，必须停下并说明：

- 为什么需要修改禁止区域（或为什么无法继续）
- 已执行的排查步骤
- 缺失的条件
- 建议的后续步骤

## Testing Requirements

- 新增接口时必须补充测试
- 修改解析流程时必须补后端集成测试或说明原因
- 修改前端轮询/编辑时必须给出手工验证步骤
- 修改关键日志、状态流转或后台任务处理时，优先补充能覆盖该流转的最小测试

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

## Output Contract

完成任务后，必须包含以下内容：

1. **Summary**：一句话说明完成内容
2. **Files Changed**：列出所有修改文件
3. **Why Each File Changed**：说明每个文件的改动原因
4. **Validation**：运行的验证命令与结果
5. **Manual Verification**：手工验证步骤（如有）
6. **Risks / Follow-ups**：风险与后续跟进项
7. **Blockers**：阻塞项（如有）
