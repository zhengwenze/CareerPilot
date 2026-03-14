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

## Resume Module

The backend now includes the first MVP slice of the resume center:

- `POST /resumes/upload` - upload a PDF resume to MinIO and create a pending parse job
- `GET /resumes` - list the current user's resumes
- `GET /resumes/{resume_id}` - get resume detail
- `GET /resumes/{resume_id}/download-url` - generate a temporary download URL

### Required storage env vars

These values are already present in `.env.example` for local MinIO:

```bash
STORAGE_PROVIDER=minio
STORAGE_ENDPOINT=localhost:9000
STORAGE_ACCESS_KEY=careerpilot
STORAGE_SECRET_KEY=careerpilot123
STORAGE_BUCKET_NAME=career-pilot-resumes
STORAGE_USE_SSL=false
STORAGE_PRESIGNED_EXPIRE_SECONDS=3600
MAX_RESUME_FILE_SIZE_MB=10
```

### Local upload flow

1. Make sure `docker compose -f ../../docker-compose.middleware.yml up -d minio` is running
2. Run `uv run alembic upgrade head`
3. Start the API server
4. Call `POST /resumes/upload` with a multipart field named `file`

## Why Alembic Instead Of `init.sql`

`infra/sql/init.sql` is now only a local bootstrap reference. The long-term source of truth
for database schema lives in `alembic/versions/`, so all future table changes should be made
through Alembic migrations.
