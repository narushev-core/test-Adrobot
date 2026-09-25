from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from adrobot.infrastructure.db.base import Base


class KeitaroGroupORM(Base):
    """Локальная копия групп кампаний из Keitaro для поиска (docs/DATABASE.md)."""

    __tablename__ = "keitaro_groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_keitaro_groups_name", "name"),)
