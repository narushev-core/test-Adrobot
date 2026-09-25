from __future__ import annotations

from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any

from sqlalchemy.exc import IntegrityError

from adrobot.infrastructure.db.exception_handler import integrity_error_handler


def sqlalchemy_error_handler(
    func: Callable[..., Coroutine[Any, Any, Any]],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    @wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await func(self, *args, **kwargs)
        except IntegrityError as exc:
            await self.session.rollback()
            raise integrity_error_handler(exc) from exc

    return wrapper
