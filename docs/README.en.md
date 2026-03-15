# CareerPilot

CareerPilot is an AI-powered job search and mock interview platform. The current repository includes:

- `apps/api`: FastAPI backend, responsible for registration, login, logout, and current user endpoints
- `apps/web`: Next.js frontend, with login state and shadcn/ui integrated
- `docker-compose.middleware.yml`: Local middleware services, including PostgreSQL, Redis, and MinIO

If your goal is "to run the entire project locally", this README is all you need.

## Project Structure

```text
career-pilot/
├── apps/
│   ├── api/                    # FastAPI backend
│   └── web/                    # Next.js frontend
├── docker-compose.middleware.yml
├── infra/
│   └── sql/
│       └── init.sql            # For local setup reference only, not the long-term schema source
└── DEV_DOCUMENT.md             # Product/Architecture documentation
```

## Requirements

To run the project locally, your machine should have the following installed:

- `Docker Desktop` installed and running
- `uv` available
- `Python 3.11.15`
- `Node.js 22+`
- `npm 10+`

You can quickly check these with:

```bash
docker info
uv --version
python3 --version
node --version
npm --version
```

## Initial Setup

When you first clone the repository, follow this sequence to set up the project.

### 1. Start Middleware Services

Execute in the project root:

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d
```

This starts 3 local services:

- PostgreSQL: `localhost:5432`
- Redis: `localhost:6380`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

MinIO default credentials:

- Username: `careerpilot`
- Password: `careerpilot123`

Check service status:

```bash
docker compose -f docker-compose.middleware.yml ps
```

### 2. Initialize Backend

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/api
cp .env.example .env
uv sync --group dev
uv run alembic upgrade head
```

Notes:

- `.env` contains database, Redis, JWT, and other configurations
- `alembic upgrade head` creates the tables required by the current backend
- The long-term database schema source is `apps/api/alembic/versions/`, not `infra/sql/init.sql`

### 3. Initialize Frontend

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
cp .env.example .env.local
npm install
```

Notes:

- The most critical setting in `.env.local` is `NEXT_PUBLIC_API_BASE_URL`
- By default, it points to the local backend: `http://127.0.0.1:8000`

## Full Start Method

We recommend opening 3 terminal windows to run middleware services, backend, and frontend separately.

### Terminal 1: Middleware Services

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d
```

### Terminal 2: Backend API

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/api
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify backend is running:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### Terminal 3: Frontend Web

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
npm run dev
```

Access after startup:

- Homepage: <http://localhost:3000>
- Login page: <http://localhost:3000/login>
- Register page: <http://localhost:3000/register>

## Modular Startup

If you don't need to start everything every time, you can start components individually.

### Start Only Database and Redis

The current login/register module only depends on PostgreSQL and Redis. Minimal startup:

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d postgres redis
```

### Start Only MinIO

When you start working on resume upload, start MinIO separately:

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml up -d minio
```

### Start Only Backend

前提基础服务正在运行:

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/api
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Start Only Frontend

前提后端正在运行:

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
npm run dev
```

## How the Login/Register Flow Works

The current frontend and backend have integrated the following endpoints and pages:

### Backend Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /health`

### Frontend Pages

- `/register`
- `/login`
- `/`

### Authentication Flow

- After successful registration, the frontend saves the JWT
- After successful login, the frontend saves the JWT
- On page refresh, the frontend automatically calls `/auth/me` to restore the current user
- On logout, the frontend calls `/auth/logout`

## Common Development Commands

### Backend

Install dependencies:

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/api
uv sync --group dev
```

Run migrations:

```bash
uv run alembic upgrade head
```

Run tests:

```bash
uv run pytest
```

Run static checks:

```bash
uv run ruff check .
```

### Frontend

Install dependencies:

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot/apps/web
npm install
```

Local development:

```bash
npm run dev
```

Code linting:

```bash
npm run lint
```

Production build check:

```bash
npm run build
```

## Stopping the Project

### Stop Frontend

Press in the frontend terminal:

```bash
Ctrl + C
```

### Stop Backend

Press in the backend terminal:

```bash
Ctrl + C
```

### Stop Middleware Services

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml down
```

If you want to remove volumes as well:

```bash
docker compose -f docker-compose.middleware.yml down -v
```

## Common Issues

### 1. `docker info` Error

This means Docker Desktop is not running. Open Docker Desktop first, then retry.

### 2. Frontend Opens but Registration/Login Fails

First check:

```bash
curl http://127.0.0.1:8000/health
```

If this endpoint is not responding, the backend is not running successfully.

### 3. Database Connection Failed

Verify PostgreSQL is running:

```bash
cd /Users/zhengwenze/Desktop/codex/career-pilot
docker compose -f docker-compose.middleware.yml ps
```

### 4. After Modifying Table Structure

Do not manually edit `infra/sql/init.sql` as the official schema source. The correct approach is:

1. Add a new migration in `apps/api/alembic/versions/`
2. Run `uv run alembic upgrade head`

## Recommended Startup Sequence

For the most stable startup, follow this sequence:

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

After startup, open:

- <http://localhost:3000/register>

Register a test account first, then verify login, logout, and session restoration.
