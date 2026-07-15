from datetime import UTC, datetime

from conditioner.core.adapters.persistence.sqlite.constraints_repository import (
    SqliteConstraintsRepository,
)
from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.domain.auth.user import User
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints


async def _seed_user(db_path: str, user_id: str) -> None:
    await SqliteUserRepository(db_path).save(
        User(id=user_id, email=f"{user_id}@example.com", created_at=datetime.now(UTC))
    )


async def test_save_and_get_by_user_id_round_trips(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteConstraintsRepository(db_path)
    constraints = WorkoutConstraints(
        user_id="user-1",
        equipment=["dumbbells", "kettlebell"],
        goal=TrainingGoal.MMA_CONDITIONING,
        available_minutes_by_weekday={0: 60, 2: 45, 4: 30},
    )

    await repo.save(constraints)

    assert await repo.get_by_user_id("user-1") == constraints


async def test_save_upserts_existing_constraints(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteConstraintsRepository(db_path)
    await repo.save(
        WorkoutConstraints(
            user_id="user-1",
            equipment=["dumbbells"],
            goal=TrainingGoal.MMA_CONDITIONING,
            available_minutes_by_weekday={0: 60},
        )
    )

    updated = WorkoutConstraints(
        user_id="user-1",
        equipment=["kettlebell"],
        goal=TrainingGoal.MMA_CONDITIONING,
        available_minutes_by_weekday={1: 30},
    )
    await repo.save(updated)

    assert await repo.get_by_user_id("user-1") == updated


async def test_get_by_user_id_returns_none_when_missing(db_path: str) -> None:
    repo = SqliteConstraintsRepository(db_path)
    assert await repo.get_by_user_id("missing") is None


async def test_initial_perceived_fitness_round_trips(db_path: str) -> None:
    await _seed_user(db_path, "user-2")
    repo = SqliteConstraintsRepository(db_path)
    constraints = WorkoutConstraints(
        user_id="user-2",
        equipment=["dumbbells"],
        goal=TrainingGoal.MMA_CONDITIONING,
        available_minutes_by_weekday={0: 60},
        initial_perceived_fitness=8,
    )

    await repo.save(constraints)

    result = await repo.get_by_user_id("user-2")
    assert result is not None
    assert result.initial_perceived_fitness == 8


async def test_initial_perceived_fitness_defaults_to_none(db_path: str) -> None:
    await _seed_user(db_path, "user-3")
    repo = SqliteConstraintsRepository(db_path)
    constraints = WorkoutConstraints(
        user_id="user-3",
        equipment=[],
        goal=TrainingGoal.MMA_CONDITIONING,
        available_minutes_by_weekday={},
    )

    await repo.save(constraints)

    result = await repo.get_by_user_id("user-3")
    assert result is not None
    assert result.initial_perceived_fitness is None
