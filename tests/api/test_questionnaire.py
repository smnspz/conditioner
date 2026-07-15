import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from conditioner.api.dependencies import (
    get_access_token_service,
    get_current_user_id,
    get_questionnaire_repository,
)
from conditioner.api.main import app
from conditioner.core.adapters.persistence.sqlite.questionnaire_repository import (
    SqliteQuestionnaireRepository,
)
from conditioner.core.services.auth.access_tokens import AccessTokenService
from conditioner.core.services.auth.jwt_tokens import JwtSigner

_JWT_SIGNER = JwtSigner("test-secret")
_USER_ID = "user-123"


@pytest.fixture
def client(db_path: str) -> Iterator[TestClient]:
    # Seed the test user so FK constraints on questionnaire_responses are satisfied
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (id, email, created_at) VALUES (?, ?, ?)",
        (_USER_ID, "athlete@example.com", "2024-08-14T00:00:00"),
    )
    conn.commit()
    conn.close()

    repo = SqliteQuestionnaireRepository(db_path)
    token_service = AccessTokenService(_JWT_SIGNER)
    app.dependency_overrides[get_questionnaire_repository] = lambda: repo
    app.dependency_overrides[get_access_token_service] = lambda: token_service
    # Bypass JWT verification — return a fixed user ID for all requests
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_submit_questionnaire_stores_and_returns_response(client: TestClient) -> None:
    response = client.post(
        "/questionnaire",
        json={"date": "2024-08-14", "fatigue": 3, "soreness": 2, "stress": 5, "sleep_quality": 7},
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["date"] == "2024-08-14"
    assert body["fatigue"] == 3
    assert body["soreness"] == 2
    assert body["stress"] == 5
    assert body["sleep_quality"] == 7
    assert body["is_sick"] is False


def test_submit_with_sick_flag(client: TestClient) -> None:
    response = client.post(
        "/questionnaire",
        json={
            "date": "2024-08-14", "fatigue": 8, "soreness": 6,
            "stress": 4, "sleep_quality": 3, "is_sick": True,
        },
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.status_code == 201
    assert response.json()["is_sick"] is True


def test_submit_rejects_score_out_of_range(client: TestClient) -> None:
    response = client.post(
        "/questionnaire",
        json={"date": "2024-08-14", "fatigue": 11, "soreness": 2, "stress": 5, "sleep_quality": 7},
        headers={"Authorization": "Bearer dummy"},
    )

    assert response.status_code == 422


def test_get_questionnaire_returns_saved_response(client: TestClient) -> None:
    client.post(
        "/questionnaire",
        json={"date": "2024-08-14", "fatigue": 3, "soreness": 2, "stress": 5, "sleep_quality": 7},
        headers={"Authorization": "Bearer dummy"},
    )

    response = client.get("/questionnaire/2024-08-14", headers={"Authorization": "Bearer dummy"})

    assert response.status_code == 200
    assert response.json()["fatigue"] == 3


def test_get_questionnaire_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/questionnaire/2024-08-14", headers={"Authorization": "Bearer dummy"})

    assert response.status_code == 404


def test_submit_overwrites_existing_response(client: TestClient) -> None:
    client.post(
        "/questionnaire",
        json={"date": "2024-08-14", "fatigue": 3, "soreness": 2, "stress": 5, "sleep_quality": 7},
        headers={"Authorization": "Bearer dummy"},
    )
    client.post(
        "/questionnaire",
        json={"date": "2024-08-14", "fatigue": 9, "soreness": 8, "stress": 7, "sleep_quality": 2},
        headers={"Authorization": "Bearer dummy"},
    )

    response = client.get("/questionnaire/2024-08-14", headers={"Authorization": "Bearer dummy"})

    assert response.json()["fatigue"] == 9
