from fastapi.testclient import TestClient


def test_create_offer_returns_201_with_offer_details(client: TestClient, keitaro) -> None:
    response = client.post(
        "/api/offers",
        json={"name": "My offer", "redirect_url": "https://example.com/offer"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "My offer"
    assert body["action_type"] == "http"
    assert body["action_payload"] == "https://example.com/offer"
    assert "id" in body


def test_get_offer_returns_details(client: TestClient, keitaro) -> None:
    create_response = client.post(
        "/api/offers", json={"name": "My offer", "redirect_url": "https://example.com"}
    )
    offer_id = create_response.json()["id"]

    response = client.get(f"/api/offers/{offer_id}")

    assert response.status_code == 200
    assert response.json()["id"] == offer_id


def test_get_unknown_offer_returns_404(client: TestClient, keitaro) -> None:
    response = client.get("/api/offers/999999")
    assert response.status_code == 404


def test_list_offers_is_paginated(client: TestClient, keitaro) -> None:
    client.post("/api/offers", json={"name": "Offer 1", "redirect_url": "https://example.com/1"})
    client.post("/api/offers", json={"name": "Offer 2", "redirect_url": "https://example.com/2"})

    response = client.get("/api/offers")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_create_offer_rejects_empty_name(client: TestClient, keitaro) -> None:
    response = client.post("/api/offers", json={"name": "", "redirect_url": "https://example.com"})
    assert response.status_code == 422
