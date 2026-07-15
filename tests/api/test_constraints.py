import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from conditioner.api.dependencies import (
    get_access_token_service,
    get_constraints_repository,
    get_current_user_id,
)
from conditioner.api.main import app
from conditioner.core.adapters.persistence.sqlite.constraints_repository import (
    SqliteConstraintsRepository,
)
from conditioner.core.services.auth.access_tokens import AccessTokenService
from conditioner.core.services.auth.jwt_tokens import JwtSigner

_JWT_SIGNER = JwtSigner("test-secret")
_USER_ID = "user-123"


@pytest.fixture
def client(db_path: str) -> Iterator[TestClient]:
    # Seed the test user so FK constraints on workout_constraints are satisfied
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (id, email, created_at) VALUES (?, ?, ?)",
        (_USER_ID, "athlete@example.com", "2024-08-14T00:00:00"),
    )
    conn.commit()
    conn.close()

    repo = SqliteConstraintsRepository(db_path)
    token_service = AccessTokenService(_JWT_SIGNER)
    app.dependency_overrides[get_constraints_repository] = lambda: repo
    app.dependency_overrides[get_access_token_service] = lambda: token_service
    # Bypass JWT verification — return a fixed user ID for all requests
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_upsert_constraints_stores_and_returns_them(client: TestClient) -> None:
    response = client.put(
        "/constraints",
        json={
            "equipment": ["dumbbells", "kettlebell"],
            "goal": "mma_conditioning",
            "available_minutes_by_weekday": {"0": 60, "2": 45},
        },
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["equipment"] == ["dumbbells", "kettlebell"]
    assert body["goal"] == "mma_conditioning"
    assert body["available_minutes_by_weekday"] == {"0": 60, "2": 45}


def test_get_constraints_returns_saved_constraints(client: TestClient) -> None:
    client.put(
        "/constraints",
        json={
            "equipment": ["dumbbells"],
            "goal": "mma_conditioning",
            "available_minutes_by_weekday": {"1": 30},
        },
        headers={"Authorization": "Bearer dummy"},
    )

    response = client.get("/constraints", headers={"Authorization": "Bearer dummy"})

    assert response.status_code == 200
    assert response.json()["equipment"] == ["dumbbells"]


def test_get_constraints_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/constraints", headers={"Authorization": "Bearer dummy"})

    assert response.status_code == 404


def test_upsert_overwrites_existing_constraints(client: TestClient) -> None:
    client.put(
        "/constraints",
        json={
            "equipment": ["dumbbells"],
            "goal": "mma_conditioning",
            "available_minutes_by_weekday": {"0": 60},
        },
        headers={"Authorization": "Bearer dummy"},
    )
    client.put(
        "/constraints",
        json={
            "equipment": ["kettlebell"],
            "goal": "mma_conditioning",
            "available_minutes_by_weekday": {"3": 20},
        },
        headers={"Authorization": "Bearer dummy"},
    )

    response = client.get("/constraints", headers={"Authorization": "Bearer dummy"})

    assert response.json()["equipment"] == ["kettlebell"]


def test_upsert_rejects_weekday_out_of_range(client: TestClient) -> None:
    response = client.put(
        "/constraints",
        json={
            "equipment": ["dumbbells"],
            "goal": "mma_conditioning",
            "available_minutes_by_weekday": {"7": 60},
        },
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.status_code == 422
