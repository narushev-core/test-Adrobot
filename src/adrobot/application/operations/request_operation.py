from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from adrobot.domain.enums import OperationAction, OperationStatus
from adrobot.domain.events import OperationRequested
from adrobot.domain.exceptions import CampaignNotFoundError, CampaignNotReadyError
from adrobot.domain.models import Operation
from adrobot.domain.repositories import UnitOfWork


@dataclass(frozen=True, slots=True)
class RequestOperationCommand:
    campaign_id: UUID
    action: OperationAction
    offer_id: int


@dataclass(frozen=True, slots=True)
class RequestOperationResult:
    operation_id: UUID
    status: OperationStatus


class RequestOperationUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: RequestOperationCommand) -> RequestOperationResult:
        async with self._uow:
            campaign = await self._uow.campaigns.get(command.campaign_id)
            if campaign is None:
                raise CampaignNotFoundError(command.campaign_id)
            if campaign.keitaro_id is None:
                raise CampaignNotReadyError(command.campaign_id, campaign.status.value)

            now = datetime.now(UTC)
            operation = Operation(
                id=uuid4(),
                campaign_id=campaign.id,
                keitaro_campaign_id=campaign.keitaro_id,
                action=command.action,
                offer_id=command.offer_id,
                status=OperationStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            await self._uow.operations.add(operation)
            await self._uow.outbox.add(
                OperationRequested(operation_id=operation.id, campaign_id=campaign.id)
            )
            await self._uow.commit()

        return RequestOperationResult(operation_id=operation.id, status=operation.status)
