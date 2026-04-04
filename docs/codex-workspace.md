# Codex Workspace Map

## Purpose

This repository is organized for continuous Codex-assisted work, not just one-off code edits.

The goal is to make these layers explicit:

- product code
- repo rules
- reusable agent workflows
- plan documents
- external-tool notes
- reference-only assets

## Top-level map

### Product code

- `apps/frontend/`: Next.js workspace UI
- `apps/backend/`: FastAPI API, services, models, and migrations
- `apps/miniprogram/`: WeChat Mini Program

### Agent-native project assets

- `AGENTS.md`: root-level behavior, workflow, and repo navigation rules
- `.agents/skills/`: repeatable repo-local workflows
- `.agents/plans/`: feature plans, migration plans, and investigation plans
- `docs/`: stable documentation that should outlive a single coding session

### Reference-only assets

- `demo/`: standalone scripts, sample resumes, prompt experiments, and console demos
- `monochrome/`: design tokens and theme references

These reference directories are useful, but they are not the source of truth for shipped product behavior.

## Where new work should go

Use the narrowest directory that matches the task:

- frontend UI, routes, client state, and API clients: `apps/frontend/`
- backend routes, services, models, schemas, prompts, migrations: `apps/backend/`
- reusable Codex workflow instructions: `.agents/skills/<skill-name>/SKILL.md`
- multi-step plans or investigations: `.agents/plans/`
- durable architecture, runbooks, and setup notes: `docs/`

Avoid creating new top-level directories when one of these lanes already fits.

## Repository reading order

For cross-cutting tasks, read in this order:

1. `AGENTS.md`
2. `docs/codex-workspace.md`
3. the nearest child `AGENTS.md`
4. relevant `.agents/skills/*/SKILL.md`
5. product code in the affected app

## Generated paths to ignore first

These paths are local runtime artifacts and should not be used to infer architecture:

- `apps/frontend/.next/`
- `apps/frontend/node_modules/`
- `apps/backend/.venv/`
- `apps/backend/.uv-cache/`
- `apps/backend/.pytest_cache/`
- `apps/backend/.ruff_cache/`

## Recommended plan naming

Store complex work in `.agents/plans/` using concise, searchable names:

- `resume-pipeline-hardening.md`
- `tailored-resume-retry-fix.md`
- `mock-interview-session-rework.md`

Prefer one problem per plan document.

## Recommended subagent split

When parallelizing work, split by stable ownership boundaries:

- frontend worker: `apps/frontend`
- backend worker: `apps/backend`
- docs / workflow worker: `docs` and `.agents`

Do not split one small feature across several workers unless the write scopes are disjoint.
