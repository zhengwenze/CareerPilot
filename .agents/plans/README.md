# Plans

`.agents/plans/` is reserved for complex tasks that benefit from an explicit plan before code changes start.

Use this directory for:

- multi-step feature work
- migrations
- cross-app changes
- investigations that may take more than one focused coding pass

Keep plan filenames short and specific, for example:

- `resume-parser-hardening.md`
- `jd-tailoring-contract-update.md`
- `mock-interview-session-recovery.md`

Suggested plan shape:

1. goal
2. scope and non-goals
3. affected directories
4. contract or schema impact
5. implementation steps
6. validation steps
7. rollout or follow-up notes
