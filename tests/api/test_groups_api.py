from fastapi.testclient import TestClient

from adrobot.application.groups.sync_groups import SyncGroupsUseCase
from adrobot.application.ports import KeitaroGroupDTO
from adrobot.infrastructure.db.uow import SqlAlchemyUnitOfWork


async def test_search_groups_returns_only_matching_non_deleted(
    client: TestClient, session_factory, keitaro
) -> None:
    keitaro.groups = [
        KeitaroGroupDTO(id=1, name="Summer Sale"),
        KeitaroGroupDTO(id=2, name="Winter"),
    ]
    uow = SqlAlchemyUnitOfWork(session_factory)
    await SyncGroupsUseCase(uow, keitaro).execute(event_id="evt-1")

    response = client.get("/api/groups/search", params={"search": "summer"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "Summer Sale"


def test_sync_groups_returns_202(client: TestClient) -> None:
    response = client.post("/api/groups/sync")
    assert response.status_code == 202
    assert response.json()["status"] == "requested"
