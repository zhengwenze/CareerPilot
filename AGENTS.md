# AGENTS.md

## Project overview

Career Pilot is an AI job-search workspace focused on continuous workflows, not a marketing site.

Core workflow:

1. Upload a master resume
2. Convert it into editable Markdown
3. Save a target job description
4. Generate a tailored resume
5. Continue directly into mock interview
6. Reuse data across the workflow instead of re-entering context repeatedly

When making changes, preserve this workflow continuity. Do not treat features as isolated pages if they are part of the same user journey.

## Product intent

This repository solves practical problems for job seekers:

- resumes are hard to edit and customize across applications
- job descriptions and resumes often lack an actionable optimization bridge
- users often do not know how to continue from resume editing into interview practice
- interview practice is more valuable when it can reuse existing resume and target-job context

Prefer decisions that strengthen workflow continuity, data reuse, clear task progression, and practical MVP delivery.

## Repository structure

Main applications:

- `apps/frontend`: Next.js frontend
- `apps/backend`: FastAPI backend
- `apps/miniprogram`: WeChat Mini Program

Agent-native support directories:

- `.agents/skills`: repo-local repeatable workflows for Codex
- `.agents/plans`: plan docs for complex or multi-step work
- `docs/`: durable project docs, business maps, and external-tool notes
- `packages/`: shared contracts, reusable API client code, and shared configs
- `references/`: reference assets, historical material, and non-production inspiration

This repository currently needs AGENTS guidance for:

- root
- frontend
- backend

Do not add or rely on a Mini Program `AGENTS.md` unless explicitly requested.

## Product boundary and current feature policy

Treat the following as active product directions:

- resume upload and parsing
- editable Markdown resume workflow
- target job description storage and reuse
- tailored resume generation
- mock interview workflow
- candidate profile / personalized memory MVP
- minimal agent memory capability that supports the mock interview workflow

Treat the following as explicitly out of scope unless the user later changes requirements:

- voice features
- speech pipelines
- audio interview mode
- applications tracking
- training linkage with job application tracking
- broad multi-agent architecture for its own sake
- speculative platform expansion beyond the current workflow

Do not quietly reintroduce deprecated or paused features.

## Core operating principles

### 1. Reuse before reinvent

When implementing features, fixing bugs, designing architecture, or improving engineering quality, prefer proven existing solutions over inventing new ones from scratch.

Default priority order:

1. official documentation and official best practices
2. mature framework-native solutions
3. widely adopted community patterns
4. high-quality open-source implementations
5. well-maintained libraries
6. custom implementation only when clearly justified

Do not default to hand-rolled infrastructure if a stable, well-understood solution already exists.

### 2. Prefer mature internet-backed solutions

For any non-trivial task, actively look for the most established approach rather than improvising a custom one.

Prefer solutions that are:

- widely used in production
- actively maintained
- well documented
- consistent with the current stack
- easy for future contributors to understand
- low-risk to integrate and maintain

Good implementation work in this repo usually means:

- adapting proven ideas
- integrating stable libraries
- matching current project conventions
- minimizing unnecessary complexity

It does **not** mean building bespoke abstractions when standard patterns already solve the problem well.

### 3. Avoid unnecessary wheel reinvention

Do not rebuild common foundations unless there is a strong project-specific reason.

This especially applies to:

- form validation
- request handling
- schema validation
- authentication and authorization
- file upload flows
- caching
- retry logic
- logging
- storage client wrappers
- markdown and document processing
- AI SDK integration
- workflow orchestration
- background task patterns
- memory frameworks
- RAG or vector retrieval foundations

If a mature solution exists and fits the repository constraints, prefer reuse, encapsulation, and adaptation.

### 4. Require justification for custom implementations

If choosing a custom implementation over an existing mature solution, explicitly justify it.

Valid reasons may include:

- the existing solution does not satisfy core product requirements
- integration cost is unreasonably high for the current repo
- the dependency is poorly maintained or risky
- the project needs a narrower and simpler implementation
- custom implementation substantially improves maintainability in this repo

Do not choose custom implementation merely to appear clever or original.

## MVP-first delivery rules

### 1. Strict MVP principle

All development in this repository must follow a strict MVP principle.

This means:

- implement the smallest useful version first
- prioritize core functionality over completeness
- prefer a stable minimal path over a broad ambitious design
- avoid building future-facing architecture before current needs are proven
- ship one usable increment at a time

Do not expand scope just because a related feature seems nearby.

### 2. One feature point at a time

For planning and implementation, treat each requested feature point as an independent task.

Required behavior:

- analyze one feature point at a time
- output one solution per feature point
- do not combine multiple major features into one implementation batch
- do not implement “while we are here” adjacent features unless explicitly requested

Examples of separate feature points:

- open-source integration for parsing
- candidate profile
- resume multi-format parsing
- agent memory
- mock interview structured feedback

### 3. Prefer smallest viable change set

When a feature can be implemented by extending existing routes, schemas, services, or pages, prefer that path over creating a parallel subsystem.

Do not introduce:

- new top-level architecture layers
- large abstractions
- generic frameworks
- cross-cutting rewrites

unless clearly required by the MVP.

## Required working method for Codex

For any non-trivial feature, bug fix, refactor, or integration, Codex must follow this sequence:

1. read the relevant code first
2. summarize the current implementation truthfully
3. identify reusable modules and nearby patterns
4. identify the exact gap relative to the requested feature
5. produce an MVP implementation plan
6. list the files that will be changed or added
7. only then begin coding

Do not skip directly from user request to code changes on non-trivial tasks.

### Mandatory rule: analyze first, code second

Before implementing any non-trivial change, Codex must first provide:

1. current code status
2. reusable modules
3. missing capability
4. MVP solution
5. file change list
6. API / schema impact
7. test plan
8. risks and boundaries

Only after this analysis should coding begin.

### Scope discipline

During implementation:

- stay within the current single feature point
- do not quietly expand into other pending features
- do not perform unrelated refactors
- do not fix unrelated bugs unless they block the requested task
- do not redesign the entire system around one new requirement

If a broader change seems necessary, state it explicitly before making it.

## Output format requirements for Codex

When asked to analyze or plan a feature, use this structure:

1. Current code status
2. Reusable modules
3. Missing capability
4. MVP solution
5. Files to modify
6. Files to add
7. API design
8. Database / schema changes
9. Test plan
10. Risks and boundaries

When asked to implement a feature, after coding provide:

1. What changed
2. Why it changed
3. Files changed
4. New or changed API endpoints
5. Data model changes
6. Manual test steps
7. Remaining limitations
8. Rollback notes if relevant

Keep output practical and repository-specific. Do not respond with generic architecture advice detached from the codebase.

## How to work in this repo

- Read this file before making cross-cutting changes.
- For repo-wide tasks, also read `docs/codex-workspace.md` if it exists.
- Use `docs/index.md` as the main document entrypoint when the task depends on product or domain understanding.
- Prefer small, local, workflow-safe changes over broad refactors.
- Preserve the shared context between resume, job description, tailored resume, candidate profile, and mock interview.
- Do not invent product features that README marks as unfinished or explicitly paused.
- Treat incomplete pages as scaffolds, not delivered features.
- Before changing architecture, inspect nearby code and match existing conventions.
- Keep user-facing flows coherent across frontend, backend, and persisted data.
- Favor production-grade implementation over demo-style shortcuts.

## Decision rules for implementation

Before implementing any non-trivial change, first evaluate:

1. Is there already a framework-native way to do this?
2. Is there already a mature library or stable open-source approach?
3. Is there already a similar implementation somewhere else in this repo?
4. Can the task be solved by adapting an existing pattern instead of creating a new one?
5. Is the proposed solution consistent with long-term maintainability?
6. Is the proposed solution the smallest viable version that satisfies the request?

When multiple options are viable, prefer the one with:

- lower maintenance burden
- clearer conventions
- better ecosystem support
- fewer custom abstractions
- better fit with current repository structure
- smaller MVP scope

## Expected behavior from Codex

For non-trivial development tasks, Codex should usually:

1. inspect the local codebase first
2. identify existing conventions and nearby patterns
3. prefer official or established approaches
4. reuse or adapt before building from scratch
5. keep changes minimal but durable
6. explain major technical choices when they are not obvious
7. avoid broad rewrites unless the task explicitly calls for them
8. avoid combining multiple feature points into one delivery
9. honor explicit out-of-scope product boundaries
10. stop at MVP unless asked to continue

When introducing a dependency, prefer one that is:

- credible
- actively maintained
- popular enough to be trusted
- appropriate for the stack already in use
- justified by meaningful reduction in complexity or risk

## Navigation rules

When deciding where work belongs:

- put production product code under `apps/frontend` or `apps/backend`
- put reusable shared contracts and tooling under `packages/`
- put repo-specific reusable agent workflows under `.agents/skills`
- put complex task plans under `.agents/plans`
- put stable documentation under `docs/`
- treat `references/` as non-production material unless a task explicitly targets it

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

For product behavior, trust:

1. implemented workflow
2. current README
3. this file
4. the nearest child `AGENTS.md`
5. durable docs under `docs/`
6. shared contracts under `packages/contracts/`
7. repo-local skills in `.agents/skills/`

Do not describe reserved pages or placeholder routes as completed functionality.

When instructions conflict, prefer the nearest relevant scope while preserving the core workflow and explicit product boundaries in this file.

## Frontend guidance

When working in `apps/frontend`:

- preserve workflow continuity between resume editing, job description management, tailored resume generation, candidate profile display, and mock interview
- prefer existing UI patterns, component conventions, and routing structure
- do not introduce visual or state-management complexity without clear benefit
- keep form flows explicit, predictable, and recoverable
- prefer maintainable composition over clever abstraction
- treat unfinished pages as partial scaffolds, not hidden complete features
- prefer simple MVP UI first, such as basic tables, cards, and clear forms
- do not introduce complex dashboards or analytics UI unless explicitly requested
- avoid building voice UI or application-tracking UI

For candidate profile UI specifically:

- prefer a simple table or compact structured card view
- prioritize clarity over visual polish
- show provenance or last-updated information when practical

For mock interview UI specifically:

- prioritize question, answer input, and structured feedback
- keep the feedback format simple and readable
- do not add voice interaction, avatars, or theatrical UX

## Backend guidance

When working in `apps/backend`:

- preserve API contracts that support the workflow continuity of the product
- favor explicit schemas, typed boundaries, and predictable service behavior
- keep route, service, storage, parser, memory, and AI integration responsibilities clearly separated
- prefer robust error handling over silent failure
- avoid embedding large amounts of business logic directly in route handlers
- prefer mature patterns for retries, async jobs, object storage, caching, and persistence
- keep AI-related orchestration observable and debuggable
- prefer unified adapters for external integrations where practical

For resume parsing specifically:

- prefer a unified parser interface across file types
- normalize outputs into a shared internal representation
- preserve extracted Markdown when possible
- support incremental extension of file formats
- prioritize stable PDF, DOCX, and MD handling before treating DOC as fully supported

For memory specifically:

- prefer a lightweight repository-native memory layer first
- distinguish short-term interview context, medium-term job context, and long-term candidate profile memory
- do not introduce a heavy memory framework unless there is clear MVP benefit

For mock interview specifically:

- each answer cycle should be able to return at least:
  - question focus
  - answer weaknesses
  - improved answer

## Planning guidance

Use `.agents/plans` for tasks that are:

- multi-step
- cross-cutting
- architectural
- risky to change directly
- likely to require staged implementation

Plans should favor:

- small reversible steps
- explicit assumptions

## Default business-routing skills

For domain-specific work, prefer these skills before using purely technical routing:

- `.agents/skills/resume-pipeline/SKILL.md`
- `.agents/skills/tailored-resume-contract/SKILL.md`
- `.agents/skills/mock-interview-session/SKILL.md`

Use technical skills such as frontend/backend helpers after the domain route is clear.
- dependency awareness
- low-risk rollout order
- MVP-first sequencing
- one-feature-at-a-time execution

Do not create plan files for trivial edits.

## Skill guidance

Use `.agents/skills` for repeatable repo-specific workflows, such as:

- common setup flows
- standard debugging procedures
- recurring refactor patterns
- reusable implementation playbooks
- quality check sequences
- parser integration playbooks
- mock interview iteration playbooks

A skill should encode a repeatable working method, not a one-off task note.

## Quality bar

Changes should aim to be:

- correct
- readable
- locally consistent
- easy to maintain
- aligned with the real product workflow
- suitable for a production-oriented project, not just a temporary demo
- small enough to review safely
- testable with clear manual verification

Avoid:

- speculative architecture
- unnecessary abstraction
- cosmetic rewrites without product value
- introducing fragile dependencies
- breaking workflow continuity
- duplicating logic that should live in one place
- hidden scope expansion
- implementing multiple roadmap items at once
- adding paused features back into active development

## Testing and validation expectations

For any non-trivial change, validate at least:

- happy path behavior
- input validation
- failure path or error message behavior
- compatibility with existing workflow steps
- basic regression impact on adjacent steps

When integrating an external or open-source capability, validate at least:

- successful API or library invocation
- timeout or upstream failure handling
- malformed response handling
- unsupported input handling
- provider-specific fallback or warning behavior if applicable

Do not claim a feature is complete without basic verification evidence.

## Build and run

### Middleware services

Run required services first:

```bash
docker compose -f docker-compose.yml up -d postgres redis minio
```
