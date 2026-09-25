from __future__ import annotations

from uuid import UUID

from adrobot.application.ports import KeitaroGateway, OfferStreamState
from adrobot.domain.exceptions import CampaignNotFoundError, CampaignNotReadyError
from adrobot.domain.repositories import UnitOfWork


class GetCampaignOffersUseCase:
    def __init__(self, uow: UnitOfWork, keitaro: KeitaroGateway) -> None:
        self._uow = uow
        self._keitaro = keitaro

    async def execute(self, campaign_id: UUID) -> OfferStreamState:
        async with self._uow:
            campaign = await self._uow.campaigns.get(campaign_id)
        if campaign is None:
            raise CampaignNotFoundError(campaign_id)
        if campaign.offer_stream_id is None:
            raise CampaignNotReadyError(campaign_id, campaign.status.value)
        return await self._keitaro.get_offer_stream_state(campaign.offer_stream_id)
