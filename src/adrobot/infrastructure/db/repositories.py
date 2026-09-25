"""Реализации репозиториев поверх SQLAlchemy ORM. Конвертируют ORM-модели в domain dataclass'ы."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from adrobot.domain.enums import CampaignStatus, OperationAction, OperationStatus
from adrobot.domain.events import DomainEvent
from adrobot.domain.models import Campaign, KeitaroGroup, Operation
from adrobot.infrastructure.db.models import (
    CampaignORM,
    KeitaroGroupORM,
    OperationORM,
    OutboxORM,
    ProcessedEventORM,
)


def _campaign_to_domain(row: CampaignORM) -> Campaign:
    return Campaign(
        id=row.id,
        alias=row.alias,
        name=row.name,
        geo=row.geo,
        offer_id=row.offer_id,
        group_id=row.group_id,
        status=CampaignStatus(row.status),
        keitaro_id=row.keitaro_id,
        geo_stream_id=row.geo_stream_id,
        offer_stream_id=row.offer_stream_id,
        error=row.error,
        keitaro_payload=row.keitaro_payload,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _operation_to_domain(row: OperationORM) -> Operation:
    return Operation(
        id=row.id,
        campaign_id=row.campaign_id,
        keitaro_campaign_id=row.keitaro_campaign_id,
        action=OperationAction(row.action),
        offer_id=row.offer_id,
        status=OperationStatus(row.status),
        before=row.before,
        after=row.after,
        error=row.error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _group_to_domain(row: KeitaroGroupORM) -> KeitaroGroup:
    return KeitaroGroup(
        id=row.id, name=row.name, is_deleted=row.is_deleted, synced_at=row.synced_at
    )


class SqlAlchemyCampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, campaign: Campaign) -> None:
        self._session.add(
            CampaignORM(
                id=campaign.id,
                alias=campaign.alias,
                name=campaign.name,
                geo=campaign.geo,
                offer_id=campaign.offer_id,
                group_id=campaign.group_id,
                status=campaign.status.value,
                keitaro_id=campaign.keitaro_id,
                geo_stream_id=campaign.geo_stream_id,
                offer_stream_id=campaign.offer_stream_id,
                error=campaign.error,
                keitaro_payload=campaign.keitaro_payload,
                created_at=campaign.created_at,
                updated_at=campaign.updated_at,
            )
        )
        await self._session.flush()

    async def get(self, campaign_id: UUID) -> Campaign | None:
        row = await self._session.get(CampaignORM, campaign_id)
        return _campaign_to_domain(row) if row else None

    async def get_by_alias(self, alias: str) -> Campaign | None:
        result = await self._session.execute(select(CampaignORM).where(CampaignORM.alias == alias))
        row = result.scalar_one_or_none()
        return _campaign_to_domain(row) if row else None

    async def list(self, limit: int, offset: int) -> list[Campaign]:
        result = await self._session.execute(
            select(CampaignORM).order_by(CampaignORM.created_at.desc()).limit(limit).offset(offset)
        )
        return [_campaign_to_domain(row) for row in result.scalars()]

    async def update(self, campaign: Campaign) -> None:
        await self._session.execute(
            update(CampaignORM)
            .where(CampaignORM.id == campaign.id)
            .values(
                status=campaign.status.value,
                keitaro_id=campaign.keitaro_id,
                geo_stream_id=campaign.geo_stream_id,
                offer_stream_id=campaign.offer_stream_id,
                error=campaign.error,
                keitaro_payload=campaign.keitaro_payload,
                updated_at=campaign.updated_at,
            )
        )
        await self._session.flush()


class SqlAlchemyOperationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, operation: Operation) -> None:
        self._session.add(
            OperationORM(
                id=operation.id,
                campaign_id=operation.campaign_id,
                keitaro_campaign_id=operation.keitaro_campaign_id,
                action=operation.action.value,
                offer_id=operation.offer_id,
                status=operation.status.value,
                before=operation.before,
                after=operation.after,
                error=operation.error,
                created_at=operation.created_at,
                updated_at=operation.updated_at,
            )
        )
        await self._session.flush()

    async def get(self, operation_id: UUID) -> Operation | None:
        row = await self._session.get(OperationORM, operation_id)
        return _operation_to_domain(row) if row else None

    async def update(self, operation: Operation) -> None:
        await self._session.execute(
            update(OperationORM)
            .where(OperationORM.id == operation.id)
            .values(
                status=operation.status.value,
                before=operation.before,
                after=operation.after,
                error=operation.error,
                updated_at=operation.updated_at,
            )
        )
        await self._session.flush()


class SqlAlchemyGroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(self, query: str, limit: int) -> list[KeitaroGroup]:
        stmt = select(KeitaroGroupORM).where(KeitaroGroupORM.is_deleted.is_(False))
        if query:
            stmt = stmt.where(KeitaroGroupORM.name.ilike(f"%{query}%"))
        stmt = stmt.order_by(KeitaroGroupORM.name).limit(limit)
        result = await self._session.execute(stmt)
        return [_group_to_domain(row) for row in result.scalars()]

    async def upsert_many(self, groups: list[KeitaroGroup]) -> None:
        if not groups:
            return
        dialect = self._session.bind.dialect.name if self._session.bind else ""
        if dialect == "postgresql":
            stmt = pg_insert(KeitaroGroupORM).values(
                [
                    {
                        "id": g.id,
                        "name": g.name,
                        "is_deleted": g.is_deleted,
                        "synced_at": g.synced_at,
                    }
                    for g in groups
                ]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[KeitaroGroupORM.id],
                set_={
                    "name": stmt.excluded.name,
                    "is_deleted": stmt.excluded.is_deleted,
                    "synced_at": stmt.excluded.synced_at,
                },
            )
            await self._session.execute(stmt)
        else:
            # Портируемый fallback для тестов на SQLite: нет ON CONFLICT DO UPDATE в общем виде.
            for g in groups:
                existing = await self._session.get(KeitaroGroupORM, g.id)
                if existing is None:
                    self._session.add(
                        KeitaroGroupORM(
                            id=g.id, name=g.name, is_deleted=g.is_deleted, synced_at=g.synced_at
                        )
                    )
                else:
                    existing.name = g.name
                    existing.is_deleted = g.is_deleted
                    existing.synced_at = g.synced_at
        await self._session.flush()

    async def mark_deleted_before(self, synced_at: datetime) -> None:
        await self._session.execute(
            update(KeitaroGroupORM)
            .where(KeitaroGroupORM.synced_at < synced_at)
            .values(is_deleted=True)
        )
        await self._session.flush()


class SqlAlchemyOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: DomainEvent) -> None:
        self._session.add(
            OutboxORM(
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id(),
                event_type=event.event_type,
                payload=event.payload(),
                key=event.partition_key(),
                created_at=datetime.now(UTC),
            )
        )
        await self._session.flush()


class SqlAlchemyInboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_processed(self, event_id: str, handler: str) -> bool:
        row = await self._session.get(ProcessedEventORM, (event_id, handler))
        return row is not None

    async def mark_processed(self, event_id: str, handler: str) -> None:
        self._session.add(
            ProcessedEventORM(event_id=event_id, handler=handler, processed_at=datetime.now(UTC))
        )
        await self._session.flush()
