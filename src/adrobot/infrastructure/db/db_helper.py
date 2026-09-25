from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Request
from sqlalchemy import exc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class DatabaseHelper:
    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 30,
        max_overflow: int = 60,
        pool_timeout: int = 15,
        pool_recycle: int = 1800,
    ) -> None:
        self.engine = create_async_engine(
            database_url,
            echo=echo,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    async def dispose(self) -> None:
        await self.engine.dispose()

    @asynccontextmanager
    async def get_db_session(self) -> AsyncIterator[AsyncSession]:
        session = self.session_factory()
        try:
            yield session
        except exc.SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    db_helper: DatabaseHelper = request.app.state.db_helper
    async with db_helper.get_db_session() as session:
        yield session
