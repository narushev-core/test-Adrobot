"""
Тестовое FastAPI-приложение: те же роутеры и обработчики ошибок, что и в
`adrobot.presentation.api.main`, но без реального lifespan (без подключения к
Postgres/Kafka) — зависимости подменены на тестовую БД (SQLite) и фейковый Keitaro.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_pagination import add_pagination

from adrobot.infrastructure.db.db_helper import get_db
from adrobot.infrastructure.db.uow import SqlAlchemyUnitOfWork
from adrobot.infrastructure.sse.hub import SseHub
from adrobot.presentation.api import deps
from adrobot.presentation.api.errors import register_exception_handlers
from adrobot.presentation.api.routers import campaigns, groups, offers, operations
from tests.application.fakes import FakeKeitaroGateway


def build_test_app(session_factory, keitaro: FakeKeitaroGateway, hub: SseHub) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(campaigns.router, prefix="/api")
    app.include_router(operations.router, prefix="/api")
    app.include_router(groups.router, prefix="/api")
    app.include_router(offers.router, prefix="/api")
    add_pagination(app)

    app.dependency_overrides[deps.get_uow] = lambda: SqlAlchemyUnitOfWork(session_factory)
    app.dependency_overrides[deps.get_keitaro] = lambda: keitaro
    app.dependency_overrides[deps.get_hub] = lambda: hub

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def keitaro() -> FakeKeitaroGateway:
    return FakeKeitaroGateway()


@pytest.fixture
def hub() -> SseHub:
    return SseHub()


@pytest.fixture
def client(session_factory, keitaro: FakeKeitaroGateway, hub: SseHub) -> TestClient:
    app = build_test_app(session_factory, keitaro, hub)
    return TestClient(app)
