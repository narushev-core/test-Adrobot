from datetime import UTC, datetime
from uuid import uuid4

from adrobot.application.campaigns.process_campaign_creation import (
    ProcessCampaignCreationUseCase,
)
from adrobot.application.ports import KeitaroRequestError
from adrobot.domain.enums import CampaignStatus
from adrobot.domain.models import Campaign
from tests.application.fakes import FakeKeitaroGateway

DOMAIN_ID = 1
TRAFFIC_SOURCE_ID = 1


async def _create_pending_campaign(uow, **overrides) -> Campaign:
    now = datetime.now(UTC)
    campaign = Campaign(
        id=uuid4(),
        alias=f"adrobot-{uuid4().hex[:16]}",
        name="Test campaign",
        geo="US",
        offer_id=42,
        group_id=None,
        status=CampaignStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    for key, value in overrides.items():
        setattr(campaign, key, value)
    async with uow:
        await uow.campaigns.add(campaign)
        await uow.commit()
    return campaign


def _make_use_case(uow, keitaro: FakeKeitaroGateway) -> ProcessCampaignCreationUseCase:
    return ProcessCampaignCreationUseCase(
        uow, keitaro, domain_id=DOMAIN_ID, traffic_source_id=TRAFFIC_SOURCE_ID
    )


async def test_successful_creation_sets_all_ids_and_success_status(uow) -> None:
    campaign = await _create_pending_campaign(uow)
    keitaro = FakeKeitaroGateway()
    use_case = _make_use_case(uow, keitaro)

    await use_case.handle(campaign.id, event_id="evt-1")

    async with uow:
        updated = await uow.campaigns.get(campaign.id)
    assert updated.status is CampaignStatus.SUCCESS
    assert updated.keitaro_id is not None
    assert updated.geo_stream_id is not None
    assert updated.offer_stream_id is not None
    assert updated.error is None


async def test_permanent_error_triggers_compensation_and_failed_status(uow) -> None:
    campaign = await _create_pending_campaign(uow)
    keitaro = FakeKeitaroGateway(
        fail_create_offer_stream=KeitaroRequestError("некорректный оффер", status_code=400)
    )
    use_case = _make_use_case(uow, keitaro)

    await use_case.handle(campaign.id, event_id="evt-1")

    async with uow:
        updated = await uow.campaigns.get(campaign.id)
    assert updated.status is CampaignStatus.FAILED
    assert updated.error is not None
    # Уже созданные сущности (кампания и гео-поток) должны быть удалены компенсацией.
    assert keitaro.deleted_campaigns == [updated.keitaro_id]
    assert keitaro.deleted_streams == [updated.geo_stream_id]


async def test_rollback_failure_sets_rollback_failed_status(uow) -> None:
    campaign = await _create_pending_campaign(uow)
    keitaro = FakeKeitaroGateway(
        fail_create_offer_stream=KeitaroRequestError("некорректный оффер", status_code=400),
    )
    use_case = _make_use_case(uow, keitaro)

    async def failing_delete_stream(stream_id: int) -> None:
        raise RuntimeError("Keitaro недоступен во время отката")

    keitaro.delete_stream = failing_delete_stream  # type: ignore[method-assign]

    await use_case.handle(campaign.id, event_id="evt-1")

    async with uow:
        updated = await uow.campaigns.get(campaign.id)
    assert updated.status is CampaignStatus.ROLLBACK_FAILED


async def test_resume_after_partial_progress_does_not_recreate_campaign(uow) -> None:
    """Кампания и гео-поток уже созданы (например, воркер упал после шага 2)."""
    keitaro = FakeKeitaroGateway()
    campaign = await _create_pending_campaign(
        uow,
        status=CampaignStatus.IN_PROGRESS,
        keitaro_id=555,
        geo_stream_id=777,
    )
    keitaro.campaigns_by_alias[campaign.alias] = 555

    use_case = _make_use_case(uow, keitaro)
    await use_case.handle(campaign.id, event_id="evt-1")

    assert keitaro.create_campaign_calls == 0  # кампания не создавалась повторно
    async with uow:
        updated = await uow.campaigns.get(campaign.id)
    assert updated.status is CampaignStatus.SUCCESS
    assert updated.keitaro_id == 555
    assert updated.geo_stream_id == 777
    assert updated.offer_stream_id is not None


async def test_redelivered_event_after_success_is_a_noop(uow) -> None:
    campaign = await _create_pending_campaign(uow)
    keitaro = FakeKeitaroGateway()
    use_case = _make_use_case(uow, keitaro)

    await use_case.handle(campaign.id, event_id="evt-1")
    calls_after_first_run = keitaro.create_campaign_calls

    # Событие доставлено повторно (at-least-once) после полного успеха.
    await use_case.handle(campaign.id, event_id="evt-1")

    assert keitaro.create_campaign_calls == calls_after_first_run
