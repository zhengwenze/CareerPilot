---
name: git-commit-convention
description: Use this skill when the user wants to write, rewrite, validate, or improve Git commit messages using Conventional Commits. Helps classify changes, split mixed work into logical commits, choose scopes, detect breaking changes, and produce clear commit messages in the format type(scope): description.
---

# Git Commit Convention

Write and validate Git commit messages using the Conventional Commits standard.

## Related Skills

This skill works closely with:

- **`.agents/skills/dual-repo-publish/SKILL.md`** - For the complete commit-and-push workflow
- **`.agents/skills/git-pre-commit-check/SKILL.md`** - For pre-commit validation

## Use this skill when the user asks to:

- write a commit message
- rewrite or improve an existing commit message
- generate commits from a diff or staged changes
- split mixed changes into multiple logical commits
- check whether a commit follows Conventional Commits
- create better scope names
- identify whether a change is breaking
- produce commit messages for Git, GitHub, or PR workflows

This skill should optimize for:

- correctness
- clarity
- small logical commits
- accurate type selection
- useful scope selection
- concise subject lines
- explicit breaking change signaling
- commit history that is readable by humans and tooling

---

## Core Standard

Use Conventional Commits structure:

`<type>[optional scope]: <description>`

Optional sections:

- body
- footer
- breaking change marker using `!`
- `BREAKING CHANGE:` footer when needed

Examples:

- `feat(auth): add magic link login`
- `fix(api): handle null user profile response`
- `docs(readme): clarify local setup steps`
- `refactor(payments): extract invoice formatter`
- `feat!: remove legacy billing endpoint`

If a change introduces a breaking API or behavior change, prefer one of:

- `feat!: ...`
- `refactor!: ...`
- a footer containing `BREAKING CHANGE: ...`

---

## Allowed Commit Types

Use these types by default unless the repository clearly uses a different convention.

- `feat`: a new user-facing feature
- `fix`: a bug fix
- `docs`: documentation only changes
- `style`: formatting or style-only changes with no logic change
- `refactor`: code restructuring with no feature or bug fix intent
- `perf`: performance improvement
- `test`: add or update tests
- `build`: build system or dependency/build tooling changes
- `ci`: CI/CD configuration changes
- `chore`: maintenance work not covered above
- `revert`: revert a previous commit

Do not misuse types:

- do not use `feat` for refactoring
- do not use `fix` for new functionality
- do not use `chore` when a more precise type is available
- do not use `style` for UI redesigns that alter product behavior or structure

---

## Scope Rules

A scope is optional. Use it when it improves clarity.

Good scope candidates:

- package name
- module name
- app name
- service name
- domain area
- feature area
- route group
- UI section if clearly bounded

Examples:

- `feat(auth): add passwordless login`
- `fix(payments): retry failed invoice sync`
- `docs(api): document rate limits`
- `test(search): cover empty query state`

Avoid poor scopes:

- vague words like `stuff`, `misc`, `update`
- file names unless the repo convention prefers them
- multiple unrelated scopes in one commit
- overlong scopes

If the change spans several unrelated areas, split into multiple commits instead of forcing one broad scope.

---

## Subject Line Rules

The subject line is the most important output.

Always make it:

- concise
- specific
- action-oriented
- lower-case after the colon unless proper nouns require capitalization
- free of trailing punctuation

Preferred style:

- use imperative phrasing where natural
- describe what changed, not why the developer felt like changing it
- keep it short and information-dense

Good:

- `fix(cache): avoid stale session reads`
- `feat(editor): add slash command menu`
- `docs(setup): explain environment variables`

Bad:

- `fix: fixed stuff`
- `chore: updates`
- `feat(ui): made the page better`
- `refactor: various improvements.`

If the repository already shows a strong subject-length norm, follow it.
Otherwise, aim for a short one-line subject that stays easy to scan in `git log`.

---

## Body Rules

Add a body only when it improves understanding.

Use a body when:

- the change is not obvious from the subject
- there is an important implementation detail
- there is migration guidance
- there are side effects or caveats
- the change spans several related edits

A good body should explain:

- what changed
- why it changed
- any important constraints, migration notes, or behavior impact

Do not repeat the subject line verbatim.

---

## Footer Rules

Use footers for:

- breaking changes
- issue references
- migration notes
- related tickets when the repository uses them

Examples:

- `BREAKING CHANGE: removes the v1 export format`
- `Refs: #142`
- `Closes: #381`

When a breaking change exists, make it explicit.
Do not hide breaking behavior inside a vague body paragraph.

---

## Breaking Change Rules

A change is breaking if it forces downstream users, callers, integrators, deploy scripts, configs, or consumers to change behavior.

Common breaking cases:

- renamed or removed API fields
- removed function arguments
- changed return shape
- removed endpoints
- changed config keys
- changed CLI flags
- changed database contract or migration requirements
- changed public component props in an incompatible way

If the change is breaking:

1. use `!` in the header when appropriate
2. include a `BREAKING CHANGE:` footer with a concrete explanation
3. mention the migration path if known

Example:

`feat(api)!: rename customer status field`

Body:
`Rename status to lifecycle_status in API responses.`

Footer:
`BREAKING CHANGE: clients must read lifecycle_status instead of status.`

---

## Commit Splitting Rules

If changes are mixed, do not force one commit.

Split into multiple commits when there are separate logical units such as:

- refactor plus bug fix
- feature plus docs
- dependency update plus code changes
- formatting plus logic changes
- unrelated modules changed together accidentally

When splitting, group files by intent, not by file type alone.

Preferred order when suggesting multiple commits:

1. refactors or prep work
2. main feature or fix
3. tests
4. docs
5. chore/build/ci follow-ups

If the user asks for one commit but the diff clearly contains multiple unrelated changes, explain that the history will be cleaner if split, then provide the proposed commit set.

---

## Decision Process

When given a diff, staged files, or a natural-language summary, follow this process:

### Step 1: Classify the change

Determine whether the primary intent is:

- feature
- fix
- refactor
- docs
- test
- perf
- build
- ci
- chore
- revert

Choose the most specific valid type.

### Step 2: Detect scope

Infer a useful scope from:

- package or workspace name
- directory
- module
- domain area
- app feature

Only include scope if it adds clarity.

### Step 3: Check for breaking impact

Look for:

- removed fields
- renamed interfaces
- changed contracts
- migration requirements
- incompatible config changes

If present, mark the commit as breaking and explain why.

### Step 4: Check for mixed intent

If the change contains multiple unrelated logical units, propose multiple commits instead of one.

### Step 5: Draft the commit message

Produce:

- header first
- optional body if useful
- optional footer if needed

### Step 6: Validate quality

Before finalizing, verify that the message:

- uses a valid type
- uses a helpful scope if present
- has a clear subject
- does not contain filler wording
- correctly flags breaking changes
- matches the actual diff

---

## Integration with Other Skills

### With dual-repo-publish

When `dual-repo-publish` skill is invoked, it will:

1. Check working tree status
2. Run pre-commit checks (via `git-pre-commit-check`)
3. **Call this skill to generate commit message**
4. Create the commit
5. Push to remotes

This skill should provide the commit message that `dual-repo-publish` will use.

### With git-pre-commit-check

Before generating a commit message:

1. Pre-commit checks should pass
2. If there are issues, they should be resolved or acknowledged
3. Then proceed to generate the commit message

---

## Output Format

When the user asks for a commit message, default to this format:

### Single commit

```text
type(scope): short description

Optional body when needed.

Optional footer
```

### Multiple commits

When splitting is recommended:

```text
Proposed commits:

1. refactor(module): prepare for feature X
   - extract helper functions
   - rename variables for clarity

2. feat(module): add feature X
   - implement core functionality
   - add configuration options

3. test(module): add tests for feature X
   - unit tests
   - integration tests

4. docs(module): document feature X
   - update README
   - add usage examples
```

---

## Quick Reference

| Element | Format | Example |
|---------|--------|---------|
| Type | lowercase | `feat`, `fix`, `docs` |
| Scope | lowercase, optional | `(auth)`, `(api)` |
| Subject | lowercase, imperative | `add login feature` |
| Body | paragraphs, explanatory | `Implements OAuth2...` |
| Footer | key: value | `Closes: #123` |
| Breaking | `!` after type/scope | `feat(api)!: remove endpoint` |

---

## Common Patterns for Career Pilot

Based on the repository structure, common scopes include:

- `backend` - FastAPI backend changes
- `frontend` - Next.js frontend changes
- `resume` - Resume-related features
- `interview` - Mock interview features
- `ai` - AI client and integration
- `config` - Configuration changes
- `test` - Test-related changes
- `docs` - Documentation changes

Example messages for this repo:

```
feat(backend): integrate codex2gpt AI provider for resume parsing

fix(frontend): resolve resume editor state sync issue

docs(readme): update local development setup instructions

test(backend): add tests for AI client retry logic

refactor(resume): extract markdown parser into separate module
```
