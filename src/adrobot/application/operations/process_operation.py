"""
Воркер-часть добавления/удаления оффера (шаги 6-14 диаграммы «Добавление и
удаление оффера», docs/SEQUENCE_DIAGRAMS.md#3-добавление-и-удаление-оффера).

Поток читается из Keitaro прямо перед изменением — не используются данные с
фронта, потому что `PUT` перезаписывает список офферов целиком и затёр бы
правки, сделанные параллельно в админке Keitaro. Если оффер уже добавлен или
уже удалён, операция считается успешной без запроса в Keitaro (идемпотентность
при повторной доставке события). Временная ошибка Keitaro не финализирует
операцию и не пишет `processed_events` — событие будет доставлено повторно.
"""

from __future__ import annotations

from uuid import UUID

from adrobot.application.ports import KeitaroGateway, KeitaroRequestError
from adrobot.domain.enums import OperationAction, OperationStatus
from adrobot.domain.events import OperationStatusChanged
from adrobot.domain.exceptions import CampaignNotFoundError, OperationNotFoundError
from adrobot.domain.models import Campaign, Operation
from adrobot.domain.repositories import UnitOfWork
from adrobot.domain.value_objects import distribute_offer_shares


class ProcessOperationUseCase:
    HANDLER_NAME = "operation.process"

    def __init__(self, uow: UnitOfWork, keitaro: KeitaroGateway) -> None:
        self._uow = uow
        self._keitaro = keitaro

    async def handle(self, operation_id: UUID, *, event_id: str) -> None:
        operation, campaign = await self._start_or_skip(operation_id, event_id)
        if operation is None:
            return
        if campaign is None or campaign.offer_stream_id is None:
            raise CampaignNotFoundError(operation.campaign_id)

        try:
            before, after = await self._apply(operation, campaign)
        except KeitaroRequestError as exc:
            # Постоянная ошибка (некорректные данные) — повтор не поможет, фиксируем как final.
            operation.status = OperationStatus.FAILED
            operation.error = str(exc)
            await self._finalize(operation, event_id)
            return

        operation.before = before
        operation.after = after
        operation.status = OperationStatus.SUCCESS
        operation.error = None
        await self._finalize(operation, event_id)

    async def _apply(self, operation: Operation, campaign: Campaign) -> tuple[list[int], list[int]]:
        assert campaign.offer_stream_id is not None
        state = await self._keitaro.get_offer_stream_state(campaign.offer_stream_id)
        before = list(state.offer_ids)

        if operation.action is OperationAction.ADD_OFFER:
            if operation.offer_id in before:
                return before, before  # уже добавлен — идемпотентный успех без вызова Keitaro
            after = [*before, operation.offer_id]
        else:
            if operation.offer_id not in before:
                return before, before  # уже удалён — идемпотентный успех без вызова Keitaro
            after = [offer_id for offer_id in before if offer_id != operation.offer_id]

        shares = distribute_offer_shares(after)
        await self._keitaro.update_offer_stream(campaign.offer_stream_id, after, shares)
        return before, after

    async def _start_or_skip(
        self, operation_id: UUID, event_id: str
    ) -> tuple[Operation | None, Campaign | None]:
        async with self._uow:
            if await self._uow.inbox.is_processed(event_id, self.HANDLER_NAME):
                return None, None

            operation = await self._uow.operations.get(operation_id)
            if operation is None:
                raise OperationNotFoundError(operation_id)

            if operation.status.is_final:
                await self._uow.inbox.mark_processed(event_id, self.HANDLER_NAME)
                await self._uow.commit()
                return None, None

            campaign = await self._uow.campaigns.get(operation.campaign_id)
            return operation, campaign

    async def _finalize(self, operation: Operation, event_id: str) -> None:
        async with self._uow:
            await self._uow.operations.update(operation)
            await self._uow.outbox.add(
                OperationStatusChanged(
                    operation_id=operation.id,
                    campaign_id=operation.campaign_id,
                    status=operation.status.value,
                    error=operation.error,
                )
            )
            await self._uow.inbox.mark_processed(event_id, self.HANDLER_NAME)
            await self._uow.commit()
