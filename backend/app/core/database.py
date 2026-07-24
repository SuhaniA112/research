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
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def ensure_database_exists() -> None:
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


async def ensure_pgvector_extension() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
