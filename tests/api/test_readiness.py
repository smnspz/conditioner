import sqlite3
from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from conditioner.api.dependencies import (
    get_access_token_service,
    get_current_user_id,
    get_metrics_repository,
    get_questionnaire_repository,
    get_readiness_repository,
)
from conditioner.api.main import app
from conditioner.core.adapters.persistence.sqlite.metrics_repository import (
    SqliteMetricsRepository,
)
from conditioner.core.adapters.persistence.sqlite.questionnaire_repository import (
    SqliteQuestionnaireRepository,
)
from conditioner.core.adapters.persistence.sqlite.readiness_repository import (
    SqliteReadinessRepository,
)
from conditioner.core.domain.questionnaire import QuestionnaireResponse
from conditioner.core.domain.wearable_metrics import WearableDailyMetrics
from conditioner.core.services.access_tokens import AccessTokenService
from conditioner.core.services.jwt_tokens import JwtSigner

_JWT_SIGNER = JwtSigner("test-secret")
_USER_ID = "user-123"
_DAY = date(2024, 8, 14)


@pytest.fixture
def repos(db_path: str) -> dict[str, object]:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (id, email, created_at) VALUES (?, ?, ?)",
        (_USER_ID, "athlete@example.com", "2024-08-14T00:00:00"),
    )
    conn.commit()
    conn.close()

    return {
        "metrics": SqliteMetricsRepository(db_path),
        "questionnaire": SqliteQuestionnaireRepository(db_path),
        "readiness": SqliteReadinessRepository(db_path),
    }


@pytest.fixture
def client(repos: dict[str, object]) -> Iterator[TestClient]:
    token_service = AccessTokenService(_JWT_SIGNER)
    app.dependency_overrides[get_metrics_repository] = lambda: repos["metrics"]
    app.dependency_overrides[get_questionnaire_repository] = lambda: repos["questionnaire"]
    app.dependency_overrides[get_readiness_repository] = lambda: repos["readiness"]
    app.dependency_overrides[get_access_token_service] = lambda: token_service
    # Bypass JWT verification — return a fixed user ID for all requests
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_get_readiness_returns_404_without_data(client: TestClient) -> None:
    response = client.get(f"/readiness/{_DAY}")

    assert response.status_code == 404


async def test_get_readiness_computes_and_caches_score(
    client: TestClient, repos: dict[str, object]
) -> None:
    await repos["metrics"].save(
        WearableDailyMetrics(
            user_id=_USER_ID,
            date=_DAY,
            hrv_rmssd=60.0,
            resting_heart_rate=50.0,
            sleep_duration_hours=8.0,
            sleep_efficiency_pct=92.0,
        )
    )
    await repos["questionnaire"].save(
        QuestionnaireResponse(
            user_id=_USER_ID, date=_DAY, fatigue=2, soreness=2, stress=2, sleep_quality=8
        )
    )

    response = client.get(f"/readiness/{_DAY}")

    assert response.status_code == 200
    body = response.json()
    assert body["date"] == str(_DAY)
    assert 0 <= body["score"] <= 100
    assert body["zone"] in ("peak", "good", "moderate", "light", "rest")

    # Score is now cached; second call should return the same result
    cached = await repos["readiness"].get_by_date(_USER_ID, _DAY)
    assert cached is not None
    assert cached.score == body["score"]
