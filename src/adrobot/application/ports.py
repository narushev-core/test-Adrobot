"""
Порт (в терминах гексагональной архитектуры) для доступа к Keitaro.

Application-слой знает только этот протокол. Конкретная реализация —
`adrobot.infrastructure.keitaro.client.KeitaroClient` — работает по HTTP
и ничего не знает про use cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class KeitaroError(Exception):
    """Базовая ошибка интеграции с Keitaro. Сообщение безопасно для показа пользователю."""


class KeitaroTimeoutError(KeitaroError):
    """Keitaro не ответил за отведённое время — временная ошибка, стоит повторить."""


class KeitaroUnavailableError(KeitaroError):
    """Keitaro недоступен или вернул 5xx — временная ошибка, стоит повторить."""


class KeitaroRequestError(KeitaroError):
    """Keitaro вернул 4xx: некорректный запрос или несуществующая сущность. Повтор не поможет."""

    def __init__(self, message: str, *, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class OfferStreamState:
    """Текущее состояние потока с офферами, прочитанное напрямую из Keitaro."""

    stream_id: int
    offer_ids: list[int]
    shares: dict[int, int]


@dataclass(frozen=True, slots=True)
class KeitaroGroupDTO:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class OfferDTO:
    """Оффер Keitaro (`Offer` в openapi.json)."""

    id: int
    name: str
    action_type: str | None
    action_payload: str | dict | None
    state: str | None


class KeitaroGateway(Protocol):
    """Всё, что application-слою нужно от Keitaro Admin API."""

    async def offer_exists(self, offer_id: int) -> bool: ...

    async def create_offer(
        self, *, name: str, action_type: str, action_payload: str, group_id: int | None = None
    ) -> int: ...

    async def get_offer(self, offer_id: int) -> OfferDTO: ...

    async def list_offers(self) -> list[OfferDTO]: ...

    async def find_campaign_by_alias(self, alias: str) -> int | None: ...

    async def create_campaign(
        self,
        *,
        name: str,
        alias: str,
        domain_id: int,
        traffic_source_id: int,
        group_id: int | None,
    ) -> int: ...

    async def delete_campaign(self, keitaro_campaign_id: int) -> None: ...

    async def create_geo_redirect_stream(self, *, keitaro_campaign_id: int, geo: str) -> int: ...

    async def create_offer_stream(self, *, keitaro_campaign_id: int, offer_id: int) -> int: ...

    async def delete_stream(self, stream_id: int) -> None: ...

    async def get_offer_stream_state(self, stream_id: int) -> OfferStreamState: ...

    async def update_offer_stream(
        self, stream_id: int, offer_ids: list[int], shares: dict[int, int]
    ) -> None: ...

    async def list_groups(self) -> list[KeitaroGroupDTO]: ...
