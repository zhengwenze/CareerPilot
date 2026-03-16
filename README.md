# 职点迷津（CareerPilot）

目录

- [1. 项目定位](#1-项目定位)
- [2. 当前阶段判断](#2-当前阶段判断)
- [3. 核心功能全景](#3-核心功能全景)
- [4. 当前仓库真实现状](#4-当前仓库真实现状)
- [5. 技术栈与基础设施](#5-技术栈与基础设施)
- [6. 项目结构说明](#6-项目结构说明)
- [7. 前端设计思想](#7-前端设计思想)
- [8. 后端设计思想](#8-后端设计思想)
- [9. 本地环境安装](#9-本地环境安装)
- [10. 本地启动指南](#10-本地启动指南)
- [11. 当前已打通链路](#11-当前已打通链路)
- [12. 模块开发统一约定](#12-模块开发统一约定)
- [13. 简历解析与管理模块](#13-简历解析与管理模块)
- [14. 岗位匹配与分析模块](#14-岗位匹配与分析模块)
- [15. 其他核心模块规划](#15-其他核心模块规划)
- [16. 数据与业务流转关系](#16-数据与业务流转关系)
- [17. 开发排期与执行计划](#17-开发排期与执行计划)
- [18. 里程碑与验收标准](#18-里程碑与验收标准)
- [19. 日常开发命令](#19-日常开发命令)
- [20. 常见问题](#20-常见问题)
- [21. 当前最重要的结论](#21-当前最重要的结论)

---

## 1. 项目定位

**职点迷津（CareerPilot）** 是一个面向求职者的 **AI 求职工作台**。

它不是一个单点工具，而是围绕“用户从准备简历到完成求职闭环”的连续流程，构建的一套全栈系统。它的目标不是只解决“简历上传”或者“模拟面试”中的一个点，而是把这些能力连接起来，形成一个可持续使用的求职工作台。

它试图完成的完整链路是：

1. 用户建立账户与求职偏好。
2. 用户上传并沉淀自己的结构化简历资产。
3. 用户保存多个目标岗位 JD。
4. 系统完成简历与 JD 的可解释匹配分析。
5. 系统输出针对目标岗位的简历优化建议。
6. 系统围绕目标岗位进行模拟面试与复盘。
7. 用户持续记录投递状态，并在工作台中查看进展与待办。

因此，CareerPilot 更准确的产品定位是：

- 一个 **AI 驱动的求职工作台**
- 一个 **简历与岗位目标的数据中台**
- 一个 **围绕目标岗位持续训练与迭代的求职闭环系统**

---

## 2. 当前阶段判断

当前项目并不是“已经完成大半产品功能”，而是：

> **基础工程骨架已搭好，核心业务能力正处于逐步落地阶段。**

### 2.1 已经完成的部分

- 前端已有登录、注册、Dashboard 壳层与导航结构
- 后端已有认证主链路与基础测试
- 本地基础设施（PostgreSQL / Redis / MinIO）已准备好
- 项目文档已经把目标边界、模块职责与开发计划写得较清楚

### 2.2 尚未完成的部分

- 简历中心真实上传、解析、校正闭环
- JD 中心与岗位匹配闭环
- 简历优化建议闭环
- 模拟面试会话闭环
- 投递追踪与工作台真实聚合闭环
- AI 调用编排、异步任务、观测与部署能力

### 2.3 为什么这是一个好阶段

这个阶段反而很适合继续推进，因为：

- 技术栈已经明确，不需要再反复选型
- 路由和工程结构没有走偏
- 认证链路已跑通，具备真实业务落地前提
- 基础设施已经为文件上传、异步任务、AI 扩展预留空间
- 文档足够支撑按模块、有节奏地持续开发

---

## 3. 核心功能全景

CareerPilot 的产品能力可以概括为六大模块。

### 3.1 账户系统

负责整个工作台的用户身份与个性化上下文，是所有业务模块的基础入口。

包括：

- 注册
- 登录
- 登出
- 当前用户查询
- 个人资料维护
- 求职方向 / 目标城市 / 期望岗位等偏好设置

### 3.2 简历解析与管理

负责把 PDF 简历变成结构化、可编辑、可复用的简历资产。

包括：

- PDF 上传
- 文本抽取
- 结构化解析
- 人工校正
- 版本管理
- 向岗位匹配、优化建议、模拟面试等模块供数

### 3.3 岗位匹配与分析

负责把 JD 变成结构化岗位目标，并与结构化简历产生可解释的匹配报告。

包括：

- JD 手动录入
- JD 结构化
- 选择简历进行匹配
- 匹配评分
- 优势 / 短板 / 建议 / 证据输出
- 报告历史保存

### 3.4 简历优化建议

负责把岗位匹配结果转化成用户可以执行的修改动作。

包括：

- 面向特定 JD 生成简历优化建议
- 分模块输出建议
- 建议历史保存与复看

### 3.5 模拟面试

负责围绕目标岗位和用户简历，开展 AI 多轮面试训练与复盘。

包括：

- 选择岗位方向开始面试
- 多轮问答
- AI 追问
- 评分与点评
- 历史会话管理

### 3.6 投递追踪与复盘

负责将“分析能力”延伸成“求职过程管理能力”。

包括：

- 投递记录维护
- 阶段状态流转
- 更新时间与备注
- Dashboard 概览聚合
- 复盘沉淀

---

## 4. 当前仓库真实现状

### 4.1 当前仓库包含什么

当前仓库已经明确包含：

- `apps/api`：FastAPI 后端
- `apps/web`：Next.js 前端
- `docker-compose.middleware.yml`：本地中间件服务
- PostgreSQL / Redis / MinIO 本地启动能力
- README 与模块说明类文档

### 4.2 当前已落地能力

#### 后端已完成

- FastAPI 应用入口
- 认证接口：
  - `POST /auth/register`
  - `POST /auth/login`
  - `POST /auth/logout`
  - `GET /auth/me`
- 用户模型与迁移
- 密码哈希
- JWT 签发
- Redis token blocklist 登出机制
- 认证相关测试

#### 前端已完成

- 登录页
- 注册页
- 登录态恢复
- Dashboard 路由壳层
- 左侧导航
- 各模块占位页
- Tailwind + shadcn/ui 风格基线

### 4.3 当前主要缺口

当前最主要的缺口不是结构，而是业务能力尚未真正落地。主要包括：

- 简历上传、解析、编辑、版本化
- JD 录入、结构化、匹配报告
- 优化建议输出
- 面试会话、追问、评分
- 投递追踪页与概览聚合
- AI Provider 适配层
- 异步任务体系
- E2E 测试
- 部署、观测与告警

### 4.4 如何看待文档与代码

当前文档描述的是**目标蓝图**，代码呈现的是**当前真实实现**。

开发时应该坚持：

- 文档用于明确方向和边界
- 代码用于判断当前真实完成度
- 模块推进要以最小闭环为单位，不要试图一次性实现全部蓝图

---

## 5. 技术栈与基础设施

### 5.1 前端技术栈

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- shadcn/ui

### 5.2 后端技术栈

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- uv

### 5.3 基础设施

- PostgreSQL（镜像已带 pgvector）
- Redis
- MinIO
- Docker Compose

### 5.4 后续建议补齐能力

#### 前端建议补齐

- React Hook Form
- Zod
- TanStack Query
- 页面级 loading / empty / error 状态规范

#### 后端建议补齐

- 统一错误码
- 统一响应格式
- 文件上传模块
- AI Provider 适配层
- 任务状态模型
- 异步任务执行机制

#### 工程侧建议补齐

- GitHub Actions 或统一脚本
- `.env` 分层说明
- E2E 测试
- 部署文档
- 日志与监控策略

---

## 6. 项目结构说明

当前项目可以从下面几个层面理解：

```text
career-pilot/
├── apps/
│   ├── api/                    # FastAPI 后端
│   └── web/                    # Next.js 前端
├── docker-compose.middleware.yml
├── infra/
│   └── sql/
│       └── init.sql            # 仅本地引导参考，不再作为长期正式建表真源
└── docs / 文档体系              # 产品、开发、模块说明、计划书等
```

### 6.1 后端推荐分层

```text
apps/api/app/
├── api/routes/           # 对外接口
├── models/               # SQLAlchemy 模型
├── schemas/              # 请求/响应模型
├── services/             # 业务逻辑
├── core/                 # 配置、错误、响应、日志、安全
└── db/                   # 会话与基类
```

### 6.2 前端推荐分层

```text
apps/web/src/
  app/
    (marketing)/
    (auth)/
      login/page.tsx
      register/page.tsx
      layout.tsx
    (dashboard)/
      layout.tsx
      overview/page.tsx
      resume/page.tsx
      jobs/page.tsx
      applications/page.tsx
      interviews/page.tsx
      settings/page.tsx
  components/
    layout/
      app-shell.tsx
      app-sidebar.tsx
      app-header.tsx
      nav-main.tsx
      nav-user.tsx
    ui/
      sidebar.tsx
  config/
    nav-config.ts
  lib/
    route-access.ts
    api/
      client.ts
      contracts.ts
      modules/
```

---

## 7. 前端设计思想

本项目前端不适合走“页面上直接堆 JSX 的简易管理后台”路线，而更适合：

> **App Router + 可复用布局壳层 + 配置驱动导航 + 页面级状态规范**

### 7.1 为什么这样设计

因为当前项目前端特点是：

- 已经有登录页 / 注册页 / Dashboard 页族
- 后续会不断增加真实业务模块
- 左侧导航与头部壳层是公共能力
- 权限逻辑、菜单逻辑、显示逻辑不应混在页面里

### 7.2 Sidebar 设计原则

成熟项目的共同模式非常稳定：

1. `layout` 负责整体应用壳层。
2. 菜单数据使用配置驱动，而不是在组件里写死。
3. Sidebar 负责渲染，不承载业务判断。
4. 权限、Badge、Feature Flag 等业务规则单独管理。
5. 从一开始就考虑移动端抽屉态与折叠态。

### 7.3 CareerPilot 推荐前端结构决策

对于当前项目，最适合的落地方式是：

1. 以 `shadcn/ui sidebar` 作为基础组合件。
2. 使用本地 `config/nav-config.ts` 管理所有 dashboard 菜单。
3. 让 `src/app/(dashboard)/layout.tsx` 成为唯一挂载 sidebar 的入口。
4. 让 `login` / `register` 等页面处于独立 `(auth)` 路由组。
5. 为未来的角色控制、Badge、动态数量预留扩展口。

### 7.4 页面状态规范

页面级状态统一复用：

- `PageLoadingState`
- `PageEmptyState`
- `PageErrorState`

要求：

- 首屏数据加载必须有 loading 态
- 空状态必须有 empty 态
- 请求失败必须有 error 态和 retry 动作

### 7.5 Dashboard 复用规则

Dashboard 的公共壳层由以下能力组成：

- 左侧导航
- 顶部 Header
- 受保护路由
- 页面内容区

后续业务页面只负责内容区：

- 不重复写 sidebar
- 不重复写登录判断
- 不重复写通用头部
- 不直接改动全局布局，除非属于跨模块通用能力

---

## 8. 后端设计思想

后端当前已经具备继续扩展的好基础，因此不建议重构技术路线，而应该继续沿着当前分层补业务。

### 8.1 后端设计原则

1. **按层拆分，而不是把逻辑堆在路由里。**
2. **数据库结构以 Alembic 为长期真源。**
3. **统一错误响应与成功响应。**
4. **业务模块按 `routes / models / schemas / services` 成体系新增。**
5. **认证能力先保证可用，再逐步升级安全模型。**

### 8.2 当前认证方案的正确理解

目前后端生产骨架仍使用：

- access token
- 前端本地存储
- `/auth/logout` + token blocklist

它适合作为当前阶段的**可用方案**，但不是长期终态。后续更建议演进为：

1. access token + refresh token 双 token
2. refresh token 放在 httpOnly cookie
3. access token 短时效
4. 前端静默刷新

### 8.3 业务模块的正确扩展方式

后续所有模块都应遵循统一模式：

- 先定最小表结构
- 再定最小接口契约
- 再做页面骨架
- 最后接 AI 增强与复杂交互

---

## 9. 本地环境安装

适用对象：从 0 开始在本机搭建《职点迷津》开发环境。

### 9.1 推荐前置环境

建议本机具备：

- Docker Desktop
- uv
- Python 3.11
- Node.js 22+
- npm 10+
- pnpm（建议启用，便于后续前端统一管理）
- Homebrew（推荐）

### 9.2 推荐安装顺序

按下面顺序装最省事：

1. 安装 `Homebrew`
2. 安装并启动 `Docker Desktop`
3. 安装 `uv`
4. 用 `uv` 安装 `Python 3.11`
5. 启用 `pnpm`
6. 可选安装 `OCRmyPDF`

### 9.3 详细安装命令

#### 1）安装 Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

验证：

```bash
brew --version
```

#### 2）安装并启动 Docker Desktop

验证：

```bash
docker info
docker run --rm hello-world
```

#### 3）安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

验证：

```bash
uv --version
```

#### 4）用 uv 安装 Python 3.11

```bash
uv python install 3.11
uv python list
```

如需固定版本：

```bash
uv python pin 3.11
```

#### 5）启用 pnpm

```bash
corepack enable pnpm
corepack use pnpm@latest-10
```

验证：

```bash
pnpm --version
```

备用方式：

```bash
npm install -g pnpm@latest-10
```

#### 6）可选安装 OCRmyPDF

用于扫描版简历 PDF 的 OCR 兜底：

```bash
brew install ocrmypdf
brew install tesseract-lang
```

验证：

```bash
ocrmypdf --version
tesseract --version
```

### 9.4 当前不用单独安装到系统里的东西

现阶段可以先不单独装：

- PostgreSQL
- Redis
- MinIO
- psql
- redis-server

因为优先使用 Docker 方式启动。

### 9.5 一次性环境检查命令

```bash
brew --version
docker info
uv --version
uv python list
pnpm --version
node --version
npm --version
python3 --version
```

---

## 10. 本地启动指南

### 10.1 一次性初始化

#### 1）启动基础服务

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d
```

会启动：

- PostgreSQL：`localhost:5432`
- Redis：`localhost:6380`
- MinIO API：`http://localhost:9000`
- MinIO Console：`http://localhost:9001`

MinIO 默认账号：

- 用户名：`careerpilot`
- 密码：`careerpilot123`

查看状态：

```bash
docker compose -f docker-compose.middleware.yml ps
```

#### 2）初始化后端

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/api
cp .env.example .env
uv sync --group dev
uv run alembic upgrade head
```

说明：

- `.env` 负责数据库、Redis、JWT 等配置
- `alembic upgrade head` 创建当前后端所需表
- 长期数据库真源是 `apps/api/alembic/versions/`，不是 `infra/sql/init.sql`

#### 3）初始化前端

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
cp .env.example .env.local
npm install
```

说明：

- 当前仓库已验证启动命令以 **npm** 为准
- `NEXT_PUBLIC_API_BASE_URL` 默认应指向：`http://127.0.0.1:8000`
- `pnpm` 建议安装，但当前启动流程仍以 `npm` 命令最稳

### 10.2 全量启动方法

推荐开 3 个终端窗口。

#### 终端 1：基础服务

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d
```

#### 终端 2：后端 API

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/api
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

验证：

```bash
curl http://127.0.0.1:8000/health
```

预期：

```json
{"status":"ok"}
```

#### 终端 3：前端 Web

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
npm run dev
```

访问地址：

- 首页：`http://localhost:3000`
- 登录页：`http://localhost:3000/login`
- 注册页：`http://localhost:3000/register`

### 10.3 按模块单独启动

#### 只启动数据库和 Redis

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d postgres redis
```

#### 只启动 MinIO

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d minio
```

#### 只启动后端

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/api
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 只启动前端

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
npm run dev
```

---

## 11. 当前已打通链路

当前已明确打通的主链路是**登录注册与登录态恢复**。

### 11.1 后端接口

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /health`

### 11.2 前端页面

- `/register`
- `/login`
- `/`

### 11.3 登录态机制

- 注册成功后，前端保存 JWT
- 登录成功后，前端保存 JWT
- 页面刷新时，前端自动调用 `/auth/me` 恢复当前用户
- 退出时，前端调用 `/auth/logout`

这条链路已经为后续所有 Dashboard 业务模块提供了统一的身份上下文。

---

## 12. 模块开发统一约定

这部分是后续所有新模块的默认开发标准。

### 12.1 后端统一响应格式

成功响应：

```json
{
  "success": true,
  "data": {},
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-03-14T16:00:00Z"
  }
}
```

失败响应：

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": []
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-03-14T16:00:00Z"
  }
}
```

约定：

- `request_id` 由服务端统一生成，并写入响应头 `X-Request-ID`
- 前端错误提示优先读取 `error.message`
- 排障优先记录 `request_id`

### 12.2 错误码使用原则

推荐统一使用：

- `VALIDATION_ERROR`
- `AUTH_MISSING_TOKEN`
- `AUTH_TOKEN_EXPIRED`
- `AUTH_TOKEN_INVALID`
- `AUTH_TOKEN_REVOKED`
- `AUTH_INVALID_CREDENTIALS`
- `AUTH_USER_DISABLED`
- `USER_ALREADY_EXISTS`
- `CONFLICT`
- `INTERNAL_SERVER_ERROR`

### 12.3 后端模块目录规范

新增模块最少需要补齐：

```text
api/routes/{module}.py
models/{module}.py
schemas/{module}.py
services/{module}.py
tests/test_{module}.py
alembic/versions/..._{module}.py
```

推荐命名：

- 简历中心：`resume`
- 岗位匹配：`job`
- 投递追踪：`application`
- 模拟面试：`interview`

### 12.4 审计字段规范

业务表优先复用：

- `created_at`
- `updated_at`
- `created_by`
- `updated_by`

### 12.5 健康检查规范

统一提供：

- `GET /health`
- `GET /health/readiness`
- `GET /health/version`

语义：

- `health`：进程存活
- `readiness`：数据库与关键依赖是否就绪
- `version`：联调时确认环境与版本

### 12.6 前端 API 分层规范

页面和组件不要直接写 `fetch`，统一走：

```text
apps/web/src/lib/api/
├── client.ts             # 请求底座、错误解析
├── contracts.ts          # 响应契约类型
└── modules/
    ├── auth.ts
    ├── profile.ts
    └── future-module.ts
```

原则：

- 请求底座统一在 `client.ts`
- 每个业务模块单独一个 `modules/*.ts`
- 页面只调用模块函数，不关心响应包裹结构

### 12.7 路由守卫规范

推荐两类守卫：

- `ProtectedRoute`
  - 用于 Dashboard 与所有需登录页面
  - 未登录自动跳转 `/login?next=当前路径`
- `GuestRoute`
  - 用于 `/login`、`/register`
  - 已登录自动回到工作台

### 12.8 测试与验收约定

#### 后端

- 每新增一个路由模块，至少补一组 happy path 测试
- 认证相关接口必须覆盖未授权场景
- 新增迁移后至少跑一次 pytest

#### 前端

- 提交前至少执行 `npm run lint`
- 路由结构变动时必须执行 `npm run build`
- 首屏页面至少验证 loading / success / error 三种状态

---

## 13. 简历解析与管理模块

### 13.1 模块定位

“简历中心”不是单纯上传页，而是 CareerPilot 的：

> **简历数据入口与数据中台**

它的本质目标是把 PDF 简历变成：

- 可保存
- 可编辑
- 可复用
- 可供下游模块持续消费的结构化资产

其核心闭环为：

**上传 -> 解析 -> 展示 -> 校正 -> 复用**

### 13.2 模块职责

#### 上传

- 用户在 `/dashboard/resume` 上传 PDF 简历
- 校验文件格式与大小
- 保存到对象存储

#### 解析

- 抽取 PDF 原始文本 `raw_text`
- 转换为统一 `structured_json`

#### 展示

- 展示原始文本
- 展示解析状态
- 展示结构化结果
- 展示解析任务历史

#### 校正

- 用户人工修正教育、工作、项目、技能等字段
- 保存修正结果并形成可复用版本

#### 复用

- 给岗位匹配、简历优化、模拟面试等下游模块提供输入

### 13.3 核心功能总览

| 层次 | 核心功能 | 用户价值 | 状态定位 |
| --- | --- | --- | --- |
| 1 | 文件资产管理 | 上传、下载、删除、列表查看简历 | 必须完成 |
| 2 | 解析任务调度 | 自动解析、失败重试、任务历史追踪 | 必须完成 |
| 3 | 结构化数据沉淀 | 将 PDF 转为 `raw_text` 与 `structured_json` | 必须完成 |
| 4 | 人工校正与版本化 | 用户修正后形成可复用版本 | 必须完成 |
| 5 | 向下游能力供数 | 为岗位匹配、优化、面试提供结构化输入 | 必须完成 |

### 13.4 第一版结构化字段建议

```json
{
  "basic_info": {
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "summary": ""
  },
  "education": [],
  "work_experience": [],
  "projects": [],
  "skills": {
    "technical": [],
    "tools": [],
    "languages": []
  },
  "certifications": []
}
```

### 13.5 解析策略建议

第一版优先采用：

- 规则引擎
- 正则
- section heading 识别
- 关键词归类

先保证：

- 结果可解释
- 调试容易
- 失败原因可追踪

再逐步接入 AI 增强。

### 13.6 页面形态建议

建议 `/dashboard/resume` 第一版做成真实工作台：

- 左栏：上传卡片 + 简历列表
- 右栏顶部：状态、文件信息、重试解析、下载、删除、保存修正
- 右栏中部：原始文本预览、失败原因、解析历史
- 右栏底部：结构化编辑器

### 13.7 关键数据对象

核心表建议包括：

- `resumes`
- `resume_parse_jobs`
- 如需要更细粒度版本化，可扩展 `resume_versions`

关键字段包括：

- `file_name`
- `file_url`
- `raw_text`
- `structured_json`
- `parse_status`
- `latest_version`
- `status`
- `attempt_count`
- `error_message`
- `started_at`
- `finished_at`

---

## 14. 岗位匹配与分析模块

### 14.1 模块定位

岗位匹配模块不是一个单纯的 JD 录入页，也不是只返回一个分数的评分页，而是：

> **岗位目标管理与匹配判断中枢**

其核心闭环为：

**录入 JD -> 结构化 -> 选择简历 -> 生成匹配报告 -> 保存历史 -> 向下游复用**

### 14.2 模块目标

它主要解决以下问题：

1. 用户可以长期保存多个目标岗位 JD。
2. 用户可以判断“这份简历是否适合这个岗位”。
3. 系统可以输出可解释的匹配报告。
4. 下游的简历优化、模拟面试、投递追踪有了明确目标岗位输入。

### 14.3 第一版必须完成的能力

- JD 手动录入
- JD 列表 / 详情 / 编辑 / 删除
- JD 结构化提取
- 选择简历并生成匹配报告
- 报告展示总分、维度分、优势项、短板项、行动建议、证据摘要
- 历史报告保存与查看
- 在未配置模型 API 时，规则闭环仍能独立成立
- 在已配置模型 API 时，支持规则结果上的 AI 修正与解释增强

### 14.4 第一版暂不做

- 自动抓取招聘网站 JD
- AI 自动推荐岗位
- pgvector 参与匹配
- 多份简历批量比对同一 JD
- LLM 直接替代规则引擎裸打分

### 14.5 与简历中心的关系

岗位匹配模块直接建立在简历中心之上。

#### 上游输入

直接消费：

- `resumes.structured_json`
- `resumes.raw_text`
- 最新解析成功或人工修正后的简历版本

重点字段包括：

- `basic_info.summary`
- `education`
- `work_experience`
- `projects`
- `skills.technical`
- `skills.tools`
- `skills.languages`
- `certifications`

#### 下游供数

匹配报告会进一步供给：

- 简历优化
- 模拟面试
- 投递追踪

### 14.6 JD 第一版结构化字段建议

建议至少抽取：

- `basic`
- `requirements.required_skills`
- `requirements.preferred_skills`
- `requirements.required_keywords`
- `requirements.education`
- `requirements.experience_min_years`
- `responsibilities`
- `benefits`
- `raw_summary`

### 14.7 评分与运行模式原则

- **规则层必须独立成立**，不依赖模型也能输出完整结果
- **AI 层只做修正与增强**，不直接替代规则引擎
- **模型调用失败时自动降级** 到规则结果

推荐基础维度：

- 技能覆盖度
- 关键词命中度
- 经验年限粗匹配
- 教育要求匹配
- 城市 / 用工类型 / 其他基础约束匹配

### 14.8 页面建议

建议 `/dashboard/jobs` 第一版为：

- 左栏：JD 列表
- 中间：JD 详情与编辑区
- 右栏：匹配触发区与报告展示区

### 14.9 核心数据对象

建议包括：

- `job_descriptions`
- `match_reports`

`job_descriptions` 主要保存：

- `title`
- `company`
- `job_city`
- `employment_type`
- `source_name`
- `source_url`
- `jd_text`
- `parse_status`
- `parse_error`
- `structured_json`

`match_reports` 主要保存：

- `resume_id`
- `job_description_id`
- `rule_score`
- `model_score`
- `final_score`
- `dimension_scores`
- `strengths`
- `gaps`
- `suggestions`
- `evidence`
- `created_at`

---

## 15. 其他核心模块规划

### 15.1 简历优化建议

定位：

- 基于某份简历 + 某个 JD 的匹配报告
- 输出可执行的修改建议

要求：

- 不是泛泛聊天文本
- 要按模块给建议
- 要能保存与复看

建议数据对象：

- `optimization_reports`
- `project_scripts`

### 15.2 模拟面试

定位：

- 围绕岗位目标和简历内容，开展 AI 面试训练

核心目标：

- 多轮问答
- AI 追问
- 评分与点评
- 历史复盘

建议数据对象：

- `interview_sessions`
- `interview_turns`
- `interview_evaluations`

### 15.3 投递追踪与工作台概览

定位：

- 让用户不仅分析岗位，还能持续管理求职过程

核心目标：

- 记录岗位、阶段、更新时间、备注
- Dashboard 展示待办、最近投递、最近报告、待练习面试

建议数据对象：

- `applications`
- `application_events`

---

## 16. 数据与业务流转关系

整个 CareerPilot 的关键价值，在于不同模块之间不是孤立关系，而是数据逐层沉淀。

### 16.1 主链路

```text
用户账户 / 偏好
   -> 简历中心（简历资产）
   -> 岗位匹配（岗位目标 + 判断结果）
   -> 简历优化（改进建议）
   -> 模拟面试（训练与复盘）
   -> 投递追踪（过程管理）
```

### 16.2 为什么这个顺序很重要

因为如果没有：

- 结构化简历
- 结构化岗位目标
- 可保存的匹配结果

那么后续的优化建议、模拟面试、投递追踪都只能退化成“聊天式功能”，无法形成真正可持续的产品价值。

---

## 17. 开发排期与执行计划

当前更适合采用“先治理、再闭环、后增强”的推进节奏。

### 17.1 P0：基础治理补齐

目标：把当前认证骨架升级成可持续开发的基础盘。

前端任务：

- 建立 API 模块分层
- 增加路由守卫与未登录跳转规范
- 补 loading / empty / error 页面级组件
- 明确 Dashboard 公共布局复用规则

后端任务：

- 统一 API 错误码和响应格式
- 增加 health / readiness / version 等基础接口
- 增加请求日志、trace id、基础审计字段
- 规划业务模块目录

### 17.2 P1：最小业务闭环

- 简历上传与解析
- JD 录入与结构化
- 匹配评分与差距分析
- 简历优化建议

### 17.3 P2：增强闭环体验

- 投递追踪
- Dashboard 概览
- 个人信息与偏好

### 17.4 P3：AI 核心体验深化

- 模拟面试多轮对话
- 面试复盘与评分
- 历史记录和指标沉淀

### 17.5 推荐 8 周节奏

| 周次 | 目标 | 前端重点 | 后端重点 | 验收结果 |
| --- | --- | --- | --- | --- |
| 第 1 周 | 基础治理补齐 | 请求层、状态页、路由守卫 | 错误码、日志、模块规范 | 可以稳定开始做业务模块 |
| 第 2 周 | 账户系统加固 + 简历中心启动 | 个人信息页、简历页框架 | Profile 接口、上传接口、MinIO 接入 | 用户资料可维护，简历可上传 |
| 第 3 周 | 简历解析完成 | 简历列表、详情、解析结果展示 | 简历表、解析任务、详情接口 | 至少一份简历解析跑通 |
| 第 4 周 | JD 中心与匹配 | JD 录入、匹配结果页 | JD 表、匹配引擎、报告接口 | 简历和 JD 可生成匹配报告 |
| 第 5 周 | 优化建议 + 项目话术 | 优化建议页面 | 优化报告、项目话术生成 | 用户拿到可执行优化结果 |
| 第 6 周 | 投递追踪 + Dashboard | 概览页、投递记录页 | 投递表、概览聚合 | 工作台开始有真实运营价值 |
| 第 7 周 | 模拟面试 MVP | 会话页、历史页 | 会话接口、AI 问答、评分 | 至少一场完整面试练习可完成 |
| 第 8 周 | 稳定性与上线准备 | E2E、提示优化 | 安全、日志、部署文档 | 可以进行对外演示和内测 |

---

## 18. 里程碑与验收标准

### 18.1 里程碑 M1：基础盘稳定

- 认证稳定
- 个人资料可维护
- 文档与结构规范统一

### 18.2 里程碑 M2：求职分析闭环跑通

- 简历上传成功
- JD 录入成功
- 匹配报告生成成功
- 优化建议生成成功

### 18.3 里程碑 M3：工作台具备持续使用价值

- 投递追踪可用
- Dashboard 有真实数据
- 用户能持续回访

### 18.4 里程碑 M4：AI 面试体验成型

- 多轮面试可用
- 会话可复盘
- 输出有评分和建议

### 18.5 里程碑 M5：可演示、可部署、可继续扩展

- 部署文档可执行
- 核心流程可回归
- 风险项有记录

---

## 19. 日常开发命令

### 19.1 后端

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

静态检查：

```bash
uv run ruff check .
```

### 19.2 前端

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

### 19.3 停止项目

停止前端 / 后端：

```bash
Ctrl + C
```

停止基础服务：

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml down
```

同时删除卷：

```bash
docker compose -f docker-compose.middleware.yml down -v
```

---

## 20. 常见问题

### 20.1 `docker info` 报错

通常说明 Docker Desktop 没有启动。先打开 Docker Desktop，再重试。

### 20.2 前端能打开，但注册 / 登录失败

先检查：

```bash
curl http://127.0.0.1:8000/health
```

如果不通，说明后端没有启动成功。

### 20.3 数据库连不上

确认 PostgreSQL 是否正在运行：

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml ps
```

### 20.4 改了表结构之后怎么办

不要再把 `infra/sql/init.sql` 当成正式方案。正确做法是：

1. 在 `apps/api/alembic/versions/` 新增迁移
2. 执行 `uv run alembic upgrade head`

### 20.5 前端为什么既提到 `npm` 又提到 `pnpm`

当前仓库 README 的实际启动命令以 `npm` 为准，因此本地启动建议仍然使用 `npm install`、`npm run dev`。  
但从环境准备与后续工程统一角度，建议你同时启用 `pnpm`，为未来前端依赖管理标准化预留空间。

---

## 21. 当前最重要的结论

如果把整个项目压缩成几句最关键的判断，那么结论是：

1. **CareerPilot 的核心不是单个页面，而是求职全流程闭环。**
2. **当前项目最真实的状态是：基础骨架已成，业务能力待逐步落地。**
3. **最优开发顺序不是全面铺开，而是先治理、再跑通“简历中心 + 岗位匹配 + 优化建议”的最小闭环。**
4. **简历中心是简历资产中台，岗位匹配是岗位目标与判断中枢，这两个模块是整个产品最关键的中间层。**
5. **前端应坚持布局壳层复用、配置驱动导航、页面状态统一；后端应坚持分层、统一响应、Alembic 真源、模块化扩展。**
6. **本地开发当前最稳妥的运行方式是：Docker 起基础服务，uv 管后端，npm 跑前端。**
7. **中文 README 应成为当前项目的主说明文档，英文版仅保留参考价值。**

---

## 附：推荐启动顺序（最短实用版）

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

启动后优先打开：

- `http://localhost:3000/register`

先注册一个测试账号，再验证登录、退出和登录态恢复。
