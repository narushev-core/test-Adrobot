"""
Создание оффера в Keitaro напрямую из сервиса (без outbox — это не часть
асинхронного сценария создания кампании, а самостоятельная админ-операция).
"""

from __future__ import annotations

from dataclasses import dataclass

from adrobot.application.ports import KeitaroGateway, OfferDTO


@dataclass(frozen=True, slots=True)
class CreateOfferCommand:
    name: str
    redirect_url: str
    group_id: int | None = None


class CreateOfferUseCase:
    def __init__(self, keitaro: KeitaroGateway) -> None:
        self._keitaro = keitaro

    async def execute(self, command: CreateOfferCommand) -> OfferDTO:
        offer_id = await self._keitaro.create_offer(
            name=command.name,
            action_type="http",
            action_payload=command.redirect_url,
            group_id=command.group_id,
        )
        return await self._keitaro.get_offer(offer_id)
