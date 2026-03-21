# Career Pilot

求职工作台，帮助您高效管理求职流程。

## 快速启动

### Docker 一键启动（推荐）

```bash
docker compose -f docker-compose.yml up -d
```

服务地址：

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

中间件：

- PostgreSQL: localhost:5432
- Redis: localhost:6380
- MinIO: localhost:9000

### 本地开发模式

#### 1. 启动依赖服务

```bash
docker compose -f docker-compose.yml up -d postgres redis minio
```

#### 2. 启动后端

```bash
cd apps/backend
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

后端 API: http://127.0.0.1:8000

#### 3. 启动前端

```bash
cd apps/frontend
npm install
npm run dev
```

前端: http://localhost:3000

## 当前项目结构

```
career-pilot/
├── apps/
│   ├── backend/          # FastAPI 后端服务
│   │   ├── app/
│   │   │   ├── core/     # 核心配置（config, errors, security, logging）
│   │   │   ├── db/       # 数据库（base, session）
│   │   │   ├── models/   # 数据模型（resume, user, job, match_report...）
│   │   │   ├── routers/  # API 路由（auth, resumes, jobs, match_reports...）
│   │   │   ├── schemas/  # Pydantic schemas（请求/响应模型）
│   │   │   ├── services/ # 业务逻辑（resume_parser, resume_ai, match_engine...）
│   │   │   └── prompts/  # AI prompt 模板
│   │   ├── alembic/      # 数据库迁移
│   │   │   └── versions/ # 迁移历史
│   │   └── tests/        # 后端测试
│   │
│   ├── frontend/         # Next.js 前端
│   │   └── src/
│   │       ├── app/      # 页面路由（dashboard, login, register）
│   │       ├── components/# UI 组件（resume, jobs, layout, ui...）
│   │       └── lib/      # API 映射
│   │
│   └── miniprogram/      # 微信小程序
│       ├── pages/        # 页面
│       └── components/   # 组件
│
├── docker-compose.yml     # Docker 编排
└── docker-compose.middleware.yml # 中间件编排
```

## Docker 相关

```bash
# 查看服务状态
docker compose -f docker-compose.yml ps

# 查看日志
docker compose -f docker-compose.yml logs -f backend
docker compose -f docker-compose.yml logs -f frontend

# 停止服务
docker compose -f docker-compose.yml down

# 重新构建
docker compose -f docker-compose.yml up -d --build
```
