"""
In-process pub/sub для SSE. API-процесс потребляет статусные события из Kafka
и передаёт их через hub всем подписчикам конкретной кампании/операции
(docs/SEQUENCE_DIAGRAMS.md#2-создание-кампании, шаги 23-25).

Подписка регистрируется в hub ДО чтения текущего статуса из БД (см. вызывающий
код в presentation/api/routers), поэтому событие, пришедшее в узкий промежуток
между чтением БД и подпиской, не теряется.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class SseHub:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, aggregate_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._subscribers[aggregate_id].add(queue)
        return queue

    async def unsubscribe(self, aggregate_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(aggregate_id)
            if subscribers is None:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(aggregate_id, None)

    async def publish(self, aggregate_id: str, message: dict[str, Any]) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.get(aggregate_id, ()))
        for queue in subscribers:
            queue.put_nowait(message)
