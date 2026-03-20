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
