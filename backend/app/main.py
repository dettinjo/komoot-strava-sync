from __future__ import annotations

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to Redis on startup; disconnect on shutdown."""
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.redis = redis_client

    # Also make the ARQ pool available for enqueueing jobs
    try:
        import arq
        arq_pool = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.REDIS_URL))
        app.state.arq_pool = arq_pool
    except Exception:
        app.state.arq_pool = None

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

    # CORS
    if settings.ENVIRONMENT == "development":
        allow_origins = ["*"]
    else:
        allow_origins = [
            "https://app.komoot-strava-sync.com",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok"}

    # API v1 router
    from app.api.v1.router import router as api_v1_router
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
