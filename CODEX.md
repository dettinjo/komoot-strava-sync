## Codex Project Guide

Use this file as the Codex-facing equivalent of `CLAUDE.md`.

### Goals

- Keep Codex output aligned with the strongest parts of the existing Claude workflow.
- Prefer executable checks and current code over stale planning docs.
- Optimize for functional backend changes, not speculative scaffolding.

### Read Order

1. `git status --short`
2. `git log --oneline -5`
3. `CLAUDE.md`
4. `backend/CLAUDE.md`
5. `AI_HANDOFF.md`
6. `PROJECT.md`

Treat `AI_HANDOFF.md` and `PROJECT.md` as helpful context, not source of truth. They currently disagree with each other and with the codebase.

### Current Reality

- `legacy/` contains the old standalone implementation.
- `backend/` contains the active FastAPI SaaS backend.
- `frontend/` does not exist yet, even though some docs and compose files still reference it.
- The database models, Alembic migration, and docs are not fully aligned. Verify before changing schema-related code.

### Core Working Rules

- All backend HTTP handlers stay async.
- All outbound Strava API traffic must go through `RateLimitGuard.call()`.
- Komoot credentials and Strava tokens must be encrypted before DB persistence.
- Do not trust docs that claim the backend is fully complete or fully scaffold-only. Validate in code.
- Prefer small, testable fixes over broad rewrites.
- When touching auth, billing, migrations, or job processing, inspect neighboring files first.

### Recommended Workflow

1. Establish current state with `make status`.
2. Run `make check` before and after substantial backend changes when the environment supports it.
3. For backend-only local development, use `make dev` to start `db`, `redis`, `api`, and `worker` without the missing frontend.
4. When working on schema or persistence logic, compare:
   - `backend/app/db/models/`
   - `backend/alembic/versions/`
   - any API or worker code that writes those models
5. Before concluding a session, summarize:
   - what changed
   - what was verified
   - what remains risky or inconsistent

### Quality Bar

- Fix root causes, not just symptoms.
- Add or update tests when behavior changes.
- Keep comments rare and high-signal.
- Avoid compatibility shims unless they are truly needed.
- If a command cannot be run locally because dependencies are missing, say so explicitly.

### Known High-Risk Areas

- Webhook routing between Strava athlete IDs and local user IDs
- Token encryption and refresh behavior
- Alembic drift versus SQLAlchemy models
- Compose/docs references to missing frontend assets
- Tests that rely on heavy mocking rather than real integration paths
