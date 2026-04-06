# Career Pilot

Career Pilot 是一个强调连续操作的求职工作流产品，核心链路如下：

| 步骤 | 操作                                    |
| ---- | --------------------------------------- |
| 1    | 上传 PDF 简历，自动转化为 Markdown      |
| 2    | 保存目标岗位 JD                         |
| 3    | 基于 JD + Markdown 简历生成专属优化简历 |
| 4    | 直接进入对应的模拟面试训练              |

## 功能模块（我的最终目标）

### 1. 账号与基础工作台

- 注册、登录、登出及当前用户状态识别
- 生成个人画像（由AI根据简历和JD自动生成）
- 登录后进入统一 Dashboard

### 2. 主简历上传与 Markdown 化

- 上传 PDF 简历，系统抽取文本并转换为可编辑 Markdown
- 转换结果自动保存到数据库，用户可以直接在网页进行编辑
- Markdown 编辑区与实时预览区同步显示
- 目标是将简历内容沉淀为可维护的 Markdown 版本，而非简单存档。

### 3. 目标岗位 JD 保存

- 用户输入并保存目标岗位描述
- 保存后触发岗位解析，提取JD关键信息
- 简历页内直接维护当前岗位，无需跳转独立后台
- 简历和目标岗位必须在同一页进行操作，减少页面切换。

### 5. 专属简历生成

- 基于"主简历 + 岗位 JD"生成定制版简历
- 生成过程有状态反馈，支持轮询查看进度
- 对于有优化的部分必须说明优化原因
- 成功后可下载 Markdown 结果；失败或为空时支持重试

### 6. 从优化结果直接进入模拟面试

- 专属简历生成成功后，页面提供"开始模拟面试"入口
- 进入面试时，自动带上岗位和优化结果上下文
- 无需重新整理背景信息或重复创建练习材料

> 打通"改简历"和"练面试"两个环节，而非独立功能页。

### 7. 模拟面试

- 基于目标岗位和优化简历创建模拟面试会话
- 系统先准备第一题，后台继续准备后续问题
- 用户逐题作答，系统返回追问或继续下一题
- 每一题在用户回答之后，系统必须对于用户的回答做出评判（全靠弹窗显示），说出回答好的地方以及不足之处和改进建议
- 模拟面试是带会话状态和历史记录的持续训练流程

## 目录结构

````text
career-pilot/
├── AGENTS.md                      # 根级代理规则
├── .agents/
│   ├── plans/                     # 复杂任务计划文档
│   └── skills/                    # repo-local Codex workflows
├── apps/
│   ├── frontend/                  # Next.js 前端工作台
│   │   ├── AGENTS.md
│   │   ├── src/
│   │   │   ├── app/               # Next.js App Router 页面
│   │   │   │   ├── (dashboard)/  # 受保护仪表盘路由组
│   │   │   │   ├── login/
│   │   │   │   ├── register/
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── page.tsx
│   │   │   │   └── globals.css
│   │   │   └── components/        # React 组件
│   │   │       ├── ui/           # shadcn/ui 基础组件
│   │   │       ├── layout/       # 布局组件
│   │   │       ├── guards/       # 路由守卫
│   │   │       └── ...
│   │   ├── package.json
│   │   ├── next.config.ts
│   │   └── Dockerfile
│   ├── backend/                   # FastAPI 后端
│   │   ├── AGENTS.md
│   │   ├── app/
│   │   │   ├── core/              # 核心配置、错误、安全
│   │   │   ├── db/                # 数据库连接与会话
│   │   │   ├── models/            # SQLAlchemy 模型
│   │   │   ├── prompts/           # AI 提示词模板
│   │   │   ├── routers/           # API 路由
│   │   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   │   ├── services/          # 业务逻辑服务
│   │   │   └── main.py
│   │   ├── alembic/               # 数据库迁移
│   │   │   └── versions/
│   │   ├── tests/                 # pytest 测试
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── miniprogram/               # 微信小程序（占位）
├── packages/                      # 共享契约、API 客户端与配置
│   ├── api-client/               # 前后端通信客户端
│   ├── configs/                   # ESLint、TypeScript 共享配置
│   └── contracts/                 # 跨应用数据契约文档
├── docs/                          # 仓库地图、业务知识与运行说明
│   ├── architecture/
│   ├── domain/
│   ├── product/
│   └── index.md
├── references/                    # 参考资产，不是产品源码
│   ├── codex2gpt-demo/
│   ├── monochrome-design/
│   └── ollama-demo/
├── docker/                        # 部署与启动脚本
│   ├── deploy.sh
│   └── start.sh
├── docker-compose.yml             # 中间件编排
└── README.md

## 快速启动

```bash
git clone https://gitee.com/zwz050418/career-pilot.git
cd career-pilot
docker compose up -d
```

访问 **http://localhost:3000** 即可。

### 配置 AI 提供商

编辑 `apps/backend/.env`，推荐使用 `codex2gpt` 作为本地主力 AI provider。

> 将本地登录好的 Codex 转为 OpenAI 风格 API，业务流程与提示词不变，仅替换底层模型。

```env
RESUME_AI_PROVIDER=codex2gpt
RESUME_AI_BASE_URL=http://127.0.0.1:18100/v1
RESUME_AI_API_KEY=
RESUME_AI_MODEL=gpt-5.4
```

> 若 `codex2gpt` 开启了本地鉴权，需填写 `RESUME_AI_API_KEY`。

#### 其他 Provider

**Ollama**

```env
RESUME_AI_PROVIDER=ollama
RESUME_AI_BASE_URL=http://127.0.0.1:11434
RESUME_AI_API_KEY=
RESUME_AI_MODEL=qwen2.5:7b
```

> 若本地有其他 OpenAI-compatible 代理或模型网关，可新增 provider 适配层接入，无需改动业务 prompt 和工作流。

#### PDF 简历清洗降级配置

```env
RESUME_PDF_AI_PRIMARY_TIMEOUT_SECONDS=30
RESUME_PDF_AI_RETRY_COUNT=0
RESUME_PDF_AI_SECONDARY_PROVIDER=ollama
RESUME_PDF_AI_SECONDARY_BASE_URL=http://127.0.0.1:11434
RESUME_PDF_AI_SECONDARY_API_KEY=
RESUME_PDF_AI_SECONDARY_MODEL=qwen2.5:7b
RESUME_PDF_AI_SECONDARY_TIMEOUT_SECONDS=20
```

> 默认按"主模型 → 次模型 → rules"顺序降级。目标是解决失败长尾，使主备降级链路可观测。

## 访问地址

| URL                   | 说明           |
| --------------------- | -------------- |
| http://localhost:3000 | 前端           |
| http://localhost:8000 | 后端 API       |
| http://localhost:9001 | MinIO 控制台   |
| https://codeclaw.top  | 服务器部署地址 |
````
