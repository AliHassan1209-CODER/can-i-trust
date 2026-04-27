from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from loguru import logger


# ── Async Engine ────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Base Model ──────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency ──────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables on startup (use Alembic in production)."""
    async with engine.begin() as conn:
        from app.models import user, check_history  # noqa: F401 — import to register models
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")
