from adrobot.application.groups.sync_groups import SyncGroupsUseCase
from adrobot.application.ports import KeitaroGroupDTO
from tests.application.fakes import FakeKeitaroGateway


async def _search(uow, query: str = "", limit: int = 10):
    async with uow:
        return await uow.groups.search(query, limit)


async def test_sync_upserts_groups_and_marks_removed_ones_deleted(uow) -> None:
    keitaro = FakeKeitaroGateway(
        groups=[KeitaroGroupDTO(id=1, name="Alpha"), KeitaroGroupDTO(id=2, name="Beta")]
    )
    use_case = SyncGroupsUseCase(uow, keitaro)
    await use_case.execute(event_id="evt-1")

    groups = await _search(uow)
    assert {g.name for g in groups} == {"Alpha", "Beta"}

    # Второй синк без "Beta" -> она должна пропасть из результатов поиска.
    keitaro.groups = [KeitaroGroupDTO(id=1, name="Alpha")]
    await use_case.execute(event_id="evt-2")

    groups = await _search(uow)
    assert {g.name for g in groups} == {"Alpha"}


async def test_sync_is_idempotent_for_the_same_event(uow) -> None:
    keitaro = FakeKeitaroGateway(groups=[KeitaroGroupDTO(id=1, name="Alpha")])
    use_case = SyncGroupsUseCase(uow, keitaro)

    await use_case.execute(event_id="evt-1")

    async def fail_if_called():
        raise AssertionError("list_groups must not be called again for a processed event")

    keitaro.list_groups = fail_if_called  # type: ignore[method-assign]

    await use_case.execute(event_id="evt-1")  # не должно упасть


async def test_search_groups_is_case_insensitive_substring(uow) -> None:
    keitaro = FakeKeitaroGateway(groups=[KeitaroGroupDTO(id=1, name="Summer Sale")])
    await SyncGroupsUseCase(uow, keitaro).execute(event_id="evt-1")

    results = await _search(uow, "summer")
    assert len(results) == 1
    assert results[0].name == "Summer Sale"
