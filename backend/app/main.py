import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.session import dispose_engine
from app.logging_config import set_request_id, setup_logging
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.providers.cache import dispose_redis, get_redis
from app.providers.ratelimit import RedisRateLimiter
from app.providers.triage.factory import build_triage_provider
from app.routes import complaints, health, meta, stats

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings.log_level)

    app.state.settings = settings
    app.state.triage_provider = build_triage_provider(settings)
    app.state.rate_limiter = RedisRateLimiter(get_redis(), settings.rate_limit_per_minute)

    logger.info("civicpulse backend starting", extra={"provider": settings.triage_provider})
    yield

    # Graceful shutdown (SIGTERM): uvicorn has already stopped accepting new connections
    # and drained in-flight requests by the time lifespan shutdown runs. We just close pools.
    logger.info("civicpulse backend shutting down")
    dispose_engine()
    dispose_redis()


app = FastAPI(title="CivicPulse API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(request_id)

    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start

    route = request.scope.get("route")
    path = route.path if route is not None else request.url.path
    REQUEST_COUNT.labels(method=request.method, path=path, status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, path=path).observe(duration)

    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """FastAPI's default is 422 with a generic body; the spec wants 400 with field-level
    errors, matching the same validation machinery used for LLM output (Pydantic)."""
    errors = [
        {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(status_code=400, content={"detail": "validation error", "errors": errors})


app.include_router(complaints.router)
app.include_router(stats.router)
app.include_router(meta.router)
app.include_router(health.router)
