from datetime import date
from unittest.mock import AsyncMock

import pytest

from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.domain.workout.workout import Workout
from conditioner.core.services.workout.generate_weekly_plan import (
    PrerequisitesMissingError,
    generate_weekly_plan,
)

_USER_ID = "user-1"
_WEEK_START = date(2026, 7, 13)

_CONSTRAINTS = WorkoutConstraints(
    user_id=_USER_ID,
    equipment=["dumbbells"],
    goal=TrainingGoal.MMA_CONDITIONING,
    available_minutes_by_weekday={0: 60},
)
_CONSTRAINTS_WITH_FITNESS = WorkoutConstraints(
    user_id=_USER_ID,
    equipment=["dumbbells"],
    goal=TrainingGoal.MMA_CONDITIONING,
    available_minutes_by_weekday={0: 60},
    initial_perceived_fitness=7,
)
_READINESS = ReadinessScore(
    user_id=_USER_ID, date=_WEEK_START, score=75, zone=ReadinessZone.GOOD
)
_WORKOUT = Workout(id="workout-1", user_id=_USER_ID, week_start=_WEEK_START)


def _repos(*, constraints=_CONSTRAINTS, readiness=_READINESS):
    constraints_repository = AsyncMock(get_by_user_id=AsyncMock(return_value=constraints))
    readiness_repository = AsyncMock(get_by_date=AsyncMock(return_value=readiness))
    generation_provider = AsyncMock(generate_weekly_plan=AsyncMock(return_value=_WORKOUT))
    workout_repository = AsyncMock()
    return constraints_repository, readiness_repository, generation_provider, workout_repository


async def test_generates_and_saves_plan_when_prerequisites_set() -> None:
    constraints_repo, readiness_repo, provider, workout_repo = _repos()

    workout = await generate_weekly_plan(
        _USER_ID, _WEEK_START, constraints_repo, readiness_repo, provider, workout_repo
    )

    assert workout == _WORKOUT
    provider.generate_weekly_plan.assert_awaited_once_with(
        _USER_ID, _WEEK_START, _CONSTRAINTS, _READINESS
    )
    workout_repo.save.assert_awaited_once_with(_WORKOUT)


async def test_raises_when_constraints_missing() -> None:
    constraints_repo, readiness_repo, provider, workout_repo = _repos(constraints=None)

    with pytest.raises(PrerequisitesMissingError):
        await generate_weekly_plan(
            _USER_ID, _WEEK_START, constraints_repo, readiness_repo, provider, workout_repo
        )

    provider.generate_weekly_plan.assert_not_awaited()
    workout_repo.save.assert_not_awaited()


async def test_raises_when_readiness_missing_and_no_perceived_fitness() -> None:
    constraints_repo, readiness_repo, provider, workout_repo = _repos(readiness=None)

    with pytest.raises(PrerequisitesMissingError):
        await generate_weekly_plan(
            _USER_ID, _WEEK_START, constraints_repo, readiness_repo, provider, workout_repo
        )

    provider.generate_weekly_plan.assert_not_awaited()
    workout_repo.save.assert_not_awaited()


async def test_uses_perceived_fitness_when_no_readiness_score() -> None:
    constraints_repo = AsyncMock(
        get_by_user_id=AsyncMock(return_value=_CONSTRAINTS_WITH_FITNESS)
    )
    readiness_repo = AsyncMock(get_by_date=AsyncMock(return_value=None))
    provider = AsyncMock(generate_weekly_plan=AsyncMock(return_value=_WORKOUT))
    workout_repo = AsyncMock()

    workout = await generate_weekly_plan(
        _USER_ID, _WEEK_START, constraints_repo, readiness_repo, provider, workout_repo
    )

    assert workout == _WORKOUT

    # Verify AI was called with a synthesized readiness score: 7 * 10 = 70 (GOOD zone)
    call_args = provider.generate_weekly_plan.call_args
    synthesized_readiness = call_args.args[3]
    assert synthesized_readiness.score == 70
    assert synthesized_readiness.zone == ReadinessZone.GOOD
    assert synthesized_readiness.user_id == _USER_ID
    assert synthesized_readiness.date == _WEEK_START
