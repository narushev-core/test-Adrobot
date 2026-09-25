from __future__ import annotations

from fastapi_filter.contrib.sqlalchemy import Filter

from adrobot.infrastructure.db.base import Base
from adrobot.infrastructure.db.crud.base import CRUDBase
from adrobot.infrastructure.db.models import CampaignORM


class CampaignFilter(Filter):
    status: str | None = None
    geo: str | None = None
    search: str | None = None
    order_by: list[str] | None = None

    class Constants(Filter.Constants):
        model = CampaignORM
        search_model_fields = ["name", "alias"]


class CampaignCRUD[T: Base](CRUDBase[T]): ...
