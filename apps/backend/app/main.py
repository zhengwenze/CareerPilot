from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis, from_url

from app.routers import api_router
from app.core.config import Settings, get_settings
from app.core.errors import ApiException, ErrorCode
from app.core.logging import configure_logging
from app.core.responses import error_response
from app.db.session import close_engine
from app.services.storage import MinioObjectStorage
from app.services.token_blocklist import InMemoryTokenBlocklist, RedisTokenBlocklist

logger = logging.getLogger(__name__)


def serialize_error_code(code: ErrorCode | str) -> str:
    return code.value if isinstance(code, ErrorCode) else code


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = getattr(app.state, "settings", get_settings())
    app.state.settings = settings
    redis_client: Redis | None = getattr(app.state, "redis", None)

    if not hasattr(app.state, "token_blocklist") and settings.redis_url:
        redis_client = from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        app.state.token_blocklist = RedisTokenBlocklist(redis_client)
        app.state.redis = redis_client
    elif not hasattr(app.state, "token_blocklist"):
        app.state.token_blocklist = InMemoryTokenBlocklist()
        app.state.redis = None

    if not hasattr(app.state, "object_storage") and settings.storage_provider == "minio":
        app.state.object_storage = MinioObjectStorage(
            endpoint=settings.storage_endpoint,
            access_key=settings.storage_access_key,
            secret_key=settings.storage_secret_key,
            secure=settings.storage_use_ssl,
        )
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
    app.state.settings = config

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        started_at = perf_counter()

        logger.info("[%s] -> %s %s", request_id, request.method, request.url.path)
        response = await call_next(request)
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "[%s] <- %s %s %s %.2fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        payload = error_response(
            request,
            code=serialize_error_code(ErrorCode.VALIDATION_ERROR),
            message="Request validation failed",
            details=exc.errors(),
        )
        return JSONResponse(status_code=422, content=payload.model_dump(mode="json"))

    @app.exception_handler(ApiException)
    async def api_exception_handler(request: Request, exc: ApiException) -> JSONResponse:
        payload = error_response(
            request,
            code=serialize_error_code(exc.code),
            message=exc.message,
            details=exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(mode="json"),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code = {
            400: ErrorCode.BAD_REQUEST,
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            409: ErrorCode.CONFLICT,
            503: ErrorCode.SERVICE_UNAVAILABLE,
        }.get(exc.status_code, ErrorCode.BAD_REQUEST)
        payload = error_response(
            request,
            code=serialize_error_code(code),
            message=str(exc.detail),
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(mode="json"))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error while serving %s", request.url.path, exc_info=exc)
        payload = error_response(
            request,
            code=serialize_error_code(ErrorCode.INTERNAL_SERVER_ERROR),
            message="Internal server error",
        )
        return JSONResponse(status_code=500, content=payload.model_dump(mode="json"))

    app.include_router(api_router)
    return app


app = create_app()
