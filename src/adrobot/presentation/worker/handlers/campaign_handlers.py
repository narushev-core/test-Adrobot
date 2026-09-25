"""Обработчик события `campaign.create.requested`."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from adrobot.application.campaigns.process_campaign_creation import (
    ProcessCampaignCreationUseCase,
)
from adrobot.application.ports import KeitaroGateway
from adrobot.infrastructure.db.uow import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)


async def handle_campaign_create_requested(
    message: dict[str, Any],
    session_factory: async_sessionmaker[AsyncSession],
    keitaro: KeitaroGateway,
    *,
    domain_id: int,
    traffic_source_id: int,
) -> None:
    campaign_id = UUID(message["payload"]["campaign_id"])
    uow = SqlAlchemyUnitOfWork(session_factory)
    use_case = ProcessCampaignCreationUseCase(
        uow, keitaro, domain_id=domain_id, traffic_source_id=traffic_source_id
    )
    logger.info("Processing campaign.create.requested for campaign %s", campaign_id)
    await use_case.handle(campaign_id, event_id=message["event_id"])
