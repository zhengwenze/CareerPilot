# Career Pilot

求职工作台，帮助您高效管理求职流程。

## 项目结构

- **Backend**: `apps/backend` - FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: `apps/frontend` - Next.js 16 + React 19 + TypeScript
- **MiniProgram**: `apps/miniprogram` - 微信小程序

## 本地开发启动

### 启动依赖服务

```bash
docker compose -f docker-compose.yml up -d
```

### 启动后端

```bash
cd apps/backend
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

后端 API 地址: `http://localhost:8000`

### 启动前端

```bash
cd apps/frontend
npm install
npm run dev
```

前端地址: `http://localhost:3000`

## Docker 启动

```bash
docker compose -f docker-compose.yml up -d
```

所有服务将以后台模式启动：
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6380`
- MinIO: `localhost:9000` (API), `localhost:9001` (控制台)
- Backend: `localhost:8000`
- Frontend: `localhost:3000`

## 环境变量

参考各服务目录下的 `.env.example` 文件配置环境变量。
