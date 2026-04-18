from __future__ import annotations
"""ARQ Worker configuration for background synchronization tasks."""

import logging

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import settings
from app.db.session import engine
from app.jobs.sync_jobs import (
    komoot_poll_scheduler,
    poll_komoot_user,
    process_strava_activity,
)

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Initialize resources for the worker."""
    logger.info("ARQ Worker starting up. Connecting to DB and Redis...")
    ctx["engine"] = engine


async def shutdown(ctx: dict) -> None:
    """Clean up resources on worker shutdown."""
    logger.info("ARQ Worker shutting down. Cleaning up...")
    await ctx["engine"].dispose()


class WorkerSettings:
    """ARQ Worker configuration."""

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    on_startup = startup
    on_shutdown = shutdown

    functions = [
        poll_komoot_user,
        process_strava_activity,
    ]

    cron_jobs = [
        cron(
            komoot_poll_scheduler,
            hour=None,
            minute=set(range(0, 60, 5)), # Run every 5 minutes
            run_at_startup=True,
        )
    ]

    # Max simultaneous jobs
    max_jobs = 10
    
    # Max job timeout
    job_timeout = 600
