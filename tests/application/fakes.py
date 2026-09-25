"""Фейковая реализация KeitaroGateway для тестов application-слоя (NFR-12: мок Keitaro API)."""

from __future__ import annotations

from dataclasses import dataclass, field

from adrobot.application.ports import (
    KeitaroGroupDTO,
    KeitaroRequestError,
    KeitaroUnavailableError,
    OfferDTO,
    OfferStreamState,
)


@dataclass
class FakeKeitaroGateway:
    existing_offer_ids: set[int] = field(default_factory=set)
    offers: dict[int, OfferDTO] = field(default_factory=dict)
    campaigns_by_alias: dict[str, int] = field(default_factory=dict)
    streams: dict[int, OfferStreamState] = field(default_factory=dict)
    groups: list[KeitaroGroupDTO] = field(default_factory=list)

    fail_create_campaign: Exception | None = None
    fail_create_geo_stream: Exception | None = None
    fail_create_offer_stream: Exception | None = None
    fail_update_offer_stream: Exception | None = None

    deleted_campaigns: list[int] = field(default_factory=list)
    deleted_streams: list[int] = field(default_factory=list)
    create_campaign_calls: int = 0

    _next_id: int = 1000

    def _allocate_id(self) -> int:
        self._next_id += 1
        return self._next_id

    async def offer_exists(self, offer_id: int) -> bool:
        return offer_id in self.existing_offer_ids or offer_id in self.offers

    async def create_offer(
        self, *, name: str, action_type: str, action_payload: str, group_id: int | None = None
    ) -> int:
        offer_id = self._allocate_id()
        self.offers[offer_id] = OfferDTO(
            id=offer_id,
            name=name,
            action_type=action_type,
            action_payload=action_payload,
            state="active",
        )
        self.existing_offer_ids.add(offer_id)
        return offer_id

    async def get_offer(self, offer_id: int) -> OfferDTO:
        if offer_id not in self.offers:
            raise KeitaroRequestError(f"Offer {offer_id} not found", status_code=404)
        return self.offers[offer_id]

    async def list_offers(self) -> list[OfferDTO]:
        return list(self.offers.values())

    async def find_campaign_by_alias(self, alias: str) -> int | None:
        return self.campaigns_by_alias.get(alias)

    async def create_campaign(
        self,
        *,
        name: str,
        alias: str,
        domain_id: int,
        traffic_source_id: int,
        group_id: int | None,
    ) -> int:
        self.create_campaign_calls += 1
        if self.fail_create_campaign is not None:
            raise self.fail_create_campaign
        keitaro_id = self._allocate_id()
        self.campaigns_by_alias[alias] = keitaro_id
        return keitaro_id

    async def delete_campaign(self, keitaro_campaign_id: int) -> None:
        self.deleted_campaigns.append(keitaro_campaign_id)

    async def create_geo_redirect_stream(self, *, keitaro_campaign_id: int, geo: str) -> int:
        if self.fail_create_geo_stream is not None:
            raise self.fail_create_geo_stream
        return self._allocate_id()

    async def create_offer_stream(self, *, keitaro_campaign_id: int, offer_id: int) -> int:
        if self.fail_create_offer_stream is not None:
            raise self.fail_create_offer_stream
        stream_id = self._allocate_id()
        self.streams[stream_id] = OfferStreamState(
            stream_id=stream_id, offer_ids=[offer_id], shares={offer_id: 100}
        )
        return stream_id

    async def delete_stream(self, stream_id: int) -> None:
        self.deleted_streams.append(stream_id)

    async def get_offer_stream_state(self, stream_id: int) -> OfferStreamState:
        return self.streams[stream_id]

    async def update_offer_stream(
        self, stream_id: int, offer_ids: list[int], shares: dict[int, int]
    ) -> None:
        if self.fail_update_offer_stream is not None:
            raise self.fail_update_offer_stream
        self.streams[stream_id] = OfferStreamState(
            stream_id=stream_id, offer_ids=offer_ids, shares=shares
        )

    async def list_groups(self) -> list[KeitaroGroupDTO]:
        return self.groups


__all__ = [
    "FakeKeitaroGateway",
    "KeitaroRequestError",
    "KeitaroUnavailableError",
]
