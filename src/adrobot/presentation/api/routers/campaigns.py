"""Роутер кампаний: создание (FR-1..FR-5), просмотр, статус по SSE, офферы редактора."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from fastapi_filter import FilterDepends
from fastapi_pagination import Page
from sse_starlette.sse import EventSourceResponse

from adrobot.application.campaigns.create_campaign import (
    CreateCampaignCommand,
    CreateCampaignUseCase,
)
from adrobot.application.campaigns.queries import GetCampaignOffersUseCase
from adrobot.application.operations.request_operation import (
    RequestOperationCommand,
    RequestOperationUseCase,
)
from adrobot.domain.enums import OperationAction
from adrobot.domain.exceptions import CampaignNotFoundError
from adrobot.infrastructure.db.crud.campaign_crud import CampaignCRUD, CampaignFilter
from adrobot.infrastructure.db.models import CampaignORM
from adrobot.presentation.api.deps import CampaignCRUDDep, HubDep, KeitaroDep, UowDep
from adrobot.presentation.api.schemas import (
    AddOfferRequest,
    CampaignResponse,
    CreateCampaignRequest,
    CreateCampaignResponse,
    OfferShareResponse,
    OfferStreamResponse,
)
from adrobot.presentation.api.sse import stream_status_events

router = APIRouter(tags=["campaigns"])


@router.post(
    "/campaigns", response_model=CreateCampaignResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_campaign(
    body: CreateCampaignRequest, uow: UowDep, keitaro: KeitaroDep
) -> CreateCampaignResponse:
    use_case = CreateCampaignUseCase(uow, keitaro)
    result = await use_case.execute(
        CreateCampaignCommand(
            name=body.name, geo=body.geo, offer_id=body.offer_id, group_id=body.group_id
        )
    )
    return CreateCampaignResponse(
        id=result.campaign_id, alias=result.alias, status=result.status.value
    )


@router.get("/campaigns", response_model=Page[CampaignResponse])
async def list_campaigns(
    crud: CampaignCRUDDep,
    campaign_filter: CampaignFilter = FilterDepends(CampaignFilter),  # noqa: B008
) -> Page[CampaignResponse]:
    return await crud.list(campaign_filter)


async def _get_campaign_or_404(crud: CampaignCRUD, campaign_id: UUID) -> CampaignORM:
    campaign = await crud.read(campaign_id)
    if campaign is None:
        raise CampaignNotFoundError(campaign_id)
    return campaign


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: UUID, crud: CampaignCRUDDep) -> CampaignResponse:
    campaign = await _get_campaign_or_404(crud, campaign_id)
    return CampaignResponse.model_validate(campaign)


@router.get("/campaigns/{campaign_id}/events")
async def campaign_events(
    campaign_id: UUID, crud: CampaignCRUDDep, hub: HubDep
) -> EventSourceResponse:
    # Существование проверяем ДО подписки: несуществующая кампания никогда не
    # опубликует событие, гонки за статус здесь нет, а 404 отдаётся сразу.
    await _get_campaign_or_404(crud, campaign_id)

    async def load_current() -> dict:
        campaign = await _get_campaign_or_404(crud, campaign_id)
        return {"status": campaign.status, "error": campaign.error}

    return await stream_status_events(
        hub,
        str(campaign_id),
        load_current,
        is_final=lambda msg: msg["status"] in {"success", "failed", "rollback_failed"},
    )


@router.get("/campaigns/{campaign_id}/offers", response_model=OfferStreamResponse)
async def get_campaign_offers(
    campaign_id: UUID, uow: UowDep, keitaro: KeitaroDep
) -> OfferStreamResponse:
    state = await GetCampaignOffersUseCase(uow, keitaro).execute(campaign_id)
    return OfferStreamResponse(
        stream_id=state.stream_id,
        offers=[
            OfferShareResponse(offer_id=offer_id, share=state.shares[offer_id])
            for offer_id in state.offer_ids
        ],
    )


@router.post(
    "/campaigns/{campaign_id}/offers",
    status_code=status.HTTP_202_ACCEPTED,
)
async def add_offer(campaign_id: UUID, body: AddOfferRequest, uow: UowDep) -> dict:
    use_case = RequestOperationUseCase(uow)
    result = await use_case.execute(
        RequestOperationCommand(
            campaign_id=campaign_id, action=OperationAction.ADD_OFFER, offer_id=body.offer_id
        )
    )
    return {"operation_id": str(result.operation_id), "status": result.status.value}


@router.delete(
    "/campaigns/{campaign_id}/offers/{offer_id}",
    status_code=status.HTTP_202_ACCEPTED,
)
async def remove_offer(campaign_id: UUID, offer_id: int, uow: UowDep) -> dict:
    use_case = RequestOperationUseCase(uow)
    result = await use_case.execute(
        RequestOperationCommand(
            campaign_id=campaign_id, action=OperationAction.REMOVE_OFFER, offer_id=offer_id
        )
    )
    return {"operation_id": str(result.operation_id), "status": result.status.value}
