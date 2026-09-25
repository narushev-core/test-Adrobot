"""
Общая механика Server-Sent Events для статусов кампании/операции (sse-starlette).

Подписка на hub регистрируется ДО чтения текущего состояния из БД — если
финальное событие придёт в этот узкий промежуток, оно уже будет в очереди
подписчика и не потеряется (docs/SEQUENCE_DIAGRAMS.md#2, шаги 1-6).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from sse_starlette.sse import EventSourceResponse


async def stream_status_events(
    hub: Any,
    aggregate_id: str,
    load_current: Callable[[], Awaitable[dict[str, Any]]],
    is_final: Callable[[dict[str, Any]], bool],
) -> EventSourceResponse:
    queue = await hub.subscribe(aggregate_id)

    async def generator() -> AsyncIterator[dict[str, str]]:
        try:
            current = await load_current()
            yield {"data": json.dumps(current)}
            if is_final(current):
                return
            while True:
                message = await queue.get()
                yield {"data": json.dumps(message)}
                if is_final(message):
                    return
        except asyncio.CancelledError:
            raise
        finally:
            await hub.unsubscribe(aggregate_id, queue)

    return EventSourceResponse(generator())
