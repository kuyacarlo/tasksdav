from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.models import Base

settings = get_settings()
engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_pre_ping=True,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

_schema_ready = False


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    await init_db()
    _schema_ready = True


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    await ensure_schema()
    async with SessionLocal() as session:
        yield session
