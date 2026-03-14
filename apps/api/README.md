# CareerPilot API

FastAPI backend for CareerPilot.

## Quick Start

```bash
uv sync --group dev
docker compose -f ../../docker-compose.middleware.yml up -d
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The API will start on `http://127.0.0.1:8000`.

## Why Alembic Instead Of `init.sql`

`infra/sql/init.sql` is now only a local bootstrap reference. The long-term source of truth
for database schema lives in `alembic/versions/`, so all future table changes should be made
through Alembic migrations.
