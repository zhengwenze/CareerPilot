---
name: resume-pipeline
description: Use this skill when working on the master-resume workflow from file upload through Markdown editing, persistence, and downstream structured reuse.
---

# Resume Pipeline

Use this skill when a task touches the continuous master-resume workflow.

## Covers

- resume upload
- text extraction and Markdown conversion
- Markdown editing and persistence
- structured resume reuse in later workflows
- version-aware resume behavior

## Read first

1. `AGENTS.md`
2. `docs/index.md`
3. `docs/domain/resume-pipeline.md`
4. `docs/domain/entities.md`
5. `packages/contracts/`

## Working rules

- treat the master resume as the source of truth for later workflow steps
- preserve editability and persistence of Markdown output
- do not reduce the workflow to simple file storage
- keep parse status, task state, and downstream reuse explicit
- check both frontend and backend when changing resume-related contracts

## Validation

Use the narrowest useful checks across affected app layers.
