"""Роутер офферов: создание и получение (проксирует Keitaro Admin API, без своей БД)."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi_pagination import Page, paginate
from fastapi_pagination.utils import disable_installed_extensions_check

from adrobot.application.offers.create_offer import CreateOfferCommand, CreateOfferUseCase
from adrobot.application.offers.queries import GetOfferUseCase, ListOffersUseCase
from adrobot.application.ports import OfferDTO
from adrobot.presentation.api.deps import KeitaroDep
from adrobot.presentation.api.schemas import CreateOfferRequest, OfferResponse

# Офферы — данные из Keitaro, а не из БД, поэтому пагинируем generic-реализацией
# `paginate()` из списка. Предупреждение о доступном SQLAlchemy-расширении здесь
# ожидаемо: кампании и группы по-прежнему пагинируются через apaginate() с БД.
disable_installed_extensions_check()

router = APIRouter(tags=["offers"])


def _to_response(offer: OfferDTO) -> OfferResponse:
    return OfferResponse(
        id=offer.id,
        name=offer.name,
        action_type=offer.action_type,
        action_payload=offer.action_payload,
        state=offer.state,
    )


@router.post("/offers", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(body: CreateOfferRequest, keitaro: KeitaroDep) -> OfferResponse:
    offer = await CreateOfferUseCase(keitaro).execute(
        CreateOfferCommand(name=body.name, redirect_url=body.redirect_url, group_id=body.group_id)
    )
    return _to_response(offer)


@router.get("/offers", response_model=Page[OfferResponse])
async def list_offers(keitaro: KeitaroDep) -> Page[OfferResponse]:
    offers = await ListOffersUseCase(keitaro).execute()
    return paginate([_to_response(o) for o in offers])


@router.get("/offers/{offer_id}", response_model=OfferResponse)
async def get_offer(offer_id: int, keitaro: KeitaroDep) -> OfferResponse:
    offer = await GetOfferUseCase(keitaro).execute(offer_id)
    return _to_response(offer)
