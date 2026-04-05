---
name: dual-repo-publish
description: Use this skill when the user wants one-shot commit-and-push sync for Career Pilot to Gitee master and GitHub main with Conventional Commits.
---

# Dual Repo Publish

Use this skill when the user asks to:

- 提交并同步两个仓库
- 双仓库提交推送
- publish to GitHub and Gitee
- commit and sync both remotes
- 提交代码并同时推送到 GitHub 和 Gitee

This skill is repository-specific for `career-pilot`.

## Goals

- move from working tree changes to synced remotes as quickly as possible
- keep commit messages aligned with Conventional Commits
- keep Gitee `origin/master` and GitHub `github/main` on the same commit after a successful run
- stop early on real blockers instead of improvising risky Git recovery

## Fixed remote contract

This skill assumes these remotes are already configured:

- `origin` -> Gitee -> push target `master`
- `github` -> GitHub -> push target `main`

Do not guess other remotes or branch names unless the user explicitly changes the workflow.

## Read first

1. `AGENTS.md`
2. `docs/codex-workspace.md`
3. `docs/git-sync-workflow.md`
4. `.agents/skills/git-commit-convention/SKILL.md`

## Default execution path

When this skill is triggered, use this flow by default:

1. run `git status --short`
2. if the working tree is clean, report `nothing to commit` and stop without pushing
3. inspect the changed files and decide whether the diff is one logical commit or should be split
4. reuse `.agents/skills/git-commit-convention/SKILL.md` to generate the commit message
5. stage the intended files
6. create the commit
7. verify `github/main` is an ancestor of local `HEAD` before pushing
8. push `HEAD:master` to `origin`
9. push the same `HEAD:main` to `github`
10. verify `HEAD`, `origin/master`, and `github/main` resolve to the same commit hash

Default behavior is fully automatic once the user asks to submit and sync.

## Commit rules

- treat `.agents/skills/git-commit-convention/SKILL.md` as the source of truth for commit classification and wording
- prefer one commit only when the diff is clearly one logical unit
- if the changes are clearly mixed, split them before any push
- do not invent repository-specific commit types outside Conventional Commits

## Failure handling

If the flow cannot complete cleanly, stop and report the exact blocker.

### Clean tree

- if `git status --short` is empty, do not create an empty commit
- do not push just to “make sure” remotes are synced

### Mixed changes

- if unrelated changes are mixed together, prefer split commits
- explain the proposed split briefly before committing if the split materially changes history shape

### Diverged GitHub main

- if `github/main` is not an ancestor of local `HEAD`, stop before any push
- report that GitHub has diverged and needs an explicit sync decision
- do not auto-rebase, force-push, or rewrite history

### Partial push success

- if push to `origin/master` succeeds and push to `github/main` fails, report a partial-sync state
- include the local `HEAD` commit hash and the observed remote branch heads
- do not attempt force-push, reset, or rollback automatically

### Auth or remote errors

- surface the exact failing remote and branch
- keep the successful remote unchanged
- do not switch branches or modify remotes automatically

## Success output

On success, report:

- the commit message used
- the new commit hash
- confirmation that `origin/master` was updated
- confirmation that `github/main` was updated
- confirmation that local `HEAD`, `origin/master`, and `github/main` match

## Validation commands

Use the narrowest set of Git checks that proves the sync:

```bash
git status --short
git rev-parse HEAD origin/master github/main
```
