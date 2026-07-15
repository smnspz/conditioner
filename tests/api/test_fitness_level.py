import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from conditioner.api.dependencies import (
    get_access_token_service,
    get_current_user_id,
    get_fitness_level_repository,
)
from conditioner.api.main import app
from conditioner.core.adapters.persistence.sqlite.fitness_level_repository import (
    SqliteFitnessLevelRepository,
)
from conditioner.core.services.auth.access_tokens import AccessTokenService
from conditioner.core.services.auth.jwt_tokens import JwtSigner

_JWT_SIGNER = JwtSigner("test-secret")
_USER_ID = "user-123"


@pytest.fixture
def client(db_path: str) -> Iterator[TestClient]:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (id, email, created_at) VALUES (?, ?, ?)",
        (_USER_ID, "athlete@example.com", "2024-08-14T00:00:00"),
    )
    conn.commit()
    conn.close()

    repo = SqliteFitnessLevelRepository(db_path)
    token_service = AccessTokenService(_JWT_SIGNER)
    app.dependency_overrides[get_fitness_level_repository] = lambda: repo
    app.dependency_overrides[get_access_token_service] = lambda: token_service
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_upsert_fitness_level_stores_and_returns_it(client: TestClient) -> None:
    response = client.put(
        "/fitness-level/2026-07-14",
        json={"score": 7},
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 7
    assert body["week_start"] == "2026-07-14"


def test_get_fitness_level_returns_saved_value(client: TestClient) -> None:
    client.put(
        "/fitness-level/2026-07-14",
        json={"score": 5},
        headers={"Authorization": "Bearer dummy"},
    )

    response = client.get(
        "/fitness-level/2026-07-14",
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.status_code == 200
    assert response.json()["score"] == 5


def test_get_fitness_level_returns_404_when_missing(client: TestClient) -> None:
    response = client.get(
        "/fitness-level/2026-07-14",
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.status_code == 404


def test_upsert_overwrites_existing_fitness_level(client: TestClient) -> None:
    client.put(
        "/fitness-level/2026-07-14",
        json={"score": 3},
        headers={"Authorization": "Bearer dummy"},
    )
    client.put(
        "/fitness-level/2026-07-14",
        json={"score": 8},
        headers={"Authorization": "Bearer dummy"},
    )

    response = client.get(
        "/fitness-level/2026-07-14",
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.json()["score"] == 8


def test_upsert_rejects_score_out_of_range(client: TestClient) -> None:
    for bad in [0, 11]:
        response = client.put(
            "/fitness-level/2026-07-14",
            json={"score": bad},
            headers={"Authorization": "Bearer dummy"},
        )
        assert response.status_code == 422
