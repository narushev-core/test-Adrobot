from __future__ import annotations

from datetime import UTC, datetime

from adrobot.application.ports import KeitaroGateway
from adrobot.domain.models import KeitaroGroup
from adrobot.domain.repositories import UnitOfWork


class SyncGroupsUseCase:
    HANDLER_NAME = "groups.sync"

    def __init__(self, uow: UnitOfWork, keitaro: KeitaroGateway) -> None:
        self._uow = uow
        self._keitaro = keitaro

    async def execute(self, *, event_id: str) -> None:
        async with self._uow:
            if await self._uow.inbox.is_processed(event_id, self.HANDLER_NAME):
                return

        synced_at = datetime.now(UTC)
        remote_groups = await self._keitaro.list_groups()

        groups = [
            KeitaroGroup(id=g.id, name=g.name, is_deleted=False, synced_at=synced_at)
            for g in remote_groups
        ]

        async with self._uow:
            await self._uow.groups.upsert_many(groups)
            await self._uow.groups.mark_deleted_before(synced_at)
            await self._uow.inbox.mark_processed(event_id, self.HANDLER_NAME)
            await self._uow.commit()
