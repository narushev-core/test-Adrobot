from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from adrobot.infrastructure.db.base import Base
from adrobot.infrastructure.db.types import GUID


class CampaignORM(Base):
    """Кампании, созданные через сервис (docs/DATABASE.md)."""

    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    alias: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    geo: Mapped[str] = mapped_column(String(2), nullable=False)
    offer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    keitaro_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    geo_stream_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    offer_stream_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    keitaro_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_campaigns_status", "status"),)
