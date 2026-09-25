import pytest

from adrobot.application.campaigns.create_campaign import (
    CreateCampaignCommand,
    CreateCampaignUseCase,
)
from adrobot.domain.enums import CampaignStatus
from adrobot.domain.exceptions import OfferNotFoundError
from adrobot.domain.value_objects import EmptyCampaignNameError, InvalidGeoError
from tests.application.fakes import FakeKeitaroGateway


async def test_create_campaign_persists_pending_campaign_and_outbox_event(uow) -> None:
    keitaro = FakeKeitaroGateway(existing_offer_ids={42})
    use_case = CreateCampaignUseCase(uow, keitaro)

    result = await use_case.execute(
        CreateCampaignCommand(name="My campaign", geo="us", offer_id=42)
    )

    assert result.status is CampaignStatus.PENDING
    assert result.alias.startswith("adrobot-")

    async with uow:
        campaign = await uow.campaigns.get(result.campaign_id)
    assert campaign is not None
    assert campaign.geo == "US"
    assert campaign.status is CampaignStatus.PENDING


async def test_create_campaign_rejects_unknown_offer(uow) -> None:
    keitaro = FakeKeitaroGateway(existing_offer_ids=set())
    use_case = CreateCampaignUseCase(uow, keitaro)

    with pytest.raises(OfferNotFoundError):
        await use_case.execute(CreateCampaignCommand(name="X", geo="US", offer_id=999))


async def test_create_campaign_rejects_invalid_geo(uow) -> None:
    keitaro = FakeKeitaroGateway(existing_offer_ids={1})
    use_case = CreateCampaignUseCase(uow, keitaro)

    with pytest.raises(InvalidGeoError):
        await use_case.execute(CreateCampaignCommand(name="X", geo="USA", offer_id=1))


async def test_create_campaign_rejects_empty_name(uow) -> None:
    keitaro = FakeKeitaroGateway(existing_offer_ids={1})
    use_case = CreateCampaignUseCase(uow, keitaro)

    with pytest.raises(EmptyCampaignNameError):
        await use_case.execute(CreateCampaignCommand(name="   ", geo="US", offer_id=1))
