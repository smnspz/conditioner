from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from conditioner.api.main import app


@pytest.fixture
def client(db_path: str) -> Iterator[TestClient]:
    from conditioner.api.dependencies import get_equipment_repository
    from conditioner.core.adapters.persistence.sqlite.equipment_repository import (
        SqliteEquipmentRepository,
    )

    app.dependency_overrides[get_equipment_repository] = lambda: SqliteEquipmentRepository(
        db_path
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_list_equipment_returns_seeded_catalog(client: TestClient) -> None:
    response = client.get("/equipment")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert "dumbbells" in ids
    assert "kettlebell" in ids
