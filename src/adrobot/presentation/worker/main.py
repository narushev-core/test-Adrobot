from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from faststream import FastStream

from adrobot.config.common import settings
from adrobot.domain.events import CampaignCreateRequested, GroupsSyncRequested, OperationRequested
from adrobot.infrastructure.db.db_helper import DatabaseHelper
from adrobot.infrastructure.db.uow import SqlAlchemyUnitOfWork
from adrobot.infrastructure.events.broker import create_broker
from adrobot.infrastructure.events.outbox_relay import OutboxRelay
from adrobot.infrastructure.keitaro.client import KeitaroClient
from adrobot.logging import configure_logging
from adrobot.presentation.worker.handlers.campaign_handlers import (
    handle_campaign_create_requested,
)
from adrobot.presentation.worker.handlers.group_handlers import handle_groups_sync_requested
from adrobot.presentation.worker.handlers.operation_handlers import handle_operation_requested

logger = logging.getLogger(__name__)

configure_logging(settings.log_level, secrets=[settings.keitaro.api_key.get_secret_value()])

db_helper = DatabaseHelper(settings.db.database_url)
session_factory = db_helper.session_factory
keitaro = KeitaroClient(
    settings.keitaro.url,
    settings.keitaro.api_key.get_secret_value(),
    settings.keitaro.timeout_seconds,
)
broker = create_broker(settings.kafka.bootstrap_servers)
relay = OutboxRelay(
    session_factory,
    broker,
    topic=settings.kafka.events_topic,
    interval_seconds=settings.outbox.relay_interval_seconds,
    batch_size=settings.outbox.relay_batch_size,
)
scheduler = AsyncIOScheduler()


@broker.subscriber(
    settings.kafka.events_topic,
    group_id="adrobot-worker",
    auto_commit=False,
)
async def on_event(message: dict[str, Any]) -> None:
    event_type = message.get("event_type")
    if event_type == CampaignCreateRequested.event_type:
        await handle_campaign_create_requested(
            message,
            session_factory,
            keitaro,
            domain_id=settings.keitaro.domain_id,
            traffic_source_id=settings.keitaro.traffic_source_id,
        )
    elif event_type == OperationRequested.event_type:
        await handle_operation_requested(message, session_factory, keitaro)
    elif event_type == GroupsSyncRequested.event_type:
        await handle_groups_sync_requested(message, session_factory, keitaro)


async def _schedule_groups_sync() -> None:
    uow = SqlAlchemyUnitOfWork(session_factory)
    async with uow:
        await uow.outbox.add(GroupsSyncRequested(requested_by="scheduler"))
        await uow.commit()


@asynccontextmanager
async def lifespan():  # noqa: ANN201
    relay_task = asyncio.create_task(relay.run_forever())
    scheduler.add_job(
        _schedule_groups_sync,
        trigger=IntervalTrigger(minutes=settings.groups.sync_interval_minutes),
        id="groups-sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Worker started")
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        relay.stop()
        relay_task.cancel()
        await keitaro.aclose()
        await db_helper.dispose()
        logger.info("Worker stopped")


app = FastStream(broker, lifespan=lifespan)
