from datetime import UTC, date, datetime

from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.adapters.persistence.sqlite.workout_repository import (
    SqliteWorkoutRepository,
)
from conditioner.core.domain.user import User
from conditioner.core.domain.workout import Exercise, ExerciseModality, Session, Workout


async def _seed_user(db_path: str, user_id: str) -> None:
    await SqliteUserRepository(db_path).save(
        User(id=user_id, email=f"{user_id}@example.com", created_at=datetime.now(UTC))
    )


def _sample_workout(workout_id: str = "workout-1") -> Workout:
    return Workout(
        id=workout_id,
        user_id="user-1",
        week_start=date(2026, 1, 5),
        sessions=[
            Session(
                id="session-1",
                date=date(2026, 1, 5),
                exercises=[
                    Exercise(
                        id="exercise-1",
                        name="Back squat",
                        modality=ExerciseModality.STRENGTH,
                        sets=5,
                        reps=5,
                        target_load=80.0,
                    ),
                    Exercise(
                        id="exercise-2",
                        name="Easy run",
                        modality=ExerciseModality.CARDIO,
                        duration_minutes=30.0,
                    ),
                ],
            )
        ],
    )


async def test_save_and_get_by_id_round_trips(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteWorkoutRepository(db_path)
    workout = _sample_workout()

    await repo.save(workout)

    assert await repo.get_by_id("workout-1") == workout


async def test_get_by_week_finds_saved_workout(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteWorkoutRepository(db_path)
    workout = _sample_workout()

    await repo.save(workout)

    assert await repo.get_by_week("user-1", date(2026, 1, 5)) == workout
    assert await repo.get_by_week("user-1", date(2026, 1, 12)) is None


async def test_save_replaces_sessions_and_exercises(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteWorkoutRepository(db_path)
    await repo.save(_sample_workout())

    replaced = Workout(
        id="workout-1",
        user_id="user-1",
        week_start=date(2026, 1, 5),
        sessions=[
            Session(
                id="session-2",
                date=date(2026, 1, 6),
                exercises=[
                    Exercise(id="exercise-3", name="Deadlift", modality=ExerciseModality.STRENGTH)
                ],
            )
        ],
    )
    await repo.save(replaced)

    assert await repo.get_by_id("workout-1") == replaced


async def test_get_by_id_returns_none_when_missing(db_path: str) -> None:
    repo = SqliteWorkoutRepository(db_path)
    assert await repo.get_by_id("missing") is None
