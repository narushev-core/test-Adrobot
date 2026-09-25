from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Self

from fastapi_filter.contrib.sqlalchemy import Filter
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDMixin:
    @classmethod
    def _pk_column(cls) -> Any:
        return next(iter(cls.__table__.primary_key.columns))  # type: ignore[attr-defined]

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs: Any) -> Self:
        instance = cls(**kwargs)
        session.add(instance)
        await session.commit()
        return instance

    @classmethod
    async def read(
        cls, session: AsyncSession, pk: Any, options: Sequence[Any] | None = None
    ) -> Self | None:
        stmt = select(cls).where(cls._pk_column() == pk)
        if options:
            stmt = stmt.options(*options)
        result = await session.execute(stmt)
        return result.unique().scalar_one_or_none()

    @classmethod
    async def update(cls, obj: Self, session: AsyncSession, **kwargs: Any) -> Self:
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await session.commit()
        await session.refresh(obj)
        return obj

    @classmethod
    async def delete(cls, session: AsyncSession, pk: Any) -> None:
        await session.execute(delete(cls).where(cls._pk_column() == pk))
        await session.commit()

    @classmethod
    async def list(
        cls,
        session: AsyncSession,
        filters: Filter,
        is_paginate: bool = True,
        options: Sequence[Any] | None = None,
        stmt: Any = None,
    ) -> Any:
        stmt = filters.filter(select(cls) if stmt is None else stmt)
        if getattr(filters, filters.Constants.ordering_field_name, None):
            stmt = filters.sort(stmt)
        if options:
            stmt = stmt.options(*options)

        if is_paginate:
            return await apaginate(session, stmt)

        result = await session.execute(stmt)
        return result.unique().scalars().all()

    async def update_instance(self, session: AsyncSession, **kwargs: Any) -> Self:
        for key, value in kwargs.items():
            setattr(self, key, value)
        await session.commit()
        return self
