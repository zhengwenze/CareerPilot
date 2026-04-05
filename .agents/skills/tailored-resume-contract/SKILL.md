---
name: tailored-resume-contract
description: Use this skill when changing the contract and workflow that connects saved jobs, match data, tailored resume generation, retry state, download, and interview handoff.
---

# Tailored Resume Contract

Use this skill when a task touches job-driven resume tailoring behavior.

## Covers

- job description persistence and parsing
- match report bridging
- optimization / tailored resume session state
- retry, stale state, and download behavior
- handoff into mock interview

## Read first

1. `AGENTS.md`
2. `docs/index.md`
3. `docs/domain/resume-pipeline.md`
4. `docs/domain/entities.md`
5. `packages/contracts/`

## Working rules

- treat tailored resume generation as a reusable work artifact, not a one-off suggestion
- keep source resume version and source job version visible
- preserve explicit retry and stale-state handling
- keep download and interview handoff behavior aligned with the same contract
- update frontend API modules and backend schemas together when the contract changes

## Validation

Use focused frontend/backend checks on the affected workflow path.
