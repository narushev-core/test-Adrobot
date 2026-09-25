"""Обработчик события `groups.sync.requested`."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from adrobot.application.groups.sync_groups import SyncGroupsUseCase
from adrobot.application.ports import KeitaroGateway
from adrobot.infrastructure.db.uow import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)


async def handle_groups_sync_requested(
    message: dict[str, Any],
    session_factory: async_sessionmaker[AsyncSession],
    keitaro: KeitaroGateway,
) -> None:
    uow = SqlAlchemyUnitOfWork(session_factory)
    use_case = SyncGroupsUseCase(uow, keitaro)
    logger.info("Processing groups.sync.requested")
    try:
        await use_case.execute(event_id=message["event_id"])
    except Exception:
        logger.exception("Groups sync failed")
