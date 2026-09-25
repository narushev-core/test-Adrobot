from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from adrobot.domain.enums import CampaignStatus
from adrobot.domain.models import Campaign
from adrobot.infrastructure.db.uow import SqlAlchemyUnitOfWork


async def _insert_campaign(session_factory, **overrides) -> Campaign:
    now = datetime.now(UTC)
    campaign = Campaign(
        id=uuid4(),
        alias=f"adrobot-{uuid4().hex[:16]}",
        name="Existing campaign",
        geo="US",
        offer_id=1,
        group_id=None,
        status=CampaignStatus.SUCCESS,
        keitaro_id=1,
        geo_stream_id=2,
        offer_stream_id=3,
        created_at=now,
        updated_at=now,
    )
    for key, value in overrides.items():
        setattr(campaign, key, value)
    uow = SqlAlchemyUnitOfWork(session_factory)
    async with uow:
        await uow.campaigns.add(campaign)
        await uow.commit()
    return campaign


def test_create_campaign_returns_202_with_pending_status(client: TestClient, keitaro) -> None:
    keitaro.existing_offer_ids.add(42)

    response = client.post(
        "/api/campaigns", json={"name": "My campaign", "geo": "us", "offer_id": 42}
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["alias"].startswith("adrobot-")


def test_create_campaign_rejects_unknown_offer_with_422(client: TestClient, keitaro) -> None:
    response = client.post("/api/campaigns", json={"name": "X", "geo": "US", "offer_id": 999})
    assert response.status_code == 422


def test_create_campaign_rejects_invalid_geo(client: TestClient, keitaro) -> None:
    keitaro.existing_offer_ids.add(1)
    response = client.post("/api/campaigns", json={"name": "X", "geo": "USA", "offer_id": 1})
    assert response.status_code == 422


def test_create_campaign_rejects_empty_name(client: TestClient, keitaro) -> None:
    keitaro.existing_offer_ids.add(1)
    response = client.post("/api/campaigns", json={"name": "  ", "geo": "US", "offer_id": 1})
    assert response.status_code == 422


async def test_get_campaign_returns_details(client: TestClient, session_factory) -> None:
    campaign = await _insert_campaign(session_factory)

    response = client.get(f"/api/campaigns/{campaign.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(campaign.id)
    assert body["status"] == "success"


def test_get_unknown_campaign_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/campaigns/{uuid4()}")
    assert response.status_code == 404


async def test_list_campaigns_is_paginated_and_filterable_by_status(
    client: TestClient, session_factory
) -> None:
    await _insert_campaign(session_factory, status=CampaignStatus.SUCCESS)
    await _insert_campaign(session_factory, status=CampaignStatus.FAILED)

    response = client.get("/api/campaigns", params={"status": "failed"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "failed"


async def test_campaign_events_stream_returns_current_status_immediately(
    client: TestClient, session_factory
) -> None:
    campaign = await _insert_campaign(session_factory, status=CampaignStatus.SUCCESS)

    response = client.get(f"/api/campaigns/{campaign.id}/events")

    assert response.status_code == 200
    assert 'data: {"status": "success"' in response.text


async def test_get_campaign_offers_reads_live_state_from_keitaro(
    client: TestClient, session_factory, keitaro
) -> None:
    from adrobot.application.ports import OfferStreamState

    campaign = await _insert_campaign(session_factory, offer_stream_id=42)
    keitaro.streams[42] = OfferStreamState(stream_id=42, offer_ids=[1, 2], shares={1: 60, 2: 40})

    response = client.get(f"/api/campaigns/{campaign.id}/offers")

    assert response.status_code == 200
    body = response.json()
    assert body["stream_id"] == 42
    assert body["offers"] == [{"offer_id": 1, "share": 60}, {"offer_id": 2, "share": 40}]


async def test_add_offer_returns_202_with_operation_id(client: TestClient, session_factory) -> None:
    campaign = await _insert_campaign(session_factory)

    response = client.post(f"/api/campaigns/{campaign.id}/offers", json={"offer_id": 5})

    assert response.status_code == 202
    assert "operation_id" in response.json()


async def test_add_offer_to_not_ready_campaign_returns_409(
    client: TestClient, session_factory
) -> None:
    campaign = await _insert_campaign(
        session_factory, status=CampaignStatus.PENDING, keitaro_id=None
    )

    response = client.post(f"/api/campaigns/{campaign.id}/offers", json={"offer_id": 5})

    assert response.status_code == 409
