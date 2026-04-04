# AGENTS.md

## Backend overview

This backend is a FastAPI service for Career Pilot.

It powers:

- authentication and user state
- profile management
- PDF resume upload and text extraction
- Markdown resume persistence and structured resume conversion
- target job description saving and parsing
- tailored resume generation and retry flow
- mock interview session creation, continuation, answering, ending, deletion, and retry

## Tech stack

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- MinIO

AI and document processing:

- PyMuPDF / pymupdf4llm for PDF extraction and Markdown conversion
- OpenAI-compatible / Anthropic-style model access for resume processing, tailored resume generation, and mock interview flows

## Directory guidance

Important areas:

- `app/core/`: config, security, response, error handling, logging
- `app/db/`: database setup and session management
- `app/models/`: SQLAlchemy models
- `app/prompts/`: prompt templates grouped by business domain
- `app/routers/`: API routes
- `app/schemas/`: Pydantic request/response schemas
- `app/services/`: business logic
- `tests/`: backend tests
- `alembic/versions/`: migration scripts

## How to work in backend

- Keep routers thin.
- Put business logic in services, not directly in route handlers.
- Keep schemas, models, and service contracts aligned.
- Preserve the workflow chain between master resume, job description, tailored resume, and mock interview.
- Prefer explicit domain logic over scattered utility shortcuts.

## API contract rules

- Do not change response shape casually.
- If a field name or response contract changes, check frontend impact immediately.
- Preserve backward compatibility unless the task explicitly requires a breaking change.
- Return clear state for long-running or retryable workflows.

## Domain rules

### Resume pipeline

The master resume is not just a stored file.
It becomes editable Markdown and then structured data reused by later workflows.

Any change in this area must preserve:

- PDF extraction
- Markdown editability
- persistence
- structured conversion for downstream reuse
- version-aware behavior where applicable

### Job description pipeline

Saved JD data must remain useful for:

- title extraction
- key info extraction
- later tailored resume and mock interview context

Do not reduce JD handling to plain text storage if downstream parsing depends on it.

### Tailored resume pipeline

This flow must support:

- generation start
- progress/status tracking
- completion
- failure or empty-result retry
- downloadable result
- handoff into mock interview

### Mock interview pipeline

This flow is session-based.
Preserve:

- session creation
- first-question preparation
- later-question preparation
- answer submission
- follow-up or next-question behavior
- review summary generation
- continue / end / delete / retry operations

## Prompt and AI integration rules

- Keep prompts organized by business domain under `app/prompts/`.
- When changing AI behavior, update the relevant prompt domain instead of scattering prompt text across services.
- Do not silently change provider assumptions without checking `.env` configuration usage.
- Keep provider integration compatible with the documented MiniMax or local OpenAI-compatible setup.

## Database and migration rules

- For model changes, add or update Alembic migrations.
- Do not edit historical migrations unless explicitly required.
- Keep schema changes minimal and well-justified.
- Prefer additive changes when possible.

## Storage and infrastructure rules

- Respect current usage of PostgreSQL, Redis, and MinIO.
- Do not hardcode environment-specific URLs, secrets, or credentials.
- Keep config centralized in the proper config layer.

## Ignore local runtime artifacts

Do not treat these as source of truth:

- `.venv/`
- `.uv-cache/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.env`
- `.tmp-auth-debug.db`

## Validation

Before finishing backend work, run the relevant commands:

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```
