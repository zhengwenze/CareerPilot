# Git Sync Workflow

This repository keeps two primary remotes synchronized for normal publish work:

- `origin` -> Gitee -> branch `master`
- `github` -> GitHub -> branch `main`

## Expected invariant

After a successful dual-repo publish flow:

- local `HEAD`
- `origin/master`
- `github/main`

should all point to the same commit hash.

## Default publish sequence

For the standard Career Pilot workflow:

1. inspect the working tree
2. create one or more Conventional Commits
3. push to `origin/master`
4. push the same commit to `github/main`
5. verify all three refs match

## Safety rules

- do not push empty commits
- do not auto-force-push
- do not auto-rebase or rewrite history
- if GitHub `main` diverges from local history, stop and report it before pushing
- if one remote succeeds and the other fails, report partial-sync state explicitly
