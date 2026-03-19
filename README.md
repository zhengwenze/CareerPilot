# Career Pilot

求职工作台，帮助您高效管理求职流程。

## 项目结构

- **Backend**: `apps/backend` - FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: `apps/frontend` - Next.js 16 + React 19 + TypeScript
- **MiniProgram**: `apps/miniprogram` - 微信小程序

## 快速启动

### 方式一：Docker 一键启动（推荐）

```bash
docker compose -f docker-compose.yml up -d
```

所有服务将以后台模式启动：
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6380`
- MinIO: `localhost:9000` (API), `localhost:9001` (控制台)
- Backend: `localhost:8000`
- Frontend: `localhost:3000`

### 方式二：本地开发模式

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

后端 API 地址: `http://127.0.0.1:8000`

#### 3. 启动前端

```bash
cd apps/frontend
npm install
npm run dev
```

前端地址: `http://localhost:3000`

## 开发指南

### 查看服务状态

```bash
docker compose -f docker-compose.yml ps
```

### 查看日志

```bash
# 查看所有服务日志
docker compose -f docker-compose.yml logs -f

# 查看特定服务日志
docker compose -f docker-compose.yml logs -f backend
docker compose -f docker-compose.yml logs -f frontend
```

### 停止服务

```bash
docker compose -f docker-compose.yml down
```

### 重新构建镜像

```bash
docker compose -f docker-compose.yml up -d --build
```

## 环境变量

参考各服务目录下的 `.env.example` 文件配置环境变量。
