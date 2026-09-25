"""
Единая обработка ошибок: доменные и Keitaro-исключения превращаются в понятные
JSON-ответы, а не в необработанную 500-ю (NFR-10) — с сохранением статуса,
где это уместно.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from adrobot.application.ports import (
    KeitaroRequestError,
    KeitaroTimeoutError,
    KeitaroUnavailableError,
)
from adrobot.domain.exceptions import (
    CampaignNotFoundError,
    CampaignNotReadyError,
    DomainError,
    OfferNotFoundError,
    OperationNotFoundError,
)
from adrobot.domain.value_objects import EmptyCampaignNameError, InvalidGeoError
from adrobot.infrastructure.db.exception_handler import DatabaseIntegrityError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidGeoError)
    @app.exception_handler(EmptyCampaignNameError)
    async def handle_validation(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": str(exc)}
        )

    @app.exception_handler(OfferNotFoundError)
    async def handle_offer_not_found(request: Request, exc: OfferNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": str(exc)}
        )

    @app.exception_handler(CampaignNotFoundError)
    @app.exception_handler(OperationNotFoundError)
    async def handle_not_found(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(CampaignNotReadyError)
    async def handle_not_ready(request: Request, exc: CampaignNotReadyError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    @app.exception_handler(KeitaroTimeoutError)
    @app.exception_handler(KeitaroUnavailableError)
    async def handle_keitaro_unavailable(request: Request, exc: Exception) -> JSONResponse:
        logger.warning("Keitaro unavailable while handling %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Keitaro временно недоступен, попробуйте позже"},
        )

    @app.exception_handler(KeitaroRequestError)
    async def handle_keitaro_request_error(
        request: Request, exc: KeitaroRequestError
    ) -> JSONResponse:
        # Сообщение KeitaroRequestError безопасно для показа (см. adrobot.application.ports).
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    @app.exception_handler(DatabaseIntegrityError)
    async def handle_integrity_error(request: Request, exc: DatabaseIntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": [
                    {"loc": [exc.field], "type": exc.type, "msg": exc.msg, "input": exc.value}
                ]
            },
        )

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})
