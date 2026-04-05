---
name: mock-interview-session
description: Use this skill when changing mock interview session creation, question flow, answer submission, follow-up logic, review output, or session lifecycle behavior.
---

# Mock Interview Session

Use this skill when a task touches the structured mock interview workflow.

## Covers

- session creation
- preparation state
- question and follow-up flow
- answer submission
- finish / delete / retry behavior
- review summary output

## Read first

1. `AGENTS.md`
2. `docs/index.md`
3. `docs/domain/entities.md`
4. `packages/contracts/`

## Working rules

- preserve session continuity and source context from resume + job + optimization result
- keep lifecycle state explicit instead of implicit UI assumptions
- treat follow-up behavior and review output as part of the contract
- avoid reducing mock interview to a stateless question-response page
- inspect both router/service behavior and frontend module contracts before changing fields

## Validation

Use the narrowest useful checks for the affected interview path.
