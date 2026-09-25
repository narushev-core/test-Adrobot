from datetime import UTC, datetime
from uuid import uuid4

from adrobot.application.operations.process_operation import ProcessOperationUseCase
from adrobot.application.ports import KeitaroRequestError, OfferStreamState
from adrobot.domain.enums import CampaignStatus, OperationAction, OperationStatus
from adrobot.domain.models import Campaign, Operation
from tests.application.fakes import FakeKeitaroGateway

STREAM_ID = 900


async def _create_ready_campaign(uow) -> Campaign:
    now = datetime.now(UTC)
    campaign = Campaign(
        id=uuid4(),
        alias=f"adrobot-{uuid4().hex[:16]}",
        name="Test campaign",
        geo="US",
        offer_id=1,
        group_id=None,
        status=CampaignStatus.SUCCESS,
        keitaro_id=1,
        geo_stream_id=2,
        offer_stream_id=STREAM_ID,
        created_at=now,
        updated_at=now,
    )
    async with uow:
        await uow.campaigns.add(campaign)
        await uow.commit()
    return campaign


async def _create_operation(
    uow, campaign: Campaign, action: OperationAction, offer_id: int
) -> Operation:
    now = datetime.now(UTC)
    operation = Operation(
        id=uuid4(),
        campaign_id=campaign.id,
        keitaro_campaign_id=campaign.keitaro_id,
        action=action,
        offer_id=offer_id,
        status=OperationStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    async with uow:
        await uow.operations.add(operation)
        await uow.commit()
    return operation


async def test_add_offer_updates_stream_and_recalculates_shares(uow) -> None:
    campaign = await _create_ready_campaign(uow)
    keitaro = FakeKeitaroGateway(
        streams={STREAM_ID: OfferStreamState(stream_id=STREAM_ID, offer_ids=[1], shares={1: 100})}
    )
    operation = await _create_operation(uow, campaign, OperationAction.ADD_OFFER, offer_id=2)

    use_case = ProcessOperationUseCase(uow, keitaro)
    await use_case.handle(operation.id, event_id="evt-1")

    async with uow:
        updated = await uow.operations.get(operation.id)
    assert updated.status is OperationStatus.SUCCESS
    assert updated.before == [1]
    assert updated.after == [1, 2]
    new_state = keitaro.streams[STREAM_ID]
    assert sum(new_state.shares.values()) == 100


async def test_add_offer_already_present_is_idempotent_without_keitaro_call(uow) -> None:
    campaign = await _create_ready_campaign(uow)
    keitaro = FakeKeitaroGateway(
        streams={
            STREAM_ID: OfferStreamState(
                stream_id=STREAM_ID, offer_ids=[1, 2], shares={1: 50, 2: 50}
            )
        }
    )
    operation = await _create_operation(uow, campaign, OperationAction.ADD_OFFER, offer_id=2)

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("update_offer_stream must not be called for a no-op add")

    keitaro.update_offer_stream = fail_if_called  # type: ignore[method-assign]

    use_case = ProcessOperationUseCase(uow, keitaro)
    await use_case.handle(operation.id, event_id="evt-1")

    async with uow:
        updated = await uow.operations.get(operation.id)
    assert updated.status is OperationStatus.SUCCESS
    assert updated.before == updated.after == [1, 2]


async def test_remove_offer_updates_stream(uow) -> None:
    campaign = await _create_ready_campaign(uow)
    keitaro = FakeKeitaroGateway(
        streams={
            STREAM_ID: OfferStreamState(
                stream_id=STREAM_ID, offer_ids=[1, 2], shares={1: 50, 2: 50}
            )
        }
    )
    operation = await _create_operation(uow, campaign, OperationAction.REMOVE_OFFER, offer_id=2)

    use_case = ProcessOperationUseCase(uow, keitaro)
    await use_case.handle(operation.id, event_id="evt-1")

    async with uow:
        updated = await uow.operations.get(operation.id)
    assert updated.after == [1]
    assert keitaro.streams[STREAM_ID].offer_ids == [1]
    assert keitaro.streams[STREAM_ID].shares == {1: 100}


async def test_permanent_keitaro_error_marks_operation_failed(uow) -> None:
    campaign = await _create_ready_campaign(uow)
    keitaro = FakeKeitaroGateway(
        streams={STREAM_ID: OfferStreamState(stream_id=STREAM_ID, offer_ids=[1], shares={1: 100})},
        fail_update_offer_stream=KeitaroRequestError("bad request", status_code=400),
    )
    operation = await _create_operation(uow, campaign, OperationAction.ADD_OFFER, offer_id=2)

    use_case = ProcessOperationUseCase(uow, keitaro)
    await use_case.handle(operation.id, event_id="evt-1")

    async with uow:
        updated = await uow.operations.get(operation.id)
    assert updated.status is OperationStatus.FAILED
    assert updated.error is not None


async def test_redelivered_event_after_success_is_a_noop(uow) -> None:
    campaign = await _create_ready_campaign(uow)
    keitaro = FakeKeitaroGateway(
        streams={STREAM_ID: OfferStreamState(stream_id=STREAM_ID, offer_ids=[1], shares={1: 100})}
    )
    operation = await _create_operation(uow, campaign, OperationAction.ADD_OFFER, offer_id=2)
    use_case = ProcessOperationUseCase(uow, keitaro)

    await use_case.handle(operation.id, event_id="evt-1")

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("Keitaro must not be called again for an already-processed event")

    keitaro.get_offer_stream_state = fail_if_called  # type: ignore[method-assign]

    await use_case.handle(operation.id, event_id="evt-1")
