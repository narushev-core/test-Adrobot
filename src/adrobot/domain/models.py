"""
Доменные модели кампании и операции редактора.

Это dataclass-снимки состояния (не ORM), которые ходят между application-слоем
и репозиториями. Persistence-детали (таблицы, JSON-колонки) живут в infrastructure.
Статусы и действия — в adrobot.domain.enums.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from adrobot.domain.enums import CampaignStatus, OperationAction, OperationStatus


@dataclass(slots=True)
class Campaign:
    id: UUID
    alias: str
    name: str
    geo: str
    offer_id: int
    group_id: int | None
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime
    keitaro_id: int | None = None
    geo_stream_id: int | None = None
    offer_stream_id: int | None = None
    error: str | None = None
    keitaro_payload: dict | None = None


@dataclass(slots=True)
class Operation:
    id: UUID
    campaign_id: UUID
    keitaro_campaign_id: int
    action: OperationAction
    offer_id: int
    status: OperationStatus
    created_at: datetime
    updated_at: datetime
    before: list[int] | None = None
    after: list[int] | None = None
    error: str | None = None


@dataclass(slots=True)
class KeitaroGroup:
    id: int
    name: str
    is_deleted: bool
    synced_at: datetime


@dataclass(slots=True)
class OutboxMessage:
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: dict
    key: str
    id: int | None = None
    created_at: datetime | None = None
    published_at: datetime | None = None
    attempts: int = 0
    last_error: str | None = None
