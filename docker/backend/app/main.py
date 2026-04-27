"""
Can I Trust? — FastAPI Application Entry Point
================================================
Startup order:
  1. Load settings from .env
  2. Connect Redis
  3. Create DB tables
  4. Load ML model
  5. Register all routers
  6. Start uvicorn server
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.core.config import settings
from app.core.database import create_tables
from app.core.redis_client import init_redis, close_redis
from app.services.ml_service import ml
from app.api.routes import auth, analyze, news


# ── Logging Setup ────────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}",
    level="DEBUG" if settings.DEBUG else "INFO",
)
logger.add("/tmp/app.log", rotation="10 MB", retention="7 days", level="INFO")


# ── Lifespan (startup / shutdown) ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_redis()
    await create_tables()
    ml.load()                  # load ML model (non-blocking fallback if unavailable)
    logger.success("All services ready. API is live.")
    yield
    # ── SHUTDOWN ──
    await close_redis()
    logger.info("Server shutting down.")


# ── App Instance ─────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered fake news detection API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handlers ────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"])
        errors.append({"field": field, "message": error["msg"]})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Routers ──────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router,    prefix=API_PREFIX)
app.include_router(analyze.router, prefix=API_PREFIX)
app.include_router(news.router,    prefix=API_PREFIX)


# ── Health Check ─────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {
        "status":      "ok",
        "app":         settings.APP_NAME,
        "version":     settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "model_loaded": ml.is_loaded,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs":    "/docs",
        "health":  "/health",
    }
