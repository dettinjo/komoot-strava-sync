from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _bootstrap_strava_app() -> None:
    """Ensure at least one StravaApp row exists, creating one from env vars if not."""
    from app.core import security
    from app.db.models.user import StravaApp
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(StravaApp).limit(1))
        if result.scalar_one_or_none() is not None:
            return

        logger.info("No StravaApp found — seeding default app from env vars.")
        app_entry = StravaApp(
            client_id=settings.STRAVA_CLIENT_ID,
            client_secret=security.encrypt(settings.STRAVA_CLIENT_SECRET),
            display_name="Default Strava App",
            is_active=True,
        )
        db.add(app_entry)
        await db.commit()
        logger.info("Default StravaApp created.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.redis = redis_client

    try:
        import arq

        arq_pool = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.REDIS_URL))
        app.state.arq_pool = arq_pool
    except Exception:
        app.state.arq_pool = None

    try:
        await _bootstrap_strava_app()
    except Exception as exc:
        logger.warning("StravaApp bootstrap failed (non-fatal): %s", exc)

    yield

    await redis_client.aclose()
    if app.state.arq_pool is not None:
        await app.state.arq_pool.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Komoot–Strava Sync API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    if settings.ENVIRONMENT == "development":
        allow_origins = ["*"]
    else:
        allow_origins = [settings.FRONTEND_URL]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok"}

    from app.api.v1.router import router as api_v1_router

    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
