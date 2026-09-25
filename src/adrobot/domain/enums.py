"""Перечисления статусов и действий предметной области."""

from __future__ import annotations

import enum


class CampaignStatus(enum.StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLBACK_FAILED = "rollback_failed"

    @property
    def is_final(self) -> bool:
        return self in (
            CampaignStatus.SUCCESS,
            CampaignStatus.FAILED,
            CampaignStatus.ROLLBACK_FAILED,
        )


class OperationAction(enum.StrEnum):
    ADD_OFFER = "add_offer"
    REMOVE_OFFER = "remove_offer"


class OperationStatus(enum.StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

    @property
    def is_final(self) -> bool:
        return self in (OperationStatus.SUCCESS, OperationStatus.FAILED)
