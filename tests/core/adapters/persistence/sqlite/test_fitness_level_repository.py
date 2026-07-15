from datetime import UTC, datetime, date

from conditioner.core.adapters.persistence.sqlite.fitness_level_repository import (
    SqliteFitnessLevelRepository,
)
from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.domain.auth.user import User
from conditioner.core.domain.fitness.fitness_level import FitnessLevel

_WEEK_START = date(2026, 7, 14)


async def _seed_user(db_path: str, user_id: str) -> None:
    await SqliteUserRepository(db_path).save(
        User(id=user_id, email=f"{user_id}@example.com", created_at=datetime.now(UTC))
    )


async def test_save_and_get_by_week_round_trips(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteFitnessLevelRepository(db_path)
    fitness = FitnessLevel(user_id="user-1", week_start=_WEEK_START, score=7)

    await repo.save(fitness)

    assert await repo.get_by_week("user-1", _WEEK_START) == fitness


async def test_save_upserts_existing_fitness_level(db_path: str) -> None:
    await _seed_user(db_path, "user-2")
    repo = SqliteFitnessLevelRepository(db_path)
    await repo.save(FitnessLevel(user_id="user-2", week_start=_WEEK_START, score=5))

    updated = FitnessLevel(user_id="user-2", week_start=_WEEK_START, score=8)
    await repo.save(updated)

    result = await repo.get_by_week("user-2", _WEEK_START)
    assert result is not None
    assert result.score == 8


async def test_get_by_week_returns_none_when_missing(db_path: str) -> None:
    repo = SqliteFitnessLevelRepository(db_path)
    assert await repo.get_by_week("missing", _WEEK_START) is None


async def test_different_weeks_are_stored_independently(db_path: str) -> None:
    await _seed_user(db_path, "user-3")
    repo = SqliteFitnessLevelRepository(db_path)
    week_a = date(2026, 7, 14)
    week_b = date(2026, 7, 21)

    await repo.save(FitnessLevel(user_id="user-3", week_start=week_a, score=4))
    await repo.save(FitnessLevel(user_id="user-3", week_start=week_b, score=9))

    result_a = await repo.get_by_week("user-3", week_a)
    result_b = await repo.get_by_week("user-3", week_b)
    assert result_a is not None and result_a.score == 4
    assert result_b is not None and result_b.score == 9
