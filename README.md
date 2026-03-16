# 职点迷津（CareerPilot）

职点迷津（CareerPilot）是一个面向求职者的 **AI 求职工作台**。它不是单点工具，而是围绕“从简历准备到求职复盘”的连续流程，构建的一套全栈系统。它的目标不是只解决简历上传、岗位分析或模拟面试中的某一个点，而是把这些能力连接起来，形成一个可持续使用的求职闭环。

---

## 1. 项目简介

### 1.1 产品定位

1. 一个 **AI 驱动的求职工作台**
2. 一个 **简历与岗位目标的数据中台**
3. 一个 **围绕目标岗位持续训练与迭代的求职闭环系统**

### 1.2 目标用户

主要面向需要持续求职、反复优化简历、对多个目标岗位进行分析和准备的用户。

### 1.3 核心价值

完整链路：

1. 用户建立账户与求职偏好
2. 用户上传并沉淀结构化简历资产
3. 用户保存多个目标岗位 JD
4. 系统完成简历与 JD 的可解释匹配分析
5. 系统输出针对目标岗位的简历优化建议
6. 系统围绕目标岗位进行模拟面试与复盘
7. 用户持续记录投递状态，并在工作台中查看进展与待办

---

## 2. 当前项目状态

当前项目并不是“已经完成大半产品功能”，而是：

> **基础工程骨架已搭好，核心业务能力正处于逐步落地阶段。**

### 2.1 已完成能力

#### 前端

- 已有登录页、注册页
- 已有 Dashboard 路由壳层与左侧导航
- 已有各模块占位页
- 已具备基本登录态恢复能力
- 已建立 Tailwind + shadcn/ui 风格基线

#### 后端

- 已有 FastAPI 应用入口
- 已完成认证主链路：
  - `POST /auth/register`
  - `POST /auth/login`
  - `POST /auth/logout`
  - `GET /auth/me`
- 已有用户模型与迁移
- 已有密码哈希、JWT 签发、Redis token blocklist 登出机制
- 已有认证相关测试

#### 基础设施

- PostgreSQL / Redis / MinIO 本地启动能力已准备好
- Docker Compose 可启动本地中间件服务

### 2.2 当前主要缺口

当前最主要的缺口不是结构，而是业务能力尚未真正落地，包括：

- 简历中心上传、解析、校正、版本化闭环
- JD 录入、结构化、匹配报告闭环
- 简历优化建议闭环
- 模拟面试会话闭环
- 投递追踪与 Dashboard 聚合闭环
- AI Provider 适配层
- 异步任务体系
- E2E 测试
- 部署、观测与告警能力

### 2.3 当前阶段判断

这个阶段其实是一个很好的推进期，因为：

- 技术栈已经明确，不需要再反复选型
- 前后端路由和工程结构没有走偏
- 认证链路已跑通，具备真实业务落地前提
- 基础设施已经为文件上传、异步任务、AI 扩展预留空间
- 文档已经足够支撑按模块持续推进

一句话判断：

> **当前项目最真实的状态是：基础骨架已成，业务能力待逐步落地。**

---

## 3. 核心功能模块（先不做投递状态跟踪，涉及到与其他企业合作）

CareerPilot 的产品能力可概括为六大模块（先不做投递状态跟踪模块）

### 3.1 账户与偏好

负责整个工作台的身份体系与个性化上下文，是所有业务模块的统一入口。

包括：

- 注册
- 登录
- 登出
- 当前用户查询
- 个人资料维护
- 求职方向 / 目标城市 / 期望岗位等偏好设置

### 3.2 简历中心

负责把 PDF 简历变成结构化、可编辑、可复用的简历资产。

核心闭环：

**上传 -> 解析 -> 展示 -> 校正 -> 复用**

包括：

- PDF 上传
- 文本抽取
- 结构化解析
- 人工校正
- 版本管理
- 为岗位匹配、简历优化、模拟面试等模块供数

这个模块本质上不是一个上传页，而是：

> **简历数据入口与数据中台**

### 3.3 岗位匹配

负责把 JD 变成结构化岗位目标，并与结构化简历产生可解释的匹配报告。

核心闭环：

**录入 JD -> 结构化 -> 选择简历 -> 生成匹配报告 -> 保存历史 -> 向下游复用**

包括：

- JD 手动录入
- JD 结构化
- 选择简历进行匹配
- 匹配评分
- 优势 / 短板 / 建议 / 证据输出
- 报告历史保存

这个模块本质上不是一个录入页，也不是只返回一个分数，而是：

> **岗位目标管理与匹配判断中枢**

### 3.4 简历优化

负责把岗位匹配结果转化成用户可以执行的修改动作。

包括：

- 面向特定 JD 生成简历优化建议
- 按模块输出建议
- 建议历史保存与复看

要求：

- 不是泛泛聊天文本
- 必须可执行
- 必须可复看

### 3.5 模拟面试

负责围绕目标岗位和用户简历，开展 AI 多轮面试训练与复盘。

包括：

- 选择岗位方向开始面试
- 多轮问答
- AI 追问
- 评分与点评
- 历史会话管理

### 3.6 模块之间的主链路

```text
用户账户 / 偏好
   -> 简历中心（简历资产）
   -> 岗位匹配（岗位目标 + 判断结果）
   -> 简历优化（改进建议）
   -> 模拟面试（训练与复盘）
   -> 投递追踪（过程管理）
```

这个顺序很重要，因为如果没有：

- 结构化简历
- 结构化岗位目标
- 可保存的匹配结果

那么后续的优化建议、模拟面试、投递追踪都只能退化成“聊天式功能”，无法形成真正可持续的产品价值。

---

## 4. 技术架构与项目结构

### 4.1 当前仓库结构

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

### 4.2 技术栈

#### 前端

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- shadcn/ui

#### 后端

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- uv

#### 基础设施

- PostgreSQL（镜像已带 pgvector）
- Redis
- MinIO
- Docker Compose

### 4.3 后端推荐分层

```text
apps/api/app/
├── api/routes/           # 对外接口
├── models/               # SQLAlchemy 模型
├── schemas/              # 请求/响应模型
├── services/             # 业务逻辑
├── core/                 # 配置、错误、响应、日志、安全
└── db/                   # 会话与基类
```

### 4.4 前端推荐分层

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

### 4.5 前端设计原则

本项目前端更适合：

> **App Router + 可复用布局壳层 + 配置驱动导航 + 页面级状态规范**

原则如下：

1. `layout` 负责应用壳层
2. 菜单数据使用配置驱动，而不是在组件里写死
3. Sidebar 只负责渲染，不承载业务判断
4. 权限、Badge、Feature Flag 等规则单独管理
5. 从一开始考虑折叠态与移动端抽屉态
6. Dashboard 页面只负责内容区，不重复写公共壳层

页面级状态统一复用：

- `PageLoadingState`
- `PageEmptyState`
- `PageErrorState`

要求：

- 首屏数据加载必须有 loading 态
- 空状态必须有 empty 态
- 请求失败必须有 error 态和 retry 动作

### 4.6 后端设计原则

1. **按层拆分，而不是把逻辑堆在路由里**
2. **数据库结构以 Alembic 为长期真源**
3. **统一错误响应与成功响应**
4. **业务模块按 `routes / models / schemas / services` 成体系新增**
5. **认证能力先保证可用，再逐步升级安全模型**

### 4.7 当前认证方案的正确理解

当前后端骨架仍使用：

- access token
- 前端本地存储
- `/auth/logout` + token blocklist

它适合作为当前阶段的 **可用方案**，但不是长期终态。后续建议逐步演进为：

1. access token + refresh token 双 token
2. refresh token 放在 httpOnly cookie
3. access token 短时效
4. 前端静默刷新

### 4.8 当前工程侧建议补齐能力

#### 前端建议补齐

- React Hook Form
- Zod
- TanStack Query

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

## 5. 本地开发与启动

### 5.1 推荐前置环境

建议本机具备：

- Docker Desktop
- uv
- Python 3.11
- Node.js 22+
- npm 10+
- pnpm（建议启用，便于后续前端统一管理）
- Homebrew（推荐）

现阶段可以先不单独安装到系统里的东西：

- PostgreSQL
- Redis
- MinIO
- psql
- redis-server

因为当前优先使用 Docker 方式启动。

### 5.2 一次性环境检查

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

### 5.3 一次性初始化

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

### 5.4 全量启动方法

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
{ "status": "ok" }
```

#### 终端 3：前端 Web

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
npm run dev
```

访问：

- 前端：`http://127.0.0.1:3000`
- 后端文档：`http://127.0.0.1:8000/docs`

### 5.5 常用命令

#### 后端

```bash
uv run pytest
uv run alembic current
uv run alembic history
uv run alembic revision --autogenerate -m "message"
```

#### 前端

```bash
npm run dev
npm run build
npm run lint
```

### 5.6 常见问题

#### 问题 1：前端能打开，但请求后端失败

检查：

- 后端是否已启动在 `127.0.0.1:8000`
- `.env.local` 中 `NEXT_PUBLIC_API_BASE_URL` 是否正确
- 浏览器 Network 中接口地址是否打到错误端口

#### 问题 2：数据库迁移执行失败

检查：

- PostgreSQL 容器是否正常启动
- `.env` 中数据库连接串是否正确
- 本地端口 `5432` 是否冲突

#### 问题 3：登出后仍像是登录状态

因为当前采用本地 token 存储方式，需确认：

- 前端是否正确清理本地 token
- 后端是否成功写入 Redis blocklist
- `/auth/me` 是否仍发送旧 token

---

## 6. 当前优先开发闭环

当前阶段最重要的不是把所有模块同时铺开，而是先跑通一个真正可用的业务闭环。

### 6.1 为什么不能平均推进所有模块

因为如果同时推进：

- 简历中心
- 岗位匹配
- 简历优化
- 模拟面试
- 投递追踪

很容易出现：

- 每个页面都“看起来有”
- 每个模块都“不完整”
- 到最后仍没有任何一个用户价值完整闭环

### 6.2 当前最合理的第一阶段目标

建议优先跑通：

```text
认证
  -> 简历中心
  -> 岗位匹配
  -> 简历优化
```

这是最小但最有价值的闭环，因为它直接对应求职者最核心的问题：

> **我现在这份简历，面对这个岗位，差在哪里，我该怎么改。**

### 6.3 推荐推进顺序

#### P0：工程治理与统一约定

先补齐：

- 统一响应格式
- 统一错误码
- 前端 API client / contract
- 环境变量说明
- 页面通用状态组件
- 基础测试脚手架

#### P1：简历中心闭环

先做：

- 上传文件
- 存储文件
- 抽取文本
- 结构化解析
- 详情页展示
- 人工校正
- 历史记录

#### P2：岗位匹配闭环

再做：

- JD 录入
- JD 结构化
- 选择简历进行匹配
- 输出匹配报告
- 保存报告历史

#### P3：简历优化闭环

再做：

- 基于匹配结果生成优化建议
- 生成建议历史
- 支持反复查看

#### P4：面试与投递扩展

在前面闭环稳定后，再进入：

- 模拟面试
- 投递追踪
- Dashboard 聚合

### 6.4 当前最重要的产品判断

现阶段最关键的是牢记：

> **CareerPilot 的核心竞争力不是模块数量，而是闭环质量。**

先把第一个闭环做深、做稳、做可复用，后续模块会更容易接上。

---

## 7. 开发规范

### 7.1 API 响应格式建议

成功响应建议统一为：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

失败响应建议统一为：

```json
{
  "code": 40001,
  "message": "invalid params",
  "details": {}
}
```

### 7.2 错误码建议

建议错误码按区间治理：

- `0`：成功
- `4xxxx`：客户端请求问题
- `401xx`：认证与授权问题
- `404xx`：资源不存在
- `5xxxx`：服务端错误

### 7.3 模块新增规范

后端新增业务模块时，尽量按以下结构组织：

```text
routes -> schemas -> services -> models
```

前端新增业务模块时，尽量按以下思路组织：

```text
page -> feature components -> api module -> contracts/types
```

### 7.4 数据库规范

- 正式表结构变更一律通过 Alembic 管理
- 不再把 `infra/sql/init.sql` 作为长期真源
- 迁移脚本必须可回放、可审计

### 7.5 路由与登录态规范

- 公共路由与受保护路由分组管理
- Dashboard 下页面默认走鉴权保护
- 未登录访问受保护页面时统一重定向登录
- 登录后恢复原目标页面

### 7.6 页面状态规范

每个数据页都应明确处理：

- loading
- empty
- error
- retry

不要让页面只存在“成功态”。

### 7.7 测试建议

当前最少应保证：

- 认证相关后端测试稳定通过
- 新增业务接口具备基础单测
- 关键主链路具备 E2E 测试计划

### 7.8 健康检查与可观测性建议

至少保留：

- `/health`
- 错误日志
- 请求日志
- 关键异步任务状态追踪

后续再逐步补齐：

- tracing
- metrics
- 统一监控告警

---

## 8. Roadmap 与里程碑

### 8.1 路线图

#### 第一阶段：把基础做稳

目标：

- 统一工程约定
- 保证本地可稳定启动
- 保证认证链路长期可用
- 为业务模块落地清障

#### 第二阶段：打通第一条业务闭环

目标：

- 完成简历中心闭环
- 完成岗位匹配闭环
- 完成简历优化闭环

#### 第三阶段：做强求职训练能力

目标：

- 上线模拟面试
- 形成面试训练与复盘沉淀

#### 第四阶段：补全过程管理能力

目标：

- 上线投递追踪
- 完成 Dashboard 聚合
- 形成完整求职工作台

### 8.2 关键里程碑

#### M1：工程底座稳定

验收标准：

- 前后端可一键本地启动
- 认证接口可稳定调用
- 基础环境说明清晰
- 迁移脚本可持续演进

#### M2：简历中心可用

验收标准：

- 用户可上传简历
- 系统可解析与展示
- 用户可人工修正
- 简历可被后续模块复用

#### M3：岗位匹配可用

验收标准：

- 用户可录入 JD
- 系统可生成结构化匹配报告
- 报告可被保存和复查

#### M4：简历优化可用

验收标准：

- 用户可基于匹配结果获得可执行建议
- 建议可保存、可复看

#### M5：求职工作台闭环成型

验收标准：

- 面试训练可用
- 投递追踪可用
- Dashboard 能反映关键求职状态

### 8.3 当前最重要的结论

这份项目当前最应该坚持的方向，不是继续扩目录、扩章节、扩模块说明，而是：

> **围绕最小可用闭环持续推进，让每一个新增模块都真正接到主链路上。**

README 的职责也应保持克制：

- 说清项目是什么
- 说清现在做到哪
- 说清怎么启动
- 说清下一步最该做什么

其余更细的设计、字段、流程、计划，建议逐步下沉到 `docs/` 中维护。

---

## 总结

CareerPilot 当前已经具备一个不错的起点：

- 技术栈明确
- 工程结构清晰
- 认证链路可用
- 基础设施已就位

接下来的关键不是“做更多页面”，而是：

> **优先打通“简历中心 -> 岗位匹配 -> 简历优化”这条最有价值的业务主链路。**

只要第一条闭环跑通，CareerPilot 就会从“一个工程骨架”真正进入“一个有产品价值的 AI 求职工作台”。
