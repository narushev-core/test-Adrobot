from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from adrobot.application.ports import KeitaroGateway, KeitaroRequestError
from adrobot.domain.enums import CampaignStatus
from adrobot.domain.events import CampaignStatusChanged
from adrobot.domain.models import Campaign
from adrobot.domain.repositories import UnitOfWork


class ProcessCampaignCreationUseCase:
    HANDLER_NAME = "campaign.create_or_resume"

    def __init__(
        self,
        uow: UnitOfWork,
        keitaro: KeitaroGateway,
        *,
        domain_id: int,
        traffic_source_id: int,
    ) -> None:
        self._uow = uow
        self._keitaro = keitaro
        self._domain_id = domain_id
        self._traffic_source_id = traffic_source_id

    async def handle(self, campaign_id: UUID, *, event_id: str) -> None:
        campaign = await self._start_or_skip(campaign_id, event_id)
        if campaign is None:
            return

        try:
            await self._ensure_campaign_created(campaign)
            await self._ensure_geo_stream_created(campaign)
            await self._ensure_offer_stream_created(campaign)
        except KeitaroRequestError as exc:
            await self._compensate_and_fail(campaign, exc, event_id)
            return

        campaign.status = CampaignStatus.SUCCESS
        campaign.error = None
        await self._finalize(campaign, event_id)

    async def _start_or_skip(self, campaign_id: UUID, event_id: str) -> Campaign | None:
        """Отмечает начало обработки. Возвращает None, если событие уже полностью обработано."""
        async with self._uow:
            if await self._uow.inbox.is_processed(event_id, self.HANDLER_NAME):
                return None

            campaign = await self._uow.campaigns.get(campaign_id)
            if campaign is None or campaign.status.is_final:
                await self._uow.inbox.mark_processed(event_id, self.HANDLER_NAME)
                await self._uow.commit()
                return None

            campaign.status = CampaignStatus.IN_PROGRESS
            campaign.updated_at = datetime.now(UTC)
            await self._uow.campaigns.update(campaign)
            await self._uow.commit()
            return campaign

    async def _ensure_campaign_created(self, campaign: Campaign) -> None:
        if campaign.keitaro_id is not None:
            return
        keitaro_id = await self._keitaro.find_campaign_by_alias(campaign.alias)
        if keitaro_id is None:
            keitaro_id = await self._keitaro.create_campaign(
                name=campaign.name,
                alias=campaign.alias,
                domain_id=self._domain_id,
                traffic_source_id=self._traffic_source_id,
                group_id=campaign.group_id,
            )
        campaign.keitaro_id = keitaro_id
        await self._save_step(campaign)

    async def _ensure_geo_stream_created(self, campaign: Campaign) -> None:
        if campaign.geo_stream_id is not None:
            return
        assert campaign.keitaro_id is not None
        stream_id = await self._keitaro.create_geo_redirect_stream(
            keitaro_campaign_id=campaign.keitaro_id,
            geo=campaign.geo,
        )
        campaign.geo_stream_id = stream_id
        await self._save_step(campaign)

    async def _ensure_offer_stream_created(self, campaign: Campaign) -> None:
        if campaign.offer_stream_id is not None:
            return
        assert campaign.keitaro_id is not None
        stream_id = await self._keitaro.create_offer_stream(
            keitaro_campaign_id=campaign.keitaro_id,
            offer_id=campaign.offer_id,
        )
        campaign.offer_stream_id = stream_id
        await self._save_step(campaign)

    async def _compensate_and_fail(
        self, campaign: Campaign, exc: KeitaroRequestError, event_id: str
    ) -> None:
        rollback_ok = True
        try:
            if campaign.offer_stream_id is not None:
                await self._keitaro.delete_stream(campaign.offer_stream_id)
            if campaign.geo_stream_id is not None:
                await self._keitaro.delete_stream(campaign.geo_stream_id)
            if campaign.keitaro_id is not None:
                await self._keitaro.delete_campaign(campaign.keitaro_id)
        except Exception:  # noqa: BLE001 - откат не должен маскировать исходную ошибку
            rollback_ok = False

        campaign.status = CampaignStatus.FAILED if rollback_ok else CampaignStatus.ROLLBACK_FAILED
        campaign.error = str(exc)
        await self._finalize(campaign, event_id)

    async def _save_step(self, campaign: Campaign) -> None:
        campaign.updated_at = datetime.now(UTC)
        async with self._uow:
            await self._uow.campaigns.update(campaign)
            await self._uow.commit()

    async def _finalize(self, campaign: Campaign, event_id: str) -> None:
        campaign.updated_at = datetime.now(UTC)
        async with self._uow:
            await self._uow.campaigns.update(campaign)
            await self._uow.outbox.add(
                CampaignStatusChanged(
                    campaign_id=campaign.id,
                    status=campaign.status.value,
                    error=campaign.error,
                )
            )
            await self._uow.inbox.mark_processed(event_id, self.HANDLER_NAME)
            await self._uow.commit()
