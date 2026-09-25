"""Роутер групп: поиск для автокомплита и ручной запуск синхронизации."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi_filter import FilterDepends
from fastapi_pagination import Page

from adrobot.application.groups.request_sync import RequestGroupsSyncUseCase
from adrobot.infrastructure.db.crud.group_crud import GroupFilter
from adrobot.presentation.api.deps import GroupCRUDDep, UowDep
from adrobot.presentation.api.schemas import GroupResponse

router = APIRouter(tags=["groups"])


@router.get("/groups/search", response_model=Page[GroupResponse])
async def search_groups(
    crud: GroupCRUDDep,
    group_filter: GroupFilter = FilterDepends(GroupFilter),  # noqa: B008
) -> Page[GroupResponse]:
    return await crud.list(group_filter)


@router.post("/groups/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_groups(uow: UowDep) -> dict:
    await RequestGroupsSyncUseCase(uow).execute()
    return {"status": "requested"}
