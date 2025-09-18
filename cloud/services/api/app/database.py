from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .config import ApiSettings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings: ApiSettings = get_settings()
        _engine = create_async_engine(settings.database.dsn, pool_size=settings.database.max_size)
    return _engine


async def get_session() -> AsyncIterator[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        engine = await get_engine()
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with _session_factory() as session:
        yield session
