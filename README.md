# Career Pilot

Career Pilot 是一个面向求职场景的 AI 工作台，当前围绕两条主链路展开：

- 把 PDF 简历整理成可编辑、可保存、可定制的 Markdown 简历
- 基于目标岗位生成优化后的专属简历，并直接进入对应的模拟面试训练

这个项目不是“信息展示型官网”，而是一个强调连续操作的求职工作流产品。用户从上传简历开始，到保存岗位、生成专属版本、进入模拟面试，主要动作都在同一个工作台内完成。

## 项目定位

Career Pilot 解决的是求职过程中最常见的三个断点：

- 简历内容散乱，PDF 难改，岗位定制成本高
- 岗位 JD 和个人经历之间缺少一条可执行的优化链路
- 简历改完之后，用户不知道如何继续训练面试表达

因此，当前版本重点不是堆很多模块，而是把下面这条链路打通：

1. 上传主简历
2. 转成 Markdown 并保存
3. 保存目标岗位 JD
4. 生成专属优化简历
5. 下载结果或直接进入模拟面试

## 当前功能

### 1. 账号与基础工作台

- 支持注册、登录、登出和当前用户状态识别
- 支持维护个人资料，包括昵称、求职方向、目标城市、期望岗位
- 登录后进入统一 Dashboard，按模块继续后续操作

### 2. 主简历上传与 Markdown 化

- 支持上传 PDF 简历
- 系统会先抽取 PDF 文本，再转换成可编辑的 Markdown 简历
- 转换结果会自动保存到当前账户，刷新页面后仍可继续编辑
- 页面同时提供 Markdown 编辑区与实时预览区，方便边改边看

这一部分的目标不是做“原样存档”，而是把用户后续真正会反复修改的简历内容沉淀成可维护的 Markdown 版本。

### 3. 简历保存与结构化沉淀

- 用户可以直接在页面上修改 Markdown 简历并保存
- 保存时，系统会把 Markdown 转成结构化数据，供后续匹配、优化、模拟面试复用
- 保存后的简历会保留版本号，用于后续工作流追踪

这意味着 Career Pilot 的“主简历”不是一份静态文件，而是后续所有动作的事实来源。

### 4. 目标岗位 JD 保存

- 支持录入并保存目标岗位描述
- 保存后会触发岗位解析，提取岗位标题、关键信息和后续工作流所需上下文
- 简历页内可以直接维护当前岗位，不需要跳到独立后台系统

当前产品把主简历和目标岗位放在同一页管理，减少用户在不同页面之间来回切换。

### 5. 专属简历生成

- 基于“已保存主简历 + 已保存岗位 JD”生成岗位定制版简历
- 生成过程有明确状态反馈，支持轮询查看进度
- 成功后可直接下载 Markdown 成品
- 如果当前结果失败或为空，支持重试生成

这里的核心不是给一堆泛泛建议，而是产出一份可以继续使用、继续投递、继续训练面试的专属简历结果。

### 6. 从优化结果直接进入模拟面试

- 专属简历生成成功后，页面会提供“开始模拟面试”入口
- 进入面试时，会自动带上当前岗位和对应的优化结果上下文
- 用户不需要重新整理背景信息，也不需要重复创建练习材料

这一步把“改简历”和“练面试”真正接起来了，而不是两个互相独立的功能页。

### 7. 模拟面试

- 支持基于目标岗位和优化简历创建模拟面试会话
- 系统会先准备第一题，再在后台继续准备后续问题
- 用户可以逐题作答，系统会返回追问或继续下一题
- 面试结束后会生成复盘信息，包括优势、风险和下一步建议
- 已创建的模拟面试会话支持查看、继续、结束、删除和重试准备

当前模拟面试不是单次问答弹窗，而是带会话状态和历史记录的持续训练流程。

## 典型使用流程

### 流程一：制作专属简历

1. 注册并登录
2. 进入“专属简历”
3. 上传 PDF 简历
4. 检查并编辑 Markdown 简历
5. 保存目标岗位 JD
6. 点击生成优化简历
7. 下载岗位定制版 Markdown 简历

### 流程二：从专属简历进入模拟面试

1. 完成一份优化简历生成
2. 点击“开始模拟面试”
3. 等待系统准备第一题
4. 逐题回答并接收追问
5. 在结束后查看复盘结论

## 当前模块状态

### 已可使用

- 账号注册与登录
- 个人资料维护
- PDF 简历上传
- PDF 转 Markdown
- Markdown 简历保存
- 岗位 JD 保存与解析
- 专属简历生成、重试与下载
- 从优化结果进入模拟面试
- 模拟面试会话创建、作答、结束、删除、重试

### 已有页面骨架，但仍在开发中

- 设置页
- 投递追踪页

README 下面的说明基于仓库当前页面、导航和 API 入口整理，不把“预留页面”写成已交付功能。

## 技术栈

### 前端

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4

### 后端

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- MinIO

### AI 与文档处理

- PyMuPDF / pymupdf4llm 用于 PDF 内容抽取与 Markdown 化
- OpenAI-compatible / Anthropic 风格模型接入用于简历整理、专属简历生成与模拟面试

## 目录结构

```text
career-pilot/
├── apps/
│   ├── backend/       # FastAPI 后端
│   ├── frontend/      # Next.js 前端
│   └── miniprogram/   # 微信小程序
├── docker/            # 部署与辅助脚本
├── docker-compose.yml # 本地 / 容器化运行编排
├── README.md
└── SETUP.md
```

## 快速启动

### 1. 克隆仓库

```bash
git clone https://gitee.com/zwz050418/career-pilot.git
cd career-pilot
```

### 2. 启动依赖服务

```bash
docker compose -f docker-compose.yml up -d postgres redis minio
```

### 3. 启动后端

```bash
cd apps/backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

### 4. 启动前端

```bash
cd ../frontend
npm install
npm run dev
```

访问 **http://localhost:3000** 即可。

### 配置 AI 提供商

编辑 `apps/backend/.env`，选择以下方案之一：

**MiniMax（推荐）**
```env
RESUME_AI_PROVIDER=minimax
RESUME_AI_BASE_URL=https://api.minimaxi.com/anthropid
RESUME_AI_API_KEY=your_key
RESUME_AI_MODEL=MiniMax-M2.5
```

**本地免费模型**
```bash
python scripts/codex2gpt/server.py
```
```env
RESUME_AI_PROVIDER=openai-compatible
RESUME_AI_BASE_URL=http://localhost:8001/v1
```

## 访问地址

| URL | 说明 |
|-----|------|
| http://localhost:3000 | 前端 |
| http://localhost:8000 | 后端 API |
| http://localhost:9001 | MinIO 控制台 |
| https://codeclaw.top | 服务器部署地址 |

## 适合谁使用

Career Pilot 当前更适合以下用户：

- 需要频繁为不同岗位调整简历的求职者
- 想把 PDF 简历转成可持续维护 Markdown 的用户
- 希望把“岗位定制简历”和“模拟面试训练”串成一条流程的用户
- 希望在一个工作台内持续维护简历、岗位与训练记录的用户

## 相关文档

- 更细的代码入口与代理约束见 [AGENTS.md](/Users/zhengwenze/Desktop/codex/career-pilot/AGENTS.md)
