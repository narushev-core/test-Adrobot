"""Ручной запуск синхронизации групп из редактора (docs/SEQUENCE_DIAGRAMS.md#4)."""

from __future__ import annotations

from adrobot.domain.events import GroupsSyncRequested
from adrobot.domain.repositories import UnitOfWork


class RequestGroupsSyncUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> None:
        async with self._uow:
            await self._uow.outbox.add(GroupsSyncRequested(requested_by="user"))
            await self._uow.commit()
