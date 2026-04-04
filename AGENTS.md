# AGENTS.md

## Project overview

Career Pilot is an AI job-search workspace focused on continuous workflows, not a marketing site.

Core workflow:

1. Upload a master resume PDF
2. Convert it into editable Markdown
3. Save a target job description
4. Generate a tailored resume
5. Download the result or continue directly into mock interview

When making changes, preserve this workflow continuity. Do not treat features as isolated pages if they are part of the same user journey.

## Product intent

This repository solves three practical problems for job seekers:

- PDF resumes are hard to edit and customize
- Job descriptions and user experience lack an actionable optimization bridge
- Users often do not know how to continue from resume editing into interview practice

Prefer decisions that strengthen workflow continuity, data reuse, and clear task progression.

## Repository structure

Main applications:

- `apps/frontend`: Next.js frontend
- `apps/backend`: FastAPI backend
- `apps/miniprogram`: WeChat Mini Program

Agent-native support directories:

- `.agents/skills`: repo-local repeatable workflows for Codex
- `.agents/plans`: plan docs for complex or multi-step work
- `docs/`: durable project docs, workspace maps, and external-tool notes
- `demo/`: standalone prototypes and sample assets, not production source of truth
- `monochrome/`: design reference assets, not active frontend source by default

This repository currently needs AGENTS guidance for:

- root
- frontend
- backend

Do not add or rely on a Mini Program AGENTS.md unless explicitly requested.

## How to work in this repo

- Read this file before making cross-cutting changes.
- For repo-wide tasks, also read `docs/codex-workspace.md`.
- Prefer small, local, workflow-safe changes over broad refactors.
- Preserve the shared context between resume, job description, tailored resume, and mock interview.
- Do not invent product features that README marks as unfinished.
- Treat "settings" and "applications tracking" as existing page skeletons, not fully delivered features.
- Before changing architecture, inspect nearby code and match existing conventions.

## Navigation rules

When deciding where work belongs:

- put production product code under `apps/frontend` or `apps/backend`
- put repo-specific reusable agent workflows under `.agents/skills`
- put complex task plans under `.agents/plans`
- put stable documentation under `docs/`
- treat `demo/` as sandbox / reference material unless a task explicitly targets the demo
- treat `monochrome/` as design-system reference material unless a task explicitly needs it

Avoid adding new top-level directories when an existing lane already fits.

## Generated and local-only paths

These directories are useful locally but should not drive code understanding:

- `apps/frontend/.next/`
- `apps/frontend/node_modules/`
- `apps/backend/.venv/`
- `apps/backend/.uv-cache/`
- `apps/backend/.pytest_cache/`
- `apps/backend/.ruff_cache/`

Read source files before reading generated artifacts.

## Source of truth

For product behavior, trust the implemented workflow and current README.
Do not describe reserved pages or placeholder routes as completed functionality.

For workspace organization, trust:

1. this file
2. `docs/codex-workspace.md`
3. the nearest child `AGENTS.md`
4. repo-local skills in `.agents/skills/`

## Build and run

### Middleware services

Run required services first:

```bash
docker compose -f docker-compose.yml up -d postgres redis minio
```
