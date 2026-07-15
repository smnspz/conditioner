from conditioner.core.adapters.persistence.sqlite.equipment_repository import (
    SqliteEquipmentRepository,
)


async def test_list_all_returns_seeded_catalog(db_path: str) -> None:
    repo = SqliteEquipmentRepository(db_path)

    catalog = await repo.list_all()

    ids = {item.id for item in catalog}
    assert "dumbbells" in ids
    assert "none" in ids
    assert catalog == sorted(catalog, key=lambda item: item.name)


async def test_get_by_ids_returns_only_matches(db_path: str) -> None:
    repo = SqliteEquipmentRepository(db_path)

    result = await repo.get_by_ids(["dumbbells", "kettlebell", "not-a-real-id"])

    assert {item.id for item in result} == {"dumbbells", "kettlebell"}


async def test_get_by_ids_empty_list_returns_empty(db_path: str) -> None:
    repo = SqliteEquipmentRepository(db_path)

    assert await repo.get_by_ids([]) == []
