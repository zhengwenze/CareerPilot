---
name: backend-api-change
description: Use this skill when changing FastAPI routes, schemas, services, models, prompts, or migrations in the Career Pilot backend.
---

# Backend API Change

Use this skill when a task touches `apps/backend/`.

## Goals

- keep routers thin and services authoritative
- preserve contract continuity between resume, JD, tailored resume, and mock interview workflows
- avoid backend changes that silently break the frontend

## Read first

1. `AGENTS.md`
2. `docs/codex-workspace.md`
3. `apps/backend/AGENTS.md`
4. the affected router, schema, service, model, and prompt files

## Working rules

- trace the full path before editing: router -> schema -> service -> model / prompt
- if request or response fields change, inspect frontend impact in the same task
- add a migration for schema changes instead of silently relying on ORM drift
- keep prompt text inside `app/prompts/`, not scattered in services
- preserve retryable and long-running workflow state where the product depends on it

## Validation

Run the narrowest useful check in `apps/backend/`:

```bash
uv run alembic upgrade head
uv run pytest
```
