"""Обработчик события `operation.requested`."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from adrobot.application.operations.process_operation import ProcessOperationUseCase
from adrobot.application.ports import KeitaroGateway
from adrobot.infrastructure.db.uow import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)


async def handle_operation_requested(
    message: dict[str, Any],
    session_factory: async_sessionmaker[AsyncSession],
    keitaro: KeitaroGateway,
) -> None:
    operation_id = UUID(message["payload"]["operation_id"])
    uow = SqlAlchemyUnitOfWork(session_factory)
    use_case = ProcessOperationUseCase(uow, keitaro)
    logger.info("Processing operation.requested for operation %s", operation_id)
    await use_case.handle(operation_id, event_id=message["event_id"])
