---
name: komoot-strava-sync-backend
description: Use when working in the komoot-strava-sync repository, especially the FastAPI backend, background jobs, auth, Strava/Komoot integration, migrations, and repo-specific development workflow.
---

# Komoot Strava Sync Backend

Use this skill for tasks in this repository.

## Start Here

Read, in this order:

1. `CODEX.md`
2. `CLAUDE.md`
3. `backend/CLAUDE.md`
4. `AI_HANDOFF.md`
5. `PROJECT.md`

Then validate assumptions against the code. The docs do not fully agree with each other.

## Working Priorities

- Prefer the active `backend/` code over the frozen `legacy/` app unless the task is explicitly about the old standalone worker.
- Treat migrations, models, workers, and routes as a single unit. When one changes, inspect the others.
- Use `rg` for repo search and `make status` before substantial edits.

## Backend Guardrails

- Keep route handlers async and use `httpx.AsyncClient` for network access.
- Route-level auth should use dependencies from `app.api.deps`.
- Premium gates use `require_tier("pro")` unless the feature truly needs a higher tier.
- All Strava API calls must be wrapped by `app.core.rate_limit.rate_limit_guard.call`.
- Encrypt Komoot credentials and Strava tokens before writing to the database.
- Do not trust existing token handling blindly; inspect the write and read paths together.

## Validation Flow

- First choice: `make check`
- If only formatting changed: `make lint`
- If infra is needed: `make dev`
- If commands cannot run because dependencies are missing, state that clearly and continue with code inspection

## High-Risk Files

- `backend/app/api/v1/auth.py`
- `backend/app/api/v1/webhooks.py`
- `backend/app/jobs/sync_jobs.py`
- `backend/app/services/sync.py`
- `backend/app/services/strava.py`
- `backend/app/db/models/`
- `backend/alembic/versions/`

## Useful Commands

```bash
make status
make dev
make dev-logs
make check
make migrate
make migrate-gen name=describe_change
```

## Deliverable Standard

- Explain what changed in terms of behavior, not just files.
- Call out anything unverified.
- If docs disagree with code, say which source you trusted and why.
