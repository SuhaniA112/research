from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

engine: AsyncEngine = create_async_engine(
    str(settings.database_url),
    echo=settings.database_echo,
    pool_pre_ping=settings.database_pool_pre_ping,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def ensure_database_exists() -> None:
    """Create the target database if missing (local/dev convenience only).

    Production should provision the database via infrastructure. This never
    drops or recreates an existing database.
    """
    if settings.is_production:
        return

    url = make_url(str(settings.database_url))
    database_name = url.database

    if not database_name:
        return

    maintenance_url = url.set(database="postgres")
    bootstrap_engine = create_async_engine(
        maintenance_url.render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )

    try:
        async with bootstrap_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database_name},
            )
            if exists is None:
                await conn.execute(text(f'CREATE DATABASE "{database_name}"'))
                logger.info("Created database %r", database_name)
    finally:
        await bootstrap_engine.dispose()


async def verify_pgvector_extension() -> None:
    """Verify the pgvector extension is installed.

    Production application roles often lack CREATE EXTENSION privileges. Enable
    pgvector during infrastructure / migration setup with:

        CREATE EXTENSION IF NOT EXISTS vector;

    Startup fails clearly when the extension is missing rather than silently
    falling back to non-vector behavior.
    """
    async with engine.connect() as conn:
        installed = await conn.scalar(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        if installed is None:
            raise RuntimeError(
                "pgvector extension is not installed on this database. "
                "A privileged role must run: CREATE EXTENSION IF NOT EXISTS vector;"
            )


async def ensure_pgvector_extension() -> None:
    """Best-effort create for local/dev; verify-only in production/test.

    Prefer running CREATE EXTENSION via Alembic/infrastructure. This helper
    attempts creation only outside production, then always verifies.
    """
    if not settings.is_production:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as exc:
            logger.warning(
                "Could not CREATE EXTENSION vector (will verify instead): %s", exc
            )

    await verify_pgvector_extension()


def assert_safe_test_database_url(database_url: str) -> None:
    """Refuse destructive test setup against a non-test database.

    The database name must contain 'test' (case-insensitive). Call this from
    test fixtures before dropping/recreating schema.
    """
    url = make_url(database_url)
    database_name = (url.database or "").lower()
    if "test" not in database_name:
        raise RuntimeError(
            f"Refusing to run tests against database {url.database!r}. "
            "Test DATABASE_URL must use a database name containing 'test'."
        )


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
