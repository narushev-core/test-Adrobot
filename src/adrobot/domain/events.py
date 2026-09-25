from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_type: ClassVar[str]
    aggregate_type: ClassVar[str]

    def aggregate_id(self) -> str:
        raise NotImplementedError

    def partition_key(self) -> str:
        return self.aggregate_id()

    def payload(self) -> dict[str, Any]:
        return {k: str(v) if isinstance(v, UUID) else v for k, v in asdict(self).items()}


@dataclass(frozen=True, slots=True)
class CampaignCreateRequested(DomainEvent):
    event_type: ClassVar[str] = "campaign.create.requested"
    aggregate_type: ClassVar[str] = "campaign"

    campaign_id: UUID

    def aggregate_id(self) -> str:
        return str(self.campaign_id)


@dataclass(frozen=True, slots=True)
class CampaignStatusChanged(DomainEvent):
    event_type: ClassVar[str] = "campaign.status.changed"
    aggregate_type: ClassVar[str] = "campaign"

    campaign_id: UUID
    status: str
    error: str | None = None

    def aggregate_id(self) -> str:
        return str(self.campaign_id)


@dataclass(frozen=True, slots=True)
class OperationRequested(DomainEvent):
    event_type: ClassVar[str] = "operation.requested"
    aggregate_type: ClassVar[str] = "operation"

    operation_id: UUID
    campaign_id: UUID

    def aggregate_id(self) -> str:
        return str(self.operation_id)

    def partition_key(self) -> str:
        # Ключ партиции — ID кампании: операции одной кампании обрабатываются по порядку.
        return str(self.campaign_id)


@dataclass(frozen=True, slots=True)
class OperationStatusChanged(DomainEvent):
    event_type: ClassVar[str] = "operation.status.changed"
    aggregate_type: ClassVar[str] = "operation"

    operation_id: UUID
    campaign_id: UUID
    status: str
    error: str | None = None

    def aggregate_id(self) -> str:
        return str(self.operation_id)

    def partition_key(self) -> str:
        return str(self.campaign_id)


@dataclass(frozen=True, slots=True)
class GroupsSyncRequested(DomainEvent):
    event_type: ClassVar[str] = "groups.sync.requested"
    aggregate_type: ClassVar[str] = "groups"

    requested_by: str = "scheduler"
    request_id: str = field(default="scheduler")

    def aggregate_id(self) -> str:
        return "groups"
