from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import select

from adrobot.infrastructure.db.base import Base
from adrobot.infrastructure.db.crud.base import CRUDBase
from adrobot.infrastructure.db.models import KeitaroGroupORM


class GroupFilter(Filter):
    search: str | None = None
    order_by: list[str] | None = None

    class Constants(Filter.Constants):
        model = KeitaroGroupORM
        search_model_fields = ["name"]


class GroupCRUD[T: Base](CRUDBase[T]):
    async def list(
        self, filter: Filter, paginate_response: bool = True, options: Sequence[Any] | None = None
    ) -> Any:
        stmt = select(self.db_model).where(self.db_model.is_deleted.is_(False))  # type: ignore[attr-defined]
        return await self.db_model.list(self.session, filter, paginate_response, options, stmt)
