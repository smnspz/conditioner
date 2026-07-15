import sqlite3
from collections.abc import Iterator
from datetime import date
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from conditioner.api.dependencies import (
    get_access_token_service,
    get_constraints_repository,
    get_current_user_id,
    get_fitness_level_repository,
    get_readiness_repository,
    get_workout_generation_provider,
    get_workout_repository,
)
from conditioner.api.main import app
from conditioner.core.adapters.persistence.sqlite.constraints_repository import (
    SqliteConstraintsRepository,
)
from conditioner.core.adapters.persistence.sqlite.fitness_level_repository import (
    SqliteFitnessLevelRepository,
)
from conditioner.core.adapters.persistence.sqlite.readiness_repository import (
    SqliteReadinessRepository,
)
from conditioner.core.adapters.persistence.sqlite.workout_repository import (
    SqliteWorkoutRepository,
)
from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.domain.workout.workout import Exercise, ExerciseModality, Session, Workout
from conditioner.core.services.auth.access_tokens import AccessTokenService
from conditioner.core.services.auth.jwt_tokens import JwtSigner

_JWT_SIGNER = JwtSigner("test-secret")
_USER_ID = "user-123"
_WEEK_START = date(2026, 7, 13)


@pytest.fixture
def client(db_path: str) -> Iterator[TestClient]:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (id, email, created_at) VALUES (?, ?, ?)",
        (_USER_ID, "athlete@example.com", "2024-08-14T00:00:00"),
    )
    conn.commit()
    conn.close()

    token_service = AccessTokenService(_JWT_SIGNER)
    app.dependency_overrides[get_constraints_repository] = lambda: SqliteConstraintsRepository(
        db_path
    )
    app.dependency_overrides[get_fitness_level_repository] = lambda: SqliteFitnessLevelRepository(
        db_path
    )
    app.dependency_overrides[get_readiness_repository] = lambda: SqliteReadinessRepository(
        db_path
    )
    app.dependency_overrides[get_workout_repository] = lambda: SqliteWorkoutRepository(db_path)
    app.dependency_overrides[get_access_token_service] = lambda: token_service
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_generate_rejects_when_constraints_missing(client: TestClient) -> None:
    response = client.post(
        f"/workouts/{_WEEK_START}/generate", headers={"Authorization": "Bearer dummy"}
    )

    assert response.status_code == 422


async def test_generate_succeeds_when_prerequisites_set(
    client: TestClient, db_path: str
) -> None:
    await SqliteConstraintsRepository(db_path).save(
        WorkoutConstraints(
            user_id=_USER_ID,
            equipment=["dumbbells"],
            goal=TrainingGoal.MMA_CONDITIONING,
            available_minutes_by_weekday={0: 60},
        )
    )
    await SqliteFitnessLevelRepository(db_path).save(
        FitnessLevel(user_id=_USER_ID, week_start=_WEEK_START, score=6)
    )
    await SqliteReadinessRepository(db_path).save(
        ReadinessScore(user_id=_USER_ID, date=_WEEK_START, score=75, zone=ReadinessZone.GOOD)
    )
    provider = AsyncMock()
    provider.generate_weekly_plan = AsyncMock(
        return_value=Workout(id="workout-1", user_id=_USER_ID, week_start=_WEEK_START)
    )
    app.dependency_overrides[get_workout_generation_provider] = lambda: provider

    response = client.post(
        f"/workouts/{_WEEK_START}/generate", headers={"Authorization": "Bearer dummy"}
    )

    assert response.status_code == 200
    assert response.json()["id"] == "workout-1"


def test_get_by_week_returns_404_when_missing(client: TestClient) -> None:
    response = client.get(f"/workouts/{_WEEK_START}", headers={"Authorization": "Bearer dummy"})

    assert response.status_code == 404


def test_adjust_rejects_when_readiness_missing(client: TestClient) -> None:
    response = client.post(
        f"/workouts/{_WEEK_START}/adjust", headers={"Authorization": "Bearer dummy"}
    )

    assert response.status_code == 422


async def test_adjust_scales_remaining_sessions(client: TestClient, db_path: str) -> None:
    await SqliteReadinessRepository(db_path).save(
        ReadinessScore(
            user_id=_USER_ID, date=_WEEK_START, score=55, zone=ReadinessZone.MODERATE
        )
    )
    await SqliteWorkoutRepository(db_path).save(
        Workout(
            id="workout-1",
            user_id=_USER_ID,
            week_start=_WEEK_START,
            sessions=[
                Session(
                    id="session-1",
                    date=_WEEK_START,
                    exercises=[
                        Exercise(
                            id="exercise-1",
                            name="Back squat",
                            modality=ExerciseModality.STRENGTH,
                            sets=4,
                        )
                    ],
                )
            ],
        )
    )

    response = client.post(
        f"/workouts/{_WEEK_START}/adjust", headers={"Authorization": "Bearer dummy"}
    )

    assert response.status_code == 200
    assert response.json()["sessions"][0]["exercises"][0]["sets"] == 3


def test_regenerate_rejects_when_constraints_missing(client: TestClient) -> None:
    response = client.post(
        f"/workouts/{_WEEK_START}/regenerate", headers={"Authorization": "Bearer dummy"}
    )

    assert response.status_code == 422


async def test_regenerate_succeeds_when_prerequisites_set(
    client: TestClient, db_path: str
) -> None:
    await SqliteConstraintsRepository(db_path).save(
        WorkoutConstraints(
            user_id=_USER_ID,
            equipment=["dumbbells"],
            goal=TrainingGoal.MMA_CONDITIONING,
            available_minutes_by_weekday={0: 30},
        )
    )
    await SqliteFitnessLevelRepository(db_path).save(
        FitnessLevel(user_id=_USER_ID, week_start=_WEEK_START, score=6)
    )
    await SqliteReadinessRepository(db_path).save(
        ReadinessScore(user_id=_USER_ID, date=_WEEK_START, score=75, zone=ReadinessZone.GOOD)
    )
    provider = AsyncMock()
    provider.generate_weekly_plan = AsyncMock(
        return_value=Workout(id="workout-2", user_id=_USER_ID, week_start=_WEEK_START)
    )
    app.dependency_overrides[get_workout_generation_provider] = lambda: provider

    response = client.post(
        f"/workouts/{_WEEK_START}/regenerate", headers={"Authorization": "Bearer dummy"}
    )

    assert response.status_code == 200
    assert response.json()["id"] == "workout-2"
