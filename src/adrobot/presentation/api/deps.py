from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from adrobot.application.ports import KeitaroGateway
from adrobot.infrastructure.db.crud.campaign_crud import CampaignCRUD
from adrobot.infrastructure.db.crud.dependencies import (
    get_campaign_crud,
    get_group_crud,
    get_operation_crud,
)
from adrobot.infrastructure.db.crud.group_crud import GroupCRUD
from adrobot.infrastructure.db.crud.operation_crud import OperationCRUD
from adrobot.infrastructure.db.models import CampaignORM, KeitaroGroupORM, OperationORM
from adrobot.infrastructure.db.uow import SqlAlchemyUnitOfWork
from adrobot.infrastructure.sse.hub import SseHub


def get_keitaro(request: Request) -> KeitaroGateway:
    return request.app.state.keitaro  # type: ignore[no-any-return]


def get_uow(request: Request) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(request.app.state.session_factory)


def get_hub(request: Request) -> SseHub:
    return request.app.state.hub  # type: ignore[no-any-return]


KeitaroDep = Annotated[KeitaroGateway, Depends(get_keitaro)]
UowDep = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]
HubDep = Annotated[SseHub, Depends(get_hub)]
CampaignCRUDDep = Annotated[CampaignCRUD[CampaignORM], Depends(get_campaign_crud(CampaignORM))]
OperationCRUDDep = Annotated[OperationCRUD[OperationORM], Depends(get_operation_crud(OperationORM))]
GroupCRUDDep = Annotated[GroupCRUD[KeitaroGroupORM], Depends(get_group_crud(KeitaroGroupORM))]
