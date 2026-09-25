"""
HTTP-клиент Keitaro Admin API.

Поля и пути сверены с реальной OpenAPI-спецификацией трекера (openapi.json,
поставлена вместе с проектом), а не подобраны по общим конвенциям — в
частности:

- `alias` — нативное поле кампании (используется в URL кампании), отдельно
  генерировать его в название не нужно;
- `traffic_source_id` и `domain_id` — поля кампании, а не потока;
- доля оффера в потоке передаётся как `share`, а не `value`;
- фильтр потока — это `{"name", "mode": "accept"|"reject", "payload": [...]}`,
  а не `{"value", "is_negative"}`.

Два момента в спецификации остаются динамическими справочниками, не
зафиксированными статически (`GET /stream_filters`, `GET /streams_actions`),
поэтому строковые идентификаторы `"country"` (фильтр по гео) и `"http"`
(редирект) взяты из документированного примера создания оффера в openapi.json
и общеизвестных обозначений Keitaro — при подключении к реальному инстансу
стоит свериться с этими двумя справочниками.

Все запросы идут с таймаутом (NFR-11), ошибки маппятся в типизированные
исключения из `adrobot.application.ports` (NFR-10), а сами запросы и ошибки
логируются без API-ключа (NFR-13) — ключ передаётся только в заголовке и
никогда не подставляется в текст лога.
"""

from __future__ import annotations

import logging

import httpx

from adrobot.application.ports import (
    KeitaroGroupDTO,
    KeitaroRequestError,
    KeitaroTimeoutError,
    KeitaroUnavailableError,
    OfferDTO,
    OfferStreamState,
)

logger = logging.getLogger(__name__)

# Каждая доступная стране должна прийти как ISO alpha-2 в payload фильтра.
_COUNTRY_FILTER_NAME = "country"
_REDIRECT_ACTION_TYPE = "http"

# Сколько кампаний просматривать за один проход при поиске по alias
# (GET /campaigns не поддерживает фильтр — только offset/limit).
_FIND_BY_ALIAS_PAGE_SIZE = 200
_FIND_BY_ALIAS_MAX_PAGES = 25


class KeitaroClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/admin_api/v1",
            headers={"Api-Key": api_key},
            timeout=httpx.Timeout(timeout_seconds),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        logger.info("Keitaro request: %s %s", method, path)
        try:
            response = await self._client.request(method, path, **kwargs)  # type: ignore[arg-type]
        except httpx.TimeoutException as exc:
            logger.warning("Keitaro timeout: %s %s", method, path)
            raise KeitaroTimeoutError(f"Keitaro не ответил за отведённое время: {path}") from exc
        except httpx.HTTPError as exc:
            logger.warning("Keitaro unavailable: %s %s (%s)", method, path, exc)
            raise KeitaroUnavailableError(f"Keitaro недоступен: {path}") from exc

        if response.status_code >= 500:
            logger.warning("Keitaro server error: %s %s -> %s", method, path, response.status_code)
            raise KeitaroUnavailableError(f"Keitaro вернул ошибку сервера {response.status_code}")
        if response.status_code >= 400:
            detail = self._safe_error_detail(response)
            logger.info(
                "Keitaro request error: %s %s -> %s: %s",
                method,
                path,
                response.status_code,
                detail,
            )
            raise KeitaroRequestError(detail, status_code=response.status_code)
        return response

    @staticmethod
    def _safe_error_detail(response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return f"Keitaro вернул ошибку {response.status_code}"
        if isinstance(data, dict):
            return str(data.get("message") or data.get("error") or data)
        return str(data)

    # ------------------------------------------------------------------ offers

    async def offer_exists(self, offer_id: int) -> bool:
        try:
            await self._request("GET", f"/offers/{offer_id}")
        except KeitaroRequestError as exc:
            if exc.status_code == 404:
                return False
            raise
        return True

    async def create_offer(
        self, *, name: str, action_type: str, action_payload: str, group_id: int | None = None
    ) -> int:
        payload: dict[str, object] = {
            "name": name,
            "offer_type": "external",
            "action_type": action_type,
            "action_payload": action_payload,
        }
        if group_id is not None:
            payload["group_id"] = group_id
        response = await self._request("POST", "/offers", json=payload)
        return int(response.json()["id"])

    async def get_offer(self, offer_id: int) -> OfferDTO:
        response = await self._request("GET", f"/offers/{offer_id}")
        return self._offer_from_json(response.json())

    async def list_offers(self) -> list[OfferDTO]:
        response = await self._request("GET", "/offers")
        return [self._offer_from_json(row) for row in response.json()]

    @staticmethod
    def _offer_from_json(data: dict) -> OfferDTO:
        return OfferDTO(
            id=int(data["id"]),
            name=str(data["name"]),
            action_type=data.get("action_type"),
            action_payload=data.get("action_payload"),
            state=data.get("state"),
        )

    # --------------------------------------------------------------- campaigns

    async def find_campaign_by_alias(self, alias: str) -> int | None:
        # GET /campaigns не поддерживает фильтр по alias (только offset/limit),
        # поэтому ищем постранично. Кампании поиском не создаются массово,
        # так что ограничение в 25 страниц (5000 кампаний) — разумный потолок.
        offset = 0
        for _ in range(_FIND_BY_ALIAS_MAX_PAGES):
            response = await self._request(
                "GET",
                "/campaigns",
                params={"limit": _FIND_BY_ALIAS_PAGE_SIZE, "offset": offset},
            )
            rows = response.json()
            for row in rows:
                if row.get("alias") == alias:
                    return int(row["id"])
            if len(rows) < _FIND_BY_ALIAS_PAGE_SIZE:
                return None
            offset += _FIND_BY_ALIAS_PAGE_SIZE
        logger.warning("find_campaign_by_alias: страница не найдена за %s страниц", alias)
        return None

    async def create_campaign(
        self,
        *,
        name: str,
        alias: str,
        domain_id: int,
        traffic_source_id: int,
        group_id: int | None,
    ) -> int:
        payload: dict[str, object] = {
            "name": name,
            "alias": alias,
            "domain_id": domain_id,
            "traffic_source_id": traffic_source_id,
            "state": "active",
        }
        if group_id is not None:
            payload["group_id"] = group_id
        response = await self._request("POST", "/campaigns", json=payload)
        return int(response.json()["id"])

    async def delete_campaign(self, keitaro_campaign_id: int) -> None:
        await self._request("DELETE", f"/campaigns/{keitaro_campaign_id}")

    # ----------------------------------------------------------------- streams

    async def create_geo_redirect_stream(self, *, keitaro_campaign_id: int, geo: str) -> int:
        payload = {
            "campaign_id": keitaro_campaign_id,
            "name": "Geo redirect",
            "type": "regular",
            "schema": "redirect",
            "action_type": _REDIRECT_ACTION_TYPE,
            "action_payload": "https://www.google.com",
            "filters": [
                {"name": _COUNTRY_FILTER_NAME, "mode": "accept", "payload": [geo]},
            ],
        }
        response = await self._request("POST", "/streams", json=payload)
        return int(response.json()["id"])

    async def create_offer_stream(self, *, keitaro_campaign_id: int, offer_id: int) -> int:
        payload = {
            "campaign_id": keitaro_campaign_id,
            "name": "Offer",
            "type": "default",
            "schema": "landings",
            "action_type": _REDIRECT_ACTION_TYPE,
            "offers": [{"offer_id": offer_id, "share": 100}],
        }
        response = await self._request("POST", "/streams", json=payload)
        return int(response.json()["id"])

    async def delete_stream(self, stream_id: int) -> None:
        await self._request("DELETE", f"/streams/{stream_id}")

    async def get_offer_stream_state(self, stream_id: int) -> OfferStreamState:
        response = await self._request("GET", f"/streams/{stream_id}")
        data = response.json()
        offers = data.get("offers", [])
        offer_ids = [int(o["offer_id"]) for o in offers]
        shares = {int(o["offer_id"]): int(o["share"]) for o in offers}
        return OfferStreamState(stream_id=stream_id, offer_ids=offer_ids, shares=shares)

    async def update_offer_stream(
        self, stream_id: int, offer_ids: list[int], shares: dict[int, int]
    ) -> None:
        payload = {
            "offers": [{"offer_id": offer_id, "share": shares[offer_id]} for offer_id in offer_ids]
        }
        await self._request("PUT", f"/streams/{stream_id}", json=payload)

    # ------------------------------------------------------------------ groups

    async def list_groups(self) -> list[KeitaroGroupDTO]:
        # GET /groups обязателен параметр type — нам нужны группы кампаний.
        response = await self._request("GET", "/groups", params={"type": "campaigns"})
        return [
            KeitaroGroupDTO(id=int(row["id"]), name=str(row["name"])) for row in response.json()
        ]
