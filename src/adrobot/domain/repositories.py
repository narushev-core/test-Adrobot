from __future__ import annotations

from datetime import datetime
from types import TracebackType
from typing import Protocol
from uuid import UUID

from adrobot.domain.events import DomainEvent
from adrobot.domain.models import Campaign, KeitaroGroup, Operation


class CampaignRepository(Protocol):
    async def add(self, campaign: Campaign) -> None: ...

    async def get(self, campaign_id: UUID) -> Campaign | None: ...

    async def get_by_alias(self, alias: str) -> Campaign | None: ...

    async def list(self, limit: int, offset: int) -> list[Campaign]: ...

    async def update(self, campaign: Campaign) -> None: ...


class OperationRepository(Protocol):
    async def add(self, operation: Operation) -> None: ...

    async def get(self, operation_id: UUID) -> Operation | None: ...

    async def update(self, operation: Operation) -> None: ...


class GroupRepository(Protocol):
    async def search(self, query: str, limit: int) -> list[KeitaroGroup]: ...

    async def upsert_many(self, groups: list[KeitaroGroup]) -> None: ...

    async def mark_deleted_before(self, synced_at: datetime) -> None: ...


class OutboxRepository(Protocol):
    async def add(self, event: DomainEvent) -> None: ...


class InboxRepository(Protocol):
    async def is_processed(self, event_id: str, handler: str) -> bool: ...

    async def mark_processed(self, event_id: str, handler: str) -> None: ...


class UnitOfWork(Protocol):
    @property
    def campaigns(self) -> CampaignRepository: ...

    @property
    def operations(self) -> OperationRepository: ...

    @property
    def groups(self) -> GroupRepository: ...

    @property
    def outbox(self) -> OutboxRepository: ...

    @property
    def inbox(self) -> InboxRepository: ...

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
