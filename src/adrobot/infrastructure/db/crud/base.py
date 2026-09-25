from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy.ext.asyncio import AsyncSession

from adrobot.infrastructure.db.base import Base
from adrobot.infrastructure.db.decorators import sqlalchemy_error_handler


class CRUDBase[T: Base]:
    def __init__(self, db_model: type[T], session: AsyncSession) -> None:
        self.db_model = db_model
        self.session = session

    @sqlalchemy_error_handler
    async def create(self, **kwargs: Any) -> T:
        model = await self.db_model.create(self.session, **kwargs)
        await self.session.refresh(model)
        return model

    async def read(self, obj_pk: Any, options: Sequence[Any] | None = None) -> T | None:
        return await self.db_model.read(self.session, obj_pk, options)

    async def list(
        self, filter: Filter, paginate_response: bool = True, options: Sequence[Any] | None = None
    ) -> Any:
        return await self.db_model.list(self.session, filter, paginate_response, options)

    @sqlalchemy_error_handler
    async def update(self, obj_pk: Any, options: Sequence[Any] | None = None, **kwargs: Any) -> T:
        instance = await self.read(obj_pk, options=options)
        if instance is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        return await self.db_model.update(instance, session=self.session, **kwargs)

    async def delete(self, obj_pk: Any) -> None:
        if await self.read(obj_pk) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        await self.db_model.delete(self.session, obj_pk)
