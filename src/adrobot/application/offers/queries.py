"""Чтение офферов из Keitaro (список — для выбора в форме создания кампании)."""

from __future__ import annotations

from adrobot.application.ports import KeitaroGateway, OfferDTO


class GetOfferUseCase:
    def __init__(self, keitaro: KeitaroGateway) -> None:
        self._keitaro = keitaro

    async def execute(self, offer_id: int) -> OfferDTO:
        return await self._keitaro.get_offer(offer_id)


class ListOffersUseCase:
    def __init__(self, keitaro: KeitaroGateway) -> None:
        self._keitaro = keitaro

    async def execute(self) -> list[OfferDTO]:
        return await self._keitaro.list_offers()
