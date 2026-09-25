"""Ошибки предметной области, независимые от HTTP и Keitaro."""

from __future__ import annotations


class DomainError(Exception):
    """Базовая ошибка предметной области."""


class OfferNotFoundError(DomainError):
    def __init__(self, offer_id: int) -> None:
        self.offer_id = offer_id
        super().__init__(f"Оффер {offer_id} не найден в Keitaro")


class CampaignNotFoundError(DomainError):
    def __init__(self, campaign_id: object) -> None:
        self.campaign_id = campaign_id
        super().__init__(f"Кампания {campaign_id} не найдена")


class CampaignNotReadyError(DomainError):
    """Кампания ещё не создана в Keitaro (не завершился воркер) — редактировать нельзя."""

    def __init__(self, campaign_id: object, status: str) -> None:
        self.campaign_id = campaign_id
        self.status = status
        super().__init__(f"Кампания {campaign_id} в статусе '{status}', редактирование недоступно")


class OperationNotFoundError(DomainError):
    def __init__(self, operation_id: object) -> None:
        self.operation_id = operation_id
        super().__init__(f"Операция {operation_id} не найдена")
