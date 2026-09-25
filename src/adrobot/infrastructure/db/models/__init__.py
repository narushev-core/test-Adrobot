"""
SQLAlchemy ORM-модели. Таблицы соответствуют docs/DATABASE.md.

Используется generic `JSON` тип (а не `postgresql.JSONB`), чтобы модели оставались
переносимыми: в проде это PostgreSQL JSONB-совместимый JSON, в тестах — SQLite.
"""

__all__ = (
    "Base",
    "CampaignORM",
    "KeitaroGroupORM",
    "OperationORM",
    "OutboxORM",
    "ProcessedEventORM",
)

from adrobot.infrastructure.db.base import Base
from adrobot.infrastructure.db.models.campaign import CampaignORM
from adrobot.infrastructure.db.models.keitaro_group import KeitaroGroupORM
from adrobot.infrastructure.db.models.operation import OperationORM
from adrobot.infrastructure.db.models.outbox import OutboxORM
from adrobot.infrastructure.db.models.processed_event import ProcessedEventORM
