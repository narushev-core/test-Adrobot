"""Кросс-диалектный UUID: нативный `UUID` в PostgreSQL, `CHAR(32)` в остальных (тесты на SQLite)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return value.hex

    def process_result_value(self, value: Any, dialect: Dialect) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)
