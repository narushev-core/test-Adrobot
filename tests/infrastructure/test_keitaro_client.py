"""Тесты HTTP-клиента Keitaro на моках respx (NFR-12: тесты с моками Keitaro API)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from adrobot.application.ports import (
    KeitaroRequestError,
    KeitaroTimeoutError,
    KeitaroUnavailableError,
)
from adrobot.infrastructure.keitaro.client import KeitaroClient

BASE_URL = "https://keitaro.test"
API = f"{BASE_URL}/admin_api/v1"


@pytest.fixture
async def client():
    c = KeitaroClient(BASE_URL, "secret-key", timeout_seconds=1.0)
    yield c
    await c.aclose()


@respx.mock
async def test_offer_exists_true(client: KeitaroClient) -> None:
    respx.get(f"{API}/offers/42").mock(return_value=httpx.Response(200, json={"id": 42}))
    assert await client.offer_exists(42) is True


@respx.mock
async def test_offer_exists_false_on_404(client: KeitaroClient) -> None:
    respx.get(f"{API}/offers/999").mock(
        return_value=httpx.Response(404, json={"message": "not found"})
    )
    assert await client.offer_exists(999) is False


@respx.mock
async def test_request_sends_api_key_header(client: KeitaroClient) -> None:
    route = respx.get(f"{API}/offers/1").mock(return_value=httpx.Response(200, json={}))
    await client.offer_exists(1)
    assert route.calls.last.request.headers["Api-Key"] == "secret-key"


@respx.mock
async def test_timeout_raises_keitaro_timeout_error(client: KeitaroClient) -> None:
    respx.get(f"{API}/offers/1").mock(side_effect=httpx.TimeoutException("timed out"))
    with pytest.raises(KeitaroTimeoutError):
        await client.offer_exists(1)


@respx.mock
async def test_connection_error_raises_keitaro_unavailable(client: KeitaroClient) -> None:
    respx.get(f"{API}/offers/1").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(KeitaroUnavailableError):
        await client.offer_exists(1)


@respx.mock
async def test_server_error_raises_keitaro_unavailable(client: KeitaroClient) -> None:
    respx.get(f"{API}/offers/1").mock(return_value=httpx.Response(500))
    with pytest.raises(KeitaroUnavailableError):
        await client.offer_exists(1)


@respx.mock
async def test_bad_request_raises_keitaro_request_error(client: KeitaroClient) -> None:
    respx.post(f"{API}/campaigns").mock(
        return_value=httpx.Response(400, json={"message": "invalid domain_id"})
    )
    with pytest.raises(KeitaroRequestError) as exc_info:
        await client.create_campaign(
            name="X", alias="adrobot-1", domain_id=1, traffic_source_id=1, group_id=None
        )
    assert exc_info.value.status_code == 400
    assert "invalid domain_id" in str(exc_info.value)


@respx.mock
async def test_create_campaign_sends_native_alias_and_traffic_source(
    client: KeitaroClient,
) -> None:
    route = respx.post(f"{API}/campaigns").mock(return_value=httpx.Response(200, json={"id": 777}))
    campaign_id = await client.create_campaign(
        name="X", alias="adrobot-1", domain_id=1, traffic_source_id=9, group_id=5
    )
    assert campaign_id == 777
    body = json.loads(route.calls.last.request.content)
    assert body["alias"] == "adrobot-1"
    assert body["traffic_source_id"] == 9
    assert body["domain_id"] == 1
    assert body["group_id"] == 5


@respx.mock
async def test_find_campaign_by_alias_paginates_until_match(client: KeitaroClient) -> None:
    page_1 = [{"id": i, "alias": f"other-{i}"} for i in range(200)]
    page_2 = [{"id": 500, "alias": "adrobot-target"}]
    respx.get(f"{API}/campaigns", params={"limit": "200", "offset": "0"}).mock(
        return_value=httpx.Response(200, json=page_1)
    )
    respx.get(f"{API}/campaigns", params={"limit": "200", "offset": "200"}).mock(
        return_value=httpx.Response(200, json=page_2)
    )
    assert await client.find_campaign_by_alias("adrobot-target") == 500


@respx.mock
async def test_find_campaign_by_alias_returns_none_when_not_found(client: KeitaroClient) -> None:
    respx.get(f"{API}/campaigns", params={"limit": "200", "offset": "0"}).mock(
        return_value=httpx.Response(200, json=[{"id": 1, "alias": "other"}])
    )
    assert await client.find_campaign_by_alias("adrobot-missing") is None


@respx.mock
async def test_update_offer_stream_sends_share_payload(client: KeitaroClient) -> None:
    route = respx.put(f"{API}/streams/10").mock(return_value=httpx.Response(200, json={}))
    await client.update_offer_stream(10, [1, 2], {1: 60, 2: 40})
    body = json.loads(route.calls.last.request.content)
    assert body["offers"] == [{"offer_id": 1, "share": 60}, {"offer_id": 2, "share": 40}]


@respx.mock
async def test_get_offer_stream_state_parses_offers(client: KeitaroClient) -> None:
    respx.get(f"{API}/streams/10").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 10,
                "offers": [
                    {"offer_id": 1, "share": 70},
                    {"offer_id": 2, "share": 30},
                ],
            },
        )
    )
    state = await client.get_offer_stream_state(10)
    assert state.offer_ids == [1, 2]
    assert state.shares == {1: 70, 2: 30}


@respx.mock
async def test_create_geo_redirect_stream_uses_regular_type_and_country_filter(
    client: KeitaroClient,
) -> None:
    route = respx.post(f"{API}/streams").mock(return_value=httpx.Response(200, json={"id": 55}))
    stream_id = await client.create_geo_redirect_stream(keitaro_campaign_id=1, geo="US")
    assert stream_id == 55
    body = json.loads(route.calls.last.request.content)
    assert body["schema"] == "redirect"
    assert body["type"] == "regular"
    assert body["filters"] == [{"name": "country", "mode": "accept", "payload": ["US"]}]


@respx.mock
async def test_create_offer_stream_uses_default_type_and_offers_list(
    client: KeitaroClient,
) -> None:
    route = respx.post(f"{API}/streams").mock(return_value=httpx.Response(200, json={"id": 56}))
    stream_id = await client.create_offer_stream(keitaro_campaign_id=1, offer_id=42)
    assert stream_id == 56
    body = json.loads(route.calls.last.request.content)
    assert body["schema"] == "landings"
    assert body["action_type"] == "http"
    assert body["type"] == "default"
    assert body["offers"] == [{"offer_id": 42, "share": 100}]


@respx.mock
async def test_create_offer_returns_id_and_sends_expected_payload(client: KeitaroClient) -> None:
    route = respx.post(f"{API}/offers").mock(return_value=httpx.Response(200, json={"id": 321}))
    offer_id = await client.create_offer(
        name="My offer", action_type="http", action_payload="https://example.com/offer"
    )
    assert offer_id == 321
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "My offer"
    assert body["action_type"] == "http"
    assert body["action_payload"] == "https://example.com/offer"


@respx.mock
async def test_get_offer_parses_response(client: KeitaroClient) -> None:
    respx.get(f"{API}/offers/42").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 42,
                "name": "My offer",
                "action_type": "http",
                "action_payload": "https://example.com",
                "state": "active",
            },
        )
    )
    offer = await client.get_offer(42)
    assert offer.id == 42
    assert offer.name == "My offer"
    assert offer.action_type == "http"


@respx.mock
async def test_list_offers_returns_all(client: KeitaroClient) -> None:
    respx.get(f"{API}/offers").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 1, "name": "Offer 1", "action_type": "http", "action_payload": "u1"},
                {"id": 2, "name": "Offer 2", "action_type": "http", "action_payload": "u2"},
            ],
        )
    )
    offers = await client.list_offers()
    assert [o.id for o in offers] == [1, 2]


@respx.mock
async def test_list_groups_requests_campaign_type(client: KeitaroClient) -> None:
    route = respx.get(f"{API}/groups", params={"type": "campaigns"}).mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Group A"}])
    )
    groups = await client.list_groups()
    assert groups[0].name == "Group A"
    assert route.calls.last.request.url.params["type"] == "campaigns"
