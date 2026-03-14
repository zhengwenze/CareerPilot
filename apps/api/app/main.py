from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis, from_url

from app.api.routes import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import close_engine
from app.services.token_blocklist import InMemoryTokenBlocklist, RedisTokenBlocklist

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    redis_client: Redis | None = getattr(app.state, "redis", None)

    if not hasattr(app.state, "token_blocklist") and settings.redis_url:
        redis_client = from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        app.state.token_blocklist = RedisTokenBlocklist(redis_client)
        app.state.redis = redis_client
    elif not hasattr(app.state, "token_blocklist"):
        app.state.token_blocklist = InMemoryTokenBlocklist()
        app.state.redis = None

    try:
        yield
    finally:
        if redis_client is not None:
            await redis_client.aclose()
        await close_engine()


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    config = settings or get_settings()

    app = FastAPI(title=config.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error while serving %s", request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(api_router)
    return app


app = create_app()
