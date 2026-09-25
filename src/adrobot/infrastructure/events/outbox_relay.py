"""
Transactional outbox relay (docs/SEQUENCE_DIAGRAMS.md#1-доставка-события).

Периодически выбирает неопубликованные события через
`SELECT ... WHERE published_at IS NULL ORDER BY created_at LIMIT N FOR UPDATE SKIP LOCKED`,
публикует их в Redpanda и проставляет `published_at`. `SKIP LOCKED` (на PostgreSQL)
позволяет запускать несколько relay параллельно без двойной публикации одной строки.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import UTC, datetime

from faststream.kafka import KafkaBroker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from adrobot.infrastructure.db.models import OutboxORM

logger = logging.getLogger(__name__)


class OutboxRelay:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        broker: KafkaBroker,
        *,
        topic: str,
        interval_seconds: float,
        batch_size: int,
    ) -> None:
        self._session_factory = session_factory
        self._broker = broker
        self._topic = topic
        self._interval_seconds = interval_seconds
        self._batch_size = batch_size
        self._stopped = asyncio.Event()

    def stop(self) -> None:
        self._stopped.set()

    async def run_forever(self) -> None:
        logger.info("Outbox relay started (topic=%s)", self._topic)
        while not self._stopped.is_set():
            try:
                published = await self.relay_once()
            except Exception:
                logger.exception("Outbox relay iteration failed")
                published = 0

            if published < self._batch_size:
                with suppress(TimeoutError):
                    await asyncio.wait_for(self._stopped.wait(), timeout=self._interval_seconds)

    async def relay_once(self) -> int:
        async with self._session_factory() as session:
            async with session.begin():
                rows = await self._select_batch(session)
                for row in rows:
                    await self._publish_row(session, row)
            return len(rows)

    async def _select_batch(self, session: AsyncSession) -> list[OutboxORM]:
        stmt = (
            select(OutboxORM)
            .where(OutboxORM.published_at.is_(None))
            .order_by(OutboxORM.created_at)
            .limit(self._batch_size)
        )
        dialect = session.bind.dialect.name if session.bind else ""
        if dialect == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
        result = await session.execute(stmt)
        return list(result.scalars())

    async def _publish_row(self, session: AsyncSession, row: OutboxORM) -> None:
        message = {
            "event_id": str(row.id),
            "event_type": row.event_type,
            "aggregate_type": row.aggregate_type,
            "aggregate_id": row.aggregate_id,
            "payload": row.payload,
        }
        try:
            await self._broker.publish(
                message,  # type: ignore[arg-type]
                topic=self._topic,
                key=row.key.encode(),
            )
        except Exception as exc:  # noqa: BLE001 - строка остаётся неопубликованной, попробуем снова
            row.attempts += 1
            row.last_error = str(exc)
            logger.warning("Failed to publish outbox event %s: %s", row.id, exc)
            return
        row.published_at = datetime.now(UTC)
