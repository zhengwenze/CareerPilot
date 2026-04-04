---
name: repo-structure-hygiene
description: Use this skill when reorganizing repository structure, adding project docs, or deciding where new rules, skills, plans, and reference assets should live.
---

# Repo Structure Hygiene

Use this skill when the task is about repository organization rather than product behavior.

## Primary rule

Prefer clearer boundaries over more folders.

The target structure should make it obvious where to place:

- product code
- repo rules
- reusable agent workflows
- plans
- durable docs
- reference-only assets

## Directory policy

- product code belongs in `apps/`
- repo-wide behavior belongs in `AGENTS.md`
- reusable workflows belong in `.agents/skills/`
- plan documents belong in `.agents/plans/`
- durable docs belong in `docs/`
- reference assets can stay in dedicated top-level directories if they are clearly labeled

## Avoid

- adding empty architecture layers without real ownership
- creating broad `misc/` or `temp/` buckets
- moving demo or reference material into product code paths
- letting README and AGENTS drift away from the actual tree

## Success criteria

- a new Codex session can identify the main code paths quickly
- reference-only folders are clearly marked
- repeatable workflows have stable homes
- complex tasks have a default place for plans
