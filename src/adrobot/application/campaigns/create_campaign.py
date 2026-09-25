from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from adrobot.application.ports import KeitaroGateway
from adrobot.domain.enums import CampaignStatus
from adrobot.domain.events import CampaignCreateRequested
from adrobot.domain.exceptions import OfferNotFoundError
from adrobot.domain.models import Campaign
from adrobot.domain.repositories import UnitOfWork
from adrobot.domain.value_objects import Alias, CampaignName, Geo


@dataclass(frozen=True, slots=True)
class CreateCampaignCommand:
    name: str
    geo: str
    offer_id: int
    group_id: int | None = None


@dataclass(frozen=True, slots=True)
class CreateCampaignResult:
    campaign_id: UUID
    alias: str
    status: CampaignStatus


class CreateCampaignUseCase:
    def __init__(self, uow: UnitOfWork, keitaro: KeitaroGateway) -> None:
        self._uow = uow
        self._keitaro = keitaro

    async def execute(self, command: CreateCampaignCommand) -> CreateCampaignResult:
        name = CampaignName(command.name)
        geo = Geo(command.geo)

        if not await self._keitaro.offer_exists(command.offer_id):
            raise OfferNotFoundError(command.offer_id)

        now = datetime.now(UTC)
        campaign = Campaign(
            id=uuid4(),
            alias=str(Alias.generate()),
            name=str(name),
            geo=str(geo),
            offer_id=command.offer_id,
            group_id=command.group_id,
            status=CampaignStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        async with self._uow:
            await self._uow.campaigns.add(campaign)
            await self._uow.outbox.add(CampaignCreateRequested(campaign_id=campaign.id))
            await self._uow.commit()

        return CreateCampaignResult(
            campaign_id=campaign.id, alias=campaign.alias, status=campaign.status
        )
