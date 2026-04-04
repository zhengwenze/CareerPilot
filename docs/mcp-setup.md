# MCP Setup Notes

This repository does not require a committed project-local MCP server config, but external tools should still be used intentionally.

## Recommended tool lanes

- browser / DevTools MCP: validate frontend flows, async states, and dashboard UX
- GitHub integration: inspect pull requests, review threads, and CI failures
- local shell tools: run app-specific build, lint, migration, and test commands

## Documentation rule

If the project adopts a new external system that Codex must use repeatedly, document it here:

- what the tool is for
- which workflows depend on it
- any authentication or environment prerequisites
- which directory or app it is most relevant to

## Current expectation

For routine repo work:

- use `apps/frontend/AGENTS.md` for frontend constraints
- use `apps/backend/AGENTS.md` for backend constraints
- use `.agents/skills/` for repeatable repo workflows

Only add project-specific MCP setup steps here when the repository truly depends on them.
