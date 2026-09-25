from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_pagination import add_pagination

from adrobot.config.common import settings
from adrobot.domain.events import CampaignStatusChanged, OperationStatusChanged
from adrobot.infrastructure.db.db_helper import DatabaseHelper
from adrobot.infrastructure.events.broker import create_broker
from adrobot.infrastructure.keitaro.client import KeitaroClient
from adrobot.infrastructure.sse.hub import SseHub
from adrobot.logging import configure_logging
from adrobot.presentation.api.errors import register_exception_handlers
from adrobot.presentation.api.routers import campaigns, groups, offers, operations

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parents[3].parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    app.state.db_helper = DatabaseHelper(settings.db.database_url)
    app.state.session_factory = app.state.db_helper.session_factory
    app.state.keitaro = KeitaroClient(
        settings.keitaro.url,
        settings.keitaro.api_key.get_secret_value(),
        settings.keitaro.timeout_seconds,
    )
    app.state.hub = SseHub()

    broker = create_broker(settings.kafka.bootstrap_servers)

    @broker.subscriber(
        settings.kafka.events_topic,
        group_id="adrobot-api-sse",
        auto_commit=False,
    )
    async def on_status_event(message: dict[str, Any]) -> None:
        event_type = message.get("event_type")
        if event_type in (CampaignStatusChanged.event_type, OperationStatusChanged.event_type):
            await app.state.hub.publish(message["aggregate_id"], message["payload"])

    await broker.start()
    app.state.broker = broker
    logger.info("API started")
    try:
        yield
    finally:
        await broker.close()
        await app.state.keitaro.aclose()
        await app.state.db_helper.dispose()
        logger.info("API stopped")


def create_app() -> FastAPI:
    configure_logging(settings.log_level, secrets=[settings.keitaro.api_key.get_secret_value()])

    app = FastAPI(
        title="Adrobot",
        description="Обёртка над Keitaro Admin API для создания и редактирования кампаний",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(campaigns.router, prefix="/api")
    app.include_router(operations.router, prefix="/api")
    app.include_router(groups.router, prefix="/api")
    app.include_router(offers.router, prefix="/api")
    add_pagination(app)

    if FRONTEND_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()
