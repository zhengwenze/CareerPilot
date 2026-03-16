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

可以。

我能理解这张参考图的核心设计语言，并帮你提炼成适合给 AI 生成前端页面的提示词。

我先帮你拆解这张图的视觉特征，再给你一版高质量提示词。

这张参考图的界面特征大致是：

- **整体风格**：典型苹果官网式极简设计，留白很多，秩序感强
- **主色调**：大面积白色/浅灰白背景
- **字体**：全部黑色，标题粗体，大字高对比
- **按钮**：苹果风格蓝色主按钮，圆角胶囊按钮
- **布局**：顶部导航 + 中央 Hero 主视觉区域
- **信息层级**：品牌标题最大，副标题次之，按钮第三层
- **产品展示**：中间大图居中，突出产品主体
- **页面气质**：干净、高级、科技感、克制、不花哨

下面是我给你整理好的**可直接用于生成前端界面**的提示词。

---

## 通用中文提示词

请生成一个 **苹果官网风格的前端落地页首页**，整体设计要求极简、高级、留白充足、科技感强。

具体要求如下：

- 页面整体采用 **白色为主色调**
- **所有文字必须使用黑色**
- 功能按钮使用 **苹果风格蓝色**
- 顶部为简洁的横向导航栏，导航文字黑色，背景白色
- 首屏为居中的 Hero 区域
- 主标题使用超大号黑色粗体字体，视觉中心明确
- 副标题使用较小一号黑色字体，简洁有力
- 标题下方放置两个操作按钮：

  - 主按钮：蓝色实心圆角按钮
  - 次按钮：白底蓝边框圆角按钮

- 中间展示一张大尺寸产品图，居中排版，突出产品主体
- 整体布局对齐工整，留白充足，风格接近 Apple 官网
- 不要复杂装饰，不要渐变背景，不要杂乱配色
- 设计重点是 **简洁、克制、高级、现代**
- 页面需具备优秀的响应式表现，桌面端优先
- 字体风格参考苹果官网，现代无衬线字体
- 按钮、间距、圆角、排版都要体现苹果设计语言

---

## 更适合 AI 代码生成的提示词

生成一个 **Apple 风格的产品官网首页前端页面**，使用现代极简设计语言。

设计规范：

- Background: pure white
- Text color: black only
- Primary action buttons: Apple-style blue
- Layout: clean, centered, spacious, minimal
- Top navigation bar: white background, black text, simple horizontal menu
- Hero section:

  - very large bold black headline
  - medium-size black subheadline
  - two CTA buttons below headline

- Buttons:

  - primary button: filled blue, pill-shaped, elegant hover effect
  - secondary button: white background, blue border, blue text, pill-shaped

- Product image centered below text
- Large whitespace, premium composition, perfect alignment
- Overall feel: premium, futuristic, calm, minimal, Apple.com inspired
- No clutter, no dark theme, no colorful decorations
- Typography should look like SF Pro / Apple-style sans-serif
- Responsive and production-quality UI

---

## 如果你要给 AI 画图/出设计稿，用这个版本

设计一个 **苹果官网风格的产品展示页面**：

- 白色背景
- 黑色字体
- 蓝色操作按钮
- 顶部极简导航栏
- 中间大标题 + 副标题 + 双按钮
- 下方展示产品主图
- 风格高级、极简、留白充足
- 视觉干净、现代、科技感强
- 类似 Apple 官网新品发布页的首屏视觉
- 强调居中构图、超大标题、精致圆角按钮、整洁间距

---

## 如果你要生成 HTML/CSS/React 页面，我建议再加这段约束

请输出高质量前端代码，并满足以下要求：

- 使用现代响应式布局
- 代码结构清晰，组件化
- 视觉高度还原苹果官网风格
- 不使用复杂炫技动画
- Hover 效果克制自然
- 按钮圆角较大，具有苹果官网质感
- 页面宽度、间距、字号比例协调
- 优先保证简洁与高级感

---

## 一版更精炼的最终提示词

仿照苹果官网设计一个极简产品首页，整体以白色为主色调，所有文字使用黑色，功能按钮使用苹果风格蓝色。页面包含顶部白色导航栏、中央 Hero 区域、超大黑色粗体标题、黑色副标题、两个圆角操作按钮，以及下方居中的产品展示图。整体风格要求高级、简洁、现代、留白充足、排版工整，具有 Apple 官网式的科技感与秩序感。桌面端优先，支持响应式布局。

---

如果你愿意，我下一步可以直接帮你继续输出一版：
**“适合 Cursor / v0 / Lovable / Bolt / ChatGPT 生成网页的完整提示词”**，或者直接给你一份 **HTML + CSS / React 版页面代码提示词**。

确认产品主链路本来就是“简历中心 -> 岗位匹配 -> 简历优化 -> 模拟面试”的闭环。
把当前岗位匹配模块的骨架摸清了：
后端已有 job_descriptions 和 match_reports 两张表
JD 解析目前是规则提取，不是异步任务
匹配报告目前是“规则分 + AI 修正分”的一次性报告
前端已经有岗位页和匹配报告面板，但能力还偏单次分析，不是“岗位目标管理中枢”
我现在正继续读前端岗位页、简历结构数据和模拟面试占位页，接着会补一轮竞品/开源方案调研，然后给你出完整的《岗位匹配模块》重设计方案，包括它如何和简历解析、后续模拟面试形成联动闭环。

我继续补前端和测试侧证据，重点看现在岗位页承载了什么、报告展示了什么、以及模拟面试模块当前预留到什么程度。这样设计方案就不会脱离现有代码。

本地代码已经足够说明“现在有什么”。我再补一轮外部证据，重点看两类：现成求职工作台产品怎么做闭环，以及 GitHub 上有没有值得借鉴的数据模型或流程组织。

现有代码和外部样本都说明了一点：岗位匹配如果只做“打分报告”，价值会很快见顶；真正拉开差距的是它是否成为后续简历优化、模拟面试的“任务编排中心”。我还差两项产品取舍需要你拍板，这会直接影响方案颗粒度和模块边界。

外部样本已经够用了，结论很一致：行业里成熟做法都不是“只给一个分数”，而是把岗位匹配当作后续简历裁剪、题库生成、训练反馈的上游上下文。我再补最后一块代码事实：当前 AI 在本项目里到底只承担了什么角色。

还剩一个会改变方案范围的关键点：岗位匹配是只服务“已拿到的目标 JD”，还是要同时承接“找岗位/导入岗位”。这个会直接影响数据模型和页面结构，我建议现在定掉。

编写计划

《岗位匹配模块》重设计方案：从“打分页”升级为“求职闭环中枢”
Summary
当前基线已经明确：后端是同步 JD 结构化 + 一次性匹配报告，前端是“JD 编辑 + 报告查看”页，核心代码集中在 job.py、match_engine.py、page.tsx。
本次重设计的定位已锁定为“闭环中枢 + 深度联动模拟面试 + 手动录入 JD 为主”。
模块目标不再是“生成一个分数”，而是沉淀 4 个可复用资产：岗位目标(Job Target)、匹配快照(Match Snapshot)、简历定制任务(Resume Tailoring Plan)、面试蓝图(Interview Blueprint)。
主链路改为：简历解析成功 -> 选择目标岗位 -> 生成匹配快照 -> 产出改简历任务 -> 产出面试题包/追问点 -> 面试反馈回流岗位准备度 -> 触发再次匹配。
外部参考信号：成熟产品都在强化“岗位上下文复用”而不是只做 ATS 分数，例如 Teal Match Resume to Job Description、Teal Interview Practice、Jobscan Resume Scanner，以及开源方向上的 CareerCopilot 与 FoloUp。
Key Changes
把“岗位匹配”重新定义为“目标岗位工作台”，每个岗位记录都要有 岗位画像、匹配历史、改简历任务、面试准备包、当前准备度 五个视角。
job_descriptions 保留为主表，但其 structured_json 升级为更完整的岗位画像：basic、requirements、responsibilities、signals、competencies、interview_focus、parse_confidence、normalization_warnings。
新增 job_parse_jobs，状态流转与简历解析对齐：pending -> processing -> success|failed。JD 结构化不再视为瞬时动作，而是可追踪、可重试、可排障的异步链路。
保留现有 match_reports 路径与表名以减少破坏性改动，但语义升级为“匹配快照”。它必须变成异步生成资产，status 字段真正参与流转，而不是只存 success。
match_reports 新增或扩展这些字段/JSON：resume_version、resume_snapshot_json、job_snapshot_json、tailoring_plan_json、interview_blueprint_json、readiness_status、staleness_status。
匹配生成规则固定为“一次生成三份结果”：scorecard、tailoring plan、interview blueprint。不拆成多个前台按钮，避免用户重复等待和下游模块再做一遍理解。
resume_tailoring_plan 的输出结构固定为：must_fix_gaps、nice_to_have_gaps、missing_evidence、rewrite_suggestions、section_targets、next_actions。它直接服务后续简历优化模块。
interview_blueprint 的输出结构固定为：focus_competencies、question_pack、follow_up_prompts、evidence_to_probe、rubric、opening_brief。它直接服务后续模拟面试模块。
岗位准备度采用统一状态：needs_resume_fix、ready_for_mock_interview、interview_in_progress、ready_to_apply。来源是“最新成功匹配快照 + 最近一次模拟面试反馈”。
简历模块联动规则固定：只有 parse_status=success 的简历可参与匹配；每次匹配必须绑定 resume_id + resume_version；简历被用户编辑保存成新版本后，旧匹配快照自动标记 stale，岗位页显示“建议重新匹配”。
模拟面试模块联动规则固定：面试入口必须从 match_report_id 启动，而不是只传 job_id；这样题目、追问、评分维度都能绑定到具体岗位要求和具体简历版本。
模拟面试回流规则固定：面试结束后写回结构化摘要到匹配快照关联上下文，至少包含 competency_scores、weak_answers、missing_examples、suggested_resume_evidence；岗位页据此更新准备度和下一步动作。
前端岗位页改为单页工作台，不再把“历史报告列表”放成主视图。信息架构固定为：左侧 岗位列表，中间 岗位画像/匹配结果 Tabs，右侧 下一步动作。
中间 Tabs 固定为 4 个：岗位画像、匹配得分、改简历、面试准备。历史匹配快照收进二级抽屉或历史下拉，不抢主焦点。
右侧动作面板固定只保留高价值 CTA：去简历优化、开始模拟面试、重新匹配最新简历版本、查看历史变化。
保留当前苹果风格 UI 约束：白底、黑字、蓝色主按钮、克制卡片；但岗位页要更“任务驱动”，减少纯展示块。
Public APIs / Interfaces
POST /jobs 保留，继续
