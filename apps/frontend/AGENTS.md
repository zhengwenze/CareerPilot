# AGENTS.md

## Frontend overview

This frontend is a Next.js App Router application for Career Pilot.

Primary goals:

- support account access and dashboard navigation
- support resume upload, Markdown editing, preview, save, and tailored resume generation
- support entry into mock interview from successful tailored resume output
- preserve a continuous workspace feel rather than isolated feature pages

## Tech stack

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4

## Directory guidance

Important areas:

- `src/app/`: routes and page structure
- `src/app/(dashboard)/dashboard/`: authenticated dashboard routes
- `src/components/brutalist/`: foundational UI building blocks
- `src/components/dashboard/`: dashboard-specific UI
- `src/components/guards/`: auth / route guards
- `src/components/jobs/`: job-description workflow components
- `src/components/layout/`: shell layout, sidebar, topbar
- `src/components/resume/`: resume workflow components
- `src/components/ui/`: shared UI primitives
- `src/config/`: frontend config such as navigation
- `src/lib/api/`: API client and backend contract integration

## How to work in frontend

- Follow existing App Router patterns.
- Reuse existing UI primitives before creating new ones.
- Reuse layout, guard, and dashboard structures instead of bypassing them.
- Keep the experience consistent with a single workspace product, not a disconnected multi-page site.
- Prefer local component changes before introducing new abstractions.

## Product behavior constraints

The resume flow is not a static upload page.
It must support:

- upload
- extracted Markdown editing
- real-time preview
- save and continue editing later

The tailored resume flow is not just advice output.
It must support:

- generation state feedback
- retry when result is empty or failed
- download of resulting Markdown
- direct entry to mock interview when ready

The mock interview flow is not a one-off popup.
It is a session-based training workflow with creation, answering, continuation, ending, deletion, and retry behaviors.

Do not simplify these flows into shallow placeholder UIs.

## UI and state rules

- Preserve clear status feedback for async actions.
- Handle loading, empty, success, and failure states explicitly.
- Do not hide important workflow status behind subtle UI.
- Prefer straightforward state transitions over clever but opaque patterns.
- Maintain editability and preview clarity in resume-related screens.

## Styling rules

- Use existing Tailwind conventions already present in the codebase.
- Prefer consistency over novelty.
- Do not introduce an unrelated visual system without explicit request.
- Keep dashboard pages structured and task-oriented.
- Avoid turning work pages into overly decorative landing-page layouts.

## Routing and auth

- Respect route guards and authenticated dashboard boundaries.
- Do not bypass auth assumptions in dashboard pages.
- Keep login/register flows separate from authenticated dashboard experiences.

## API integration rules

- Keep frontend contract aligned with backend response shapes.
- Do not guess backend fields; inspect existing API usage first.
- If backend behavior changes, update affected client code in the same task.
- Handle polling, retries, and long-running generation states explicitly where the product workflow requires them.

## Ignore local build output

Do not treat these as source of truth:

- `.next/`
- `node_modules/`
- `.env.local`
- `tsconfig.tsbuildinfo`

## Validation

Before finishing frontend work, run the relevant checks:

```bash
npm install
npm run dev
```
