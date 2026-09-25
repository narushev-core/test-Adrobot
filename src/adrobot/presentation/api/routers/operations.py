"""Роутер операций редактора: статус изменения оффера и его SSE-поток."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from adrobot.domain.exceptions import OperationNotFoundError
from adrobot.infrastructure.db.crud.operation_crud import OperationCRUD
from adrobot.infrastructure.db.models import OperationORM
from adrobot.presentation.api.deps import HubDep, OperationCRUDDep
from adrobot.presentation.api.schemas import OperationResponse
from adrobot.presentation.api.sse import stream_status_events

router = APIRouter(tags=["operations"])


async def _get_operation_or_404(crud: OperationCRUD, operation_id: UUID) -> OperationORM:
    operation = await crud.read(operation_id)
    if operation is None:
        raise OperationNotFoundError(operation_id)
    return operation


@router.get("/operations/{operation_id}", response_model=OperationResponse)
async def get_operation(operation_id: UUID, crud: OperationCRUDDep) -> OperationResponse:
    operation = await _get_operation_or_404(crud, operation_id)
    return OperationResponse.model_validate(operation)


@router.get("/operations/{operation_id}/events")
async def operation_events(
    operation_id: UUID, crud: OperationCRUDDep, hub: HubDep
) -> EventSourceResponse:
    await _get_operation_or_404(crud, operation_id)

    async def load_current() -> dict:
        operation = await _get_operation_or_404(crud, operation_id)
        return {"status": operation.status, "error": operation.error}

    return await stream_status_events(
        hub,
        str(operation_id),
        load_current,
        is_final=lambda msg: msg["status"] in {"success", "failed"},
    )
