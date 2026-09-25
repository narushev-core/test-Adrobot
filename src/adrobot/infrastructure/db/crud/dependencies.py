from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from adrobot.infrastructure.db.crud.base import CRUDBase
from adrobot.infrastructure.db.crud.campaign_crud import CampaignCRUD
from adrobot.infrastructure.db.crud.group_crud import GroupCRUD
from adrobot.infrastructure.db.crud.operation_crud import OperationCRUD
from adrobot.infrastructure.db.db_helper import get_db


def get_base_crud(db_model):  # noqa: ANN001, ANN201
    async def _get_crud(session: AsyncSession = Depends(get_db)) -> CRUDBase:  # noqa: B008
        return CRUDBase(db_model, session)

    return _get_crud


def get_campaign_crud(db_model):  # noqa: ANN001, ANN201
    async def _get_crud(session: AsyncSession = Depends(get_db)) -> CampaignCRUD:  # noqa: B008
        return CampaignCRUD(db_model, session)

    return _get_crud


def get_operation_crud(db_model):  # noqa: ANN001, ANN201
    async def _get_crud(session: AsyncSession = Depends(get_db)) -> OperationCRUD:  # noqa: B008
        return OperationCRUD(db_model, session)

    return _get_crud


def get_group_crud(db_model):  # noqa: ANN001, ANN201
    async def _get_crud(session: AsyncSession = Depends(get_db)) -> GroupCRUD:  # noqa: B008
        return GroupCRUD(db_model, session)

    return _get_crud
