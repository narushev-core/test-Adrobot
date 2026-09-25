"""Pydantic-схемы запросов и ответов API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateCampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    geo: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    offer_id: int = Field(gt=0)
    group_id: int | None = Field(default=None, gt=0)


class CreateCampaignResponse(BaseModel):
    id: UUID
    alias: str
    status: str


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alias: str
    name: str
    geo: str
    offer_id: int
    group_id: int | None
    status: str
    keitaro_id: int | None
    geo_stream_id: int | None
    offer_stream_id: int | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class OfferShareResponse(BaseModel):
    offer_id: int
    share: int


class OfferStreamResponse(BaseModel):
    stream_id: int
    offers: list[OfferShareResponse]


class AddOfferRequest(BaseModel):
    offer_id: int = Field(gt=0)


class OperationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    action: str
    offer_id: int
    status: str
    before: list[int] | None
    after: list[int] | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CreateOfferRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    redirect_url: str = Field(min_length=1, max_length=2048, description="URL редиректа оффера")
    group_id: int | None = Field(default=None, gt=0)


class OfferResponse(BaseModel):
    id: int
    name: str
    action_type: str | None
    action_payload: str | dict | None
    state: str | None


class ErrorResponse(BaseModel):
    detail: str
