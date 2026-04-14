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

## Prerequisites Checklist

Before executing this skill, ensure:

- [ ] Git version >= 2.30 (`git --version`)
- [ ] Remote repositories configured (`git remote -v` shows origin and github)
- [ ] Network connectivity to Gitee and GitHub
- [ ] Valid Git credentials for both remotes
- [ ] No uncommitted changes that should be preserved

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

## Pre-flight checks

Before executing the main workflow, perform these checks:

### 1. Remote connectivity check
```bash
# Check if remotes are accessible
git ls-remote origin HEAD --quiet 2>/dev/null && echo "Gitee: OK" || echo "Gitee: FAILED"
git ls-remote github HEAD --quiet 2>/dev/null && echo "GitHub: OK" || echo "GitHub: FAILED"
```

### 2. Authentication check
```bash
# Verify credentials are valid
git fetch origin --dry-run 2>&1 | head -5
git fetch github --dry-run 2>&1 | head -5
```

### 3. Branch status check
```bash
# Check if local branch is ahead/behind/diverged
git rev-list --left-right --count HEAD...origin/master 2>/dev/null || echo "Cannot compare with origin/master"
git rev-list --left-right --count HEAD...github/main 2>/dev/null || echo "Cannot compare with github/main"
```

### 4. Large files check
```bash
# Warn about files > 10MB
git diff --cached --numstat | awk '$1 > 10485760 || $2 > 10485760 {print "Large file detected: " $3}'
```

## Default execution path

When this skill is triggered, use this flow by default:

1. run `git status --short`
2. if the working tree is clean, report `nothing to commit` and stop without pushing
3. **run pre-flight checks** (network, auth, branch status)
4. inspect the changed files and decide whether the diff is one logical commit or should be split
5. reuse `.agents/skills/git-commit-convention/SKILL.md` to generate the commit message
6. stage the intended files
7. create the commit
8. verify `github/main` is an ancestor of local `HEAD` before pushing
9. push `HEAD:master` to `origin`
10. push the same `HEAD:main` to `github`
11. verify `HEAD`, `origin/master`, and `github/main` resolve to the same commit hash

Default behavior is fully automatic once the user asks to submit and sync.

## Commit rules

- treat `.agents/skills/git-commit-convention/SKILL.md` as the source of truth for commit classification and wording
- **commit message 必须使用中文编写**（由 git-commit-convention 技能的 Language Rule 规定）
- prefer one commit only when the diff is clearly one logical unit
- if the changes are clearly mixed, split them before any push
- do not invent repository-specific commit types outside Conventional Commits

## Failure handling

If the flow cannot complete cleanly, stop and report the exact blocker.

### Clean tree

- if `git status --short` is empty, do not create an empty commit
- do not push just to "make sure" remotes are synced

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

## Recovery procedures

### Scenario 1: Partial push (Gitee success, GitHub failed)

**Detection**: After push, `origin/master` matches `HEAD` but `github/main` does not.

**Recovery steps**:
1. Record the partial sync state:
   ```bash
   echo "Partial sync detected at $(date)"
   echo "Local HEAD: $(git rev-parse HEAD)"
   echo "Gitee: $(git rev-parse origin/master)"
   echo "GitHub: $(git rev-parse github/main 2>/dev/null || echo 'N/A')"
   ```

2. Analyze GitHub failure reason from error output

3. Common fixes:
   - **Authentication expired**: Refresh credentials and retry
   - **Network timeout**: Wait and retry push to github
   - **Branch protection**: Check if force-push is needed (requires explicit user approval)

4. Retry only GitHub push:
   ```bash
   git push github HEAD:main
   ```

5. If retry fails repeatedly, report partial-sync state and wait for user decision

### Scenario 2: Authentication failure

**Detection**: Push fails with 401/403 errors or "Authentication failed".

**Recovery steps**:
1. Identify which remote failed:
   - Check error message for "origin" or "github"

2. For HTTPS remotes, check credential helper:
   ```bash
   git config --get credential.helper
   ```

3. Guide user to update credentials:
   - **macOS**: Check Keychain Access for git credentials
   - **Windows**: Check Credential Manager
   - **Linux**: Check `~/.git-credentials` or credential helper

4. After credentials updated, retry failed push

### Scenario 3: Network connectivity issues

**Detection**: Connection timeouts, "Could not resolve host", or "Connection refused".

**Recovery steps**:
1. Test connectivity:
   ```bash
   curl -I https://gitee.com 2>/dev/null | head -1
   curl -I https://github.com 2>/dev/null | head -1
   ```

2. Check proxy settings if behind corporate firewall:
   ```bash
   git config --get http.proxy
   git config --get https.proxy
   ```

3. Wait and retry, or ask user about proxy configuration

### Scenario 4: Large file rejection

**Detection**: Push fails with "File too large" or similar error.

**Recovery steps**:
1. Identify large files:
   ```bash
   git ls-files | xargs -I {} sh -c 'stat -f%z "$@" 2>/dev/null || stat -c%s "$@"' _ {} | awk '$1 > 10485760 {print}'
   ```

2. Options:
   - Add to `.gitignore` if should not be committed
   - Use Git LFS for binary files
   - Compress or split large files

3. Amend commit if needed and retry

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

## Quick Reference

| Task | Command |
|------|---------|
| Check status | `git status --short` |
| View remotes | `git remote -v` |
| Test Gitee connectivity | `git ls-remote origin HEAD` |
| Test GitHub connectivity | `git ls-remote github HEAD` |
| Verify sync | `git rev-parse HEAD origin/master github/main` |
| Check divergence | `git merge-base --is-ancestor github/main HEAD` |
| Retry GitHub push | `git push github HEAD:main` |
| Retry Gitee push | `git push origin HEAD:master` |

## Integration with git-commit-convention

When generating commit messages:

1. Analyze the diff to classify changes
2. Apply Conventional Commits rules from `git-commit-convention` skill
3. Generate appropriate type, scope, and description
4. Include body when changes are complex or have side effects
5. Mark breaking changes with `!` or `BREAKING CHANGE:` footer

Example workflow:
```
User: "提交代码"
→ Check working tree
→ Analyze changes (backend AI client updates)
→ Generate message: "feat(backend): integrate codex2gpt AI provider"
→ Stage files
→ Create commit
→ Push to both remotes
→ Verify sync
```
