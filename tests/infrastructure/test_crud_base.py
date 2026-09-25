from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from adrobot.infrastructure.db.base import camel_case_to_snake_case
from adrobot.infrastructure.db.crud.base import CRUDBase
from adrobot.infrastructure.db.crud.group_crud import GroupCRUD, GroupFilter
from adrobot.infrastructure.db.models import KeitaroGroupORM


@pytest.mark.parametrize(
    ("name", "expected"),
    [("KeitaroGroup", "keitaro_group"), ("SDKDemo", "sdk_demo"), ("RServoDrive", "r_servo_drive")],
)
def test_camel_case_to_snake_case(name: str, expected: str) -> None:
    assert camel_case_to_snake_case(name) == expected


async def test_crud_create_read_update_delete(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC)
    async with session_factory() as session:
        crud = CRUDBase(KeitaroGroupORM, session)
        await crud.create(id=1, name="alpha", is_deleted=False, synced_at=now)

        updated = await crud.update(1, name="beta")
        assert updated.name == "beta"

        await crud.delete(1)
        assert await crud.read(1) is None

        with pytest.raises(HTTPException):
            await crud.delete(1)


async def test_group_crud_list_hides_deleted(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC)
    async with session_factory() as session:
        crud = GroupCRUD(KeitaroGroupORM, session)
        await crud.create(id=1, name="alive", is_deleted=False, synced_at=now)
        await crud.create(id=2, name="gone", is_deleted=True, synced_at=now)

        rows = await crud.list(GroupFilter(order_by=["name"]), paginate_response=False)

    assert [g.name for g in rows] == ["alive"]
