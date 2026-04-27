from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    # ── App ─────────────────────────────────────────────────────
    APP_NAME: str = "Can I Trust?"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Server ──────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database ────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/can_i_trust"
    DATABASE_SYNC_URL: str = "postgresql://postgres:password@localhost:5432/can_i_trust"

    # ── Redis ───────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600

    # ── JWT ─────────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── News API ────────────────────────────────────────────────
    NEWS_API_KEY: str = ""
    NEWS_API_BASE_URL: str = "https://newsapi.org/v2"

    # ── ML Model ────────────────────────────────────────────────
    MODEL_PATH: str = "./app/ml_models/fake_news_model"
    USE_LOCAL_MODEL: bool = True
    HF_MODEL_NAME: str = "distilbert-base-uncased"

    # ── File Upload ─────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "./uploads"

    # ── Rate Limiting ───────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 30
    RATE_LIMIT_ANALYZE: int = 10

    # ── CORS ────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
