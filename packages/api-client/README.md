# API Client

`packages/api-client/` is the shared home for reusable frontend API client foundations.

Current scope:

- base HTTP request helpers
- API response wrapper types

This package is introduced before full workspace wiring so the shared boundary is explicit.
The current frontend runtime may still use local copies under `apps/frontend/src/lib/api/` until a later integration pass.
