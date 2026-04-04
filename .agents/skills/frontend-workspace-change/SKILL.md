---
name: frontend-workspace-change
description: Use this skill when changing the Next.js workspace UI, especially resume, JD, tailored resume, or mock interview flows inside the authenticated dashboard.
---

# Frontend Workspace Change

Use this skill when a task touches `apps/frontend/`.

## Goals

- preserve the single-workspace feel of Career Pilot
- keep resume, job description, tailored resume, and mock interview connected
- avoid turning workflow screens into isolated marketing-style pages

## Read first

1. `AGENTS.md`
2. `docs/codex-workspace.md`
3. `apps/frontend/AGENTS.md`
4. the relevant route, component, and API module

## Working rules

- inspect existing route and layout structure before adding components
- prefer editing existing dashboard and workflow components over adding parallel abstractions
- keep async states explicit: loading, empty, success, failure, retry
- if backend contract assumptions change, update the affected API client and UI in the same task
- preserve the handoff from tailored resume output into mock interview entry

## Validation

Run the narrowest useful check in `apps/frontend/`:

```bash
npm run dev
```
