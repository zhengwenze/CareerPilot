---
name: end-to-end-workflow-check
description: Use this skill when a task spans frontend and backend, or when validating that the main resume-to-interview workflow still hangs together after changes.
---

# End-to-End Workflow Check

Use this skill when a change may affect workflow continuity across apps.

## Critical chain

The main product chain is:

1. upload master resume PDF
2. convert it into editable Markdown
3. save the target job description
4. generate a tailored resume
5. continue into mock interview

## What to verify

- master resume content remains editable and saveable
- JD data remains reusable by downstream steps
- tailored resume generation exposes usable status and retry behavior
- mock interview still receives the right job and resume context
- no step forces the user to rebuild context manually

## Working rules

- look for continuity breaks, not just local correctness
- prefer fixing contract drift and state handoff issues in the same task
- do not mark placeholder pages as complete workflow support

## Validation

Choose the lightest useful validation path:

- backend tests for affected services or routes
- frontend manual or browser-based workflow verification
- cross-check of request / response shapes where no browser run is needed
