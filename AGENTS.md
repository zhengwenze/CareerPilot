# AGENTS.md

本文件为 CareerPilot 仓库中的编码代理提供任务驱动的工作约束、导航入口、验证要求与交付规范。目标是帮助代理更快找到正确入口、执行最小修改、完成最小必要验证。

# 第一性原理

请使用第一性原理思考。你不能总是假设我非常清楚自己想要什么和该怎么得到。请保持严谨，从原始需求和问题出发，如果动机和目标不清晰，必须停下来和我讨论。

# 方案规范

当需要你给出修改或重构方案时必须符合以下规范：
不允许给出兼容性或补丁性的方案
不允许过度设计，保持最短路径实现且不能违反第一条要求
不允许自行给出我提供的需求以外的方案，例如一些兜底和降级方案，这可能导致业务逻辑偏移问题
必须确保方案的逻辑正确，必须经过全链路的逻辑验证

## 1. Scope and Core Rules

### Scope and precedence

- 本文件适用于仓库根目录及所有未被子目录 AGENTS.md 覆盖的目录。
- 若子目录存在更具体的 AGENTS.md 或 override 文件，以更具体的规则为准。
- 若用户在当前任务中给出明确指令，优先遵循用户指令；若与本文件冲突，需在结果中说明偏离原因。

### Repository snapshot

- Monorepo root: `.`
- Backend: `apps/backend`，FastAPI + SQLAlchemy + PostgreSQL
- Frontend: `apps/frontend`，Next.js 16 + React 19 + TypeScript
- MiniProgram: `apps/miniprogram`，微信小程序
- 中间件服务: PostgreSQL `5432`、Redis `6380` (映射 6379)、MinIO `9000/9001`
- Docker 编排: `docker-compose.middleware.yml` (位于根目录)

### Hard rules

- 不要默认重装依赖；优先使用已有依赖环境，仅在明确需要时执行 `uv sync` 或 `npm install`。
- 不要默认跑全量测试；优先运行与改动范围直接相关的最小验证。
- 不要无任务目的地扫描整个仓库；先看与当前任务直接相关的文件。
- 除非任务明确要求，否则不要顺手重命名文件、抽象公共层、升级依赖或调整目录结构。
- 在开始修改前，先用 3-5 行说明计划与改动范围。
- 完成修改后，列出受影响文件，并说明每个文件为何需要改动。

### Change boundaries

允许修改：

- 业务代码
- 测试代码
- 前端页面与组件
- 轮询逻辑与客户端状态管理

慎改：

- 解析 schema 定义
- 对象存储配置
- 状态机定义
- 解析脚本规则

禁止修改：

- 历史迁移文件 `alembic/versions/`
- 基础设施编排文件，除非任务明确要求
- 无关的 package lock 文件
- `.env.example` 中的变量名，除非任务明确要求

### Frontend visual rule

- 前端默认采用 Apple 风格：白色背景、黑色文字、蓝色主按钮，不使用杂乱配色和深色主题。
- 导航优先放顶部，布局居中，对齐整齐，留白充足，桌面端优先再适配移动端。
- 组件视觉保持克制：大圆角、细边框、轻阴影，不使用复杂渐变、厚重毛玻璃或炫技动画。
- 页面优先展示真实功能与真实数据，删除无实际作用的占位卡片、解释性文案和假内容。
- 文案简短直接，信息层级清楚；一个区域只表达一个核心目的，避免界面拥挤。

### Must stop and report

如果出现以下任一情况，必须停下并说明原因、已执行排查、缺失条件与建议后续步骤：

- 任务需要修改禁止区域
- 无法复现且缺少必要输入
- 外部依赖不可用，导致无法继续
- 验证无法完成

### Secrets and environment safety

- 不要在代码、测试、日志或提交说明中硬编码真实密钥。
- 不要修改 `.env.example` 中变量名，除非任务明确要求。
- 若新增环境变量，必须同时更新示例文件与说明。

## 2. High-Frequency Paths

按任务类型快速进入，避免大范围搜索。

### Resume upload / parse / retry / structured save

- 上传入口：`apps/backend/app/api/routes/resumes.py`
- 业务编排：`apps/backend/app/services/resume.py`
- 规则解析：`apps/backend/app/services/resume_parser.py`
- AI 校正：`apps/backend/app/services/resume_ai.py`
- 数据模型：`apps/backend/app/models/resume.py`、`apps/backend/app/models/resume_parse_job.py`
- API schema：`apps/backend/app/schemas/resume.py`
- 前端页面：`apps/frontend/src/app/(dashboard)/dashboard/resume/page.tsx`
- 前端 API 映射：`apps/frontend/src/lib/api/modules/resume.ts`
- 前端详情组件：`apps/frontend/src/components/resume/`
- 后端测试：`apps/backend/tests/test_resume.py`、`apps/backend/tests/test_resume_parser.py`

### MiniProgram

- 小程序入口：`apps/miniprogram/pages/index/`

### Match report

- API 入口：`apps/backend/app/api/routes/match_reports.py`
- 业务编排：`apps/backend/app/services/match_report.py`
- 规则匹配：`apps/backend/app/services/match_engine.py`
- AI 修正：`apps/backend/app/services/match_ai.py`
- 数据模型：`apps/backend/app/models/match_report.py`、`apps/backend/app/models/job_description.py`
- 测试：`apps/backend/tests/test_match_reports.py`、`apps/backend/tests/test_jobs.py`

### Resume optimization

- API 入口：`apps/backend/app/api/routes/resume_optimization.py`
- 业务逻辑：`apps/backend/app/services/resume_optimizer.py`
- 数据模型：`apps/backend/app/models/resume_optimization_session.py`
- 前端页面：`apps/frontend/src/app/(dashboard)/dashboard/optimizer/page.tsx`
- 测试：`apps/backend/tests/test_resume_optimizer.py`

### Profile and auth

- Profile API：`apps/backend/app/api/routes/profile.py`
- Auth API：`apps/backend/app/api/routes/auth.py`
- 服务层：`apps/backend/app/services/profile.py`、`apps/backend/app/services/auth.py`
- 测试：`apps/backend/tests/test_profile.py`、`apps/backend/tests/test_auth.py`

### Config, storage, and fixtures

- 运行时配置：`apps/backend/app/core/config.py`
- Object storage：`apps/backend/app/services/storage.py`
- 测试夹具：`apps/backend/tests/conftest.py`
- 本地大模型代理：`scripts/codex2gpt/`

### Environment commands

```bash
# 检查依赖服务状态
docker compose -f docker-compose.middleware.yml ps

# 启动依赖服务
docker compose -f docker-compose.middleware.yml up -d

# 停止依赖服务
docker compose -f docker-compose.middleware.yml down

# 启动后端
cd apps/backend
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 启动前端
cd apps/frontend
npm run dev

# 启动所有服务 (包含中间件)
./docker/start.sh
```

## 3. Default Work Loop

收到任务后，默认按以下顺序执行：

1. 先阅读与任务直接相关的文件，避免全仓扫描。
2. 优先复现问题；不能复现则明确缺失条件。
3. 先定位第一个偏离预期的状态节点，再决定修改点。
4. 仅做与当前问题直接相关的最小修改。
5. 修改后运行最小必要验证。
6. 输出修改说明、验证结果、风险与未验证项。

### Preferred debug loop

对异步任务、轮询、后台作业类问题，优先按以下顺序排查：

1. 请求是否到达，记录是否创建。
2. 状态是否从初始态进入下一状态。
3. 外部依赖是否被调用。
4. 结果是否成功写回数据库。
5. 前端是否正确感知最终状态并停止轮询。

### Small change vs workflow change

- 小改动：局部字段、局部文案、单函数逻辑修复。保持最小范围说明、最小验证、精简结果。
- 工作流改动：涉及 schema、状态机、后台任务、轮询、AI 接入、持久化写回。必须明确状态流转、失败策略、验证覆盖点。
- 若改动涉及解析链路、匹配链路、优化链路、AI 接入或异步任务，默认按工作流改动处理。

## 4. Workflow Specs

### Resume Parse

Primary records：

- `resumes`
- `resume_parse_jobs`

Standard flow：

1. 用户上传 PDF，文件写入 MinIO。
2. 创建 `resume` 和 `resume_parse_job` 记录，初始状态为 `pending`。
3. 后台任务进入 `processing`，读取 PDF 字节并抽取 `raw_text`。
4. 执行规则解析，得到规则结构化结果。
5. 若开启 LLM 校正，则执行 `规则解析 -> LLM 校正 -> 校验/兜底 -> 最终 structured_json`。
6. 写回 `raw_text`、`structured_json`、`parse_status`，任务结束。

Key fields：

- `resume.raw_text`
- `resume.structured_json`
- `resume.parse_status`，仅使用 `pending / processing / success / failed`
- `resume.parse_error`
- `resume_parse_jobs.status`
- `resume_parse_jobs.error_message`

Expected status transition：

- `pending -> processing -> success`
- `pending -> processing -> failed`
- Bug：任何 job 卡在 `pending` 或 `processing` 超过 120 秒

Success criteria：

- PDF 已上传到 MinIO
- job 状态完成流转
- `raw_text` 与 `structured_json` 已写回
- 前端正确展示并停止轮询

Common failure points：

1. 中间件未启动
2. 后台任务未被调度或执行
3. 文本抽取失败
4. 规则解析失败
5. AI 校正异常但未正确兜底
6. 结果写回失败
7. 前端轮询未停止

### Match Report

Primary records：

- `job_descriptions`
- `match_reports`

Expected flow：

1. 录入 JD 并异步结构化。
2. 选择简历生成匹配报告。
3. 报告生成评分卡、改写任务、面试蓝图。

Success criteria：

- 岗位画像生成成功
- 匹配报告包含可执行改写任务
- 报告可被简历优化模块消费

### Resume Optimization

Primary records：

- `resume_optimization_sessions`

Expected flow：

1. 从岗位匹配页进入创建优化会话。
2. 选择改写任务生成草案。
3. 编辑草案并应用到简历。
4. 简历版本提升，原岗位快照标记为 `stale`。

Success criteria：

- 草案可编辑且可保存
- 应用后简历版本正确提升
- 岗位快照正确标记为过期

## 5. LLM Integration Guardrails

所有新增或修改的大模型接入，默认遵循以下原则：

- 优先复用仓库内已有的 OpenAI-compatible provider 模式，不要为单个功能重新发明接入方式。
- 本地开发默认优先对接 `scripts/codex2gpt`，不要把脚本路径硬编码进业务逻辑。
- Prompt 必须明确限制模型角色；若任务是校正器，就不要让模型扮演重解析器或自由生成器。
- 结果必须是 strict JSON，可被 Pydantic 或等价校验器验证。
- 模型原始自然语言输出不得直接落库。
- 必须有明确 fallback；外部 AI 调用失败时，系统行为必须可预期。
- 未经明确确认，不要新增前端公开状态机。

### Resume parse specific guardrails

- 标准链路是：`PDF -> 规则解析 -> LLM 校正 -> 校验/兜底 -> structured_json`
- 规则解析是主链路，LLM 仅负责校正、补全、去重、归类，不负责自由抽取。
- 若规则解析失败，任务整体失败；不要再调用 AI。
- 若规则解析成功但 AI 失败、超时、返回非法 JSON 或出现幻觉风险，必须回退到规则结果，并允许任务仍然 `success`。
- 不允许让模型生成当前 schema 之外的新字段，除非用户先确认要升级 schema。
- 不允许仅为了展示更细粒度进度而扩展公开状态机；若确有必要，先给方案再改。

## 6. Verification Matrix

优先最小必要验证，不默认跑全量。

### Known good command pattern

- `UV_CACHE_DIR=.uv-cache uv run ...`：当默认 `uv` 缓存目录权限受限时，优先使用仓库内缓存目录。
- 后端定向 pytest：优先直接点到相关测试文件。
- 前端改动：优先 `npm run lint`，再补必要手工验证。

### Verification by change type

| 改动类型                                               | 最小验证命令                                                                                               | 验证要点                                  |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| 仅改 `resume_parser.py` / `resume_ai.py` / `resume.py` | `cd apps/backend && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_resume.py tests/test_resume_parser.py` | 解析状态流转、AI fallback、结构化结果写回 |
| Resume parse API 或 schema 改动                        | `cd apps/backend && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_resume.py tests/test_resume_parser.py` | 上传、详情、重试、parse jobs 正常         |
| Match report 改动                                      | `cd apps/backend && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_match_reports.py tests/test_jobs.py`   | 匹配报告生成与 AI 修正逻辑正常            |
| Resume optimization 改动                               | `cd apps/backend && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_resume_optimizer.py`                   | 会话创建、草案生成、应用版本提升          |
| Profile/Auth 改动                                      | `cd apps/backend && UV_CACHE_DIR=.uv-cache uv run pytest tests/test_profile.py tests/test_auth.py`         | 登录、鉴权、资料读写正常                  |
| Frontend-only changes                                  | `cd apps/frontend && npm run lint`                                                                         | ESLint 通过                               |
| Resume page / polling 改动                             | `cd apps/frontend && npm run lint`                                                                         | 手工验证上传、轮询、成功/失败、停止轮询   |
| API contract changes                                   | 后端定向 pytest + `cd apps/frontend && npm run lint`                                                       | 接口与前端映射一致                        |

### Testing requirements

- 新增接口时必须补测试。
- 修改解析流程时必须补最小后端集成测试或说明原因。
- 修改前端轮询或编辑时必须给出手工验证步骤。
- 修改关键日志、状态流转或后台任务处理时，优先补能覆盖该流转的最小测试。

## 7. Debug Playbooks

### UI no-response

当 UI 无响应时，按以下顺序排查：

1. 浏览器 Network 是否发出请求。
2. 对应后端接口是否收到请求。
3. 后端是否报错，是否有完整 stack trace。
4. 依赖服务是否正常。
5. 状态是否已写回数据库但前端未更新。

### Background job stuck

- 创建失败：检查请求是否到达、参数是否校验通过、记录是否创建。
- 调度失败：检查后台任务调度逻辑。
- 执行失败：检查任务日志与外部依赖调用。
- 写回失败：检查数据库更新和事务提交。
- 前端感知失败：检查轮询、成功/失败终止逻辑。

### State not moving

1. 确认任务是否已创建。
2. 确认是否进入下一状态。
3. 若未进入，判断失败点在调度前、调度时还是状态更新。
4. 若已进入，判断失败点在依赖调用、业务处理还是结果写回。

## 8. Output Contract

### Done criteria

任务完成需满足：

- 测试通过，或明确说明未通过原因
- Lint 通过，或明确说明未通过原因
- 给出复现步骤、修复说明、验证结果
- 若本地环境缺依赖或外部服务不可用，明确写出阻塞项、已执行命令、已完成验证、尚未完成验证

### Required output sections

完成任务后，默认输出以下内容：

1. `Summary`
2. `Files Changed`
3. `Why Each File Changed`
4. `Validation`
5. `Risks / Follow-ups`

以下内容按需提供：

- `Manual Verification`：前端交互、异步轮询、外部依赖联调相关改动时必须提供
- `Blockers`：存在阻塞项时必须提供

### Output expectations

- 小改动可以简洁，但不能省略验证结果。
- 工作流改动必须明确状态流转、失败策略与未覆盖风险。
- 若验证未完成，明确给出哪些已验证、哪些未验证、为什么未验证。
