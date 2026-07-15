from datetime import date
from unittest.mock import AsyncMock

import pytest

from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.domain.workout.workout import Exercise, ExerciseModality, Session, Workout
from conditioner.core.services.workout.generate_weekly_plan import PrerequisitesMissingError
from conditioner.core.services.workout.regenerate_week import regenerate_week

_USER_ID = "user-1"
_WEEK_START = date(2026, 7, 13)
_CONSTRAINTS = WorkoutConstraints(
    user_id=_USER_ID,
    equipment=["dumbbells"],
    goal=TrainingGoal.MMA_CONDITIONING,
    available_minutes_by_weekday={0: 30},
)
_FITNESS_LEVEL = FitnessLevel(user_id=_USER_ID, week_start=_WEEK_START, score=6)
_READINESS = ReadinessScore(user_id=_USER_ID, date=_WEEK_START, score=75, zone=ReadinessZone.GOOD)


def _session(day: date, *, completed: bool, sets: int) -> Session:
    return Session(
        id=f"session-{day}-{sets}",
        date=day,
        completed=completed,
        exercises=[
            Exercise(id="ex", name="Squat", modality=ExerciseModality.STRENGTH, sets=sets)
        ],
    )


def _repos(
    *,
    constraints=_CONSTRAINTS,
    fitness_level=_FITNESS_LEVEL,
    readiness=_READINESS,
    previous=None,
    regenerated=None,
):
    constraints_repository = AsyncMock(get_by_user_id=AsyncMock(return_value=constraints))
    fitness_level_repository = AsyncMock(get_by_week=AsyncMock(return_value=fitness_level))
    readiness_repository = AsyncMock(get_by_date=AsyncMock(return_value=readiness))
    workout_repository = AsyncMock(get_by_week=AsyncMock(return_value=previous))
    generation_provider = AsyncMock(generate_weekly_plan=AsyncMock(return_value=regenerated))
    return (
        constraints_repository,
        fitness_level_repository,
        readiness_repository,
        generation_provider,
        workout_repository,
    )


async def test_completed_sessions_are_kept_over_regenerated_ones() -> None:
    completed = _session(_WEEK_START, completed=True, sets=4)
    previous = Workout(id="old", user_id=_USER_ID, week_start=_WEEK_START, sessions=[completed])
    fresh_same_day = _session(_WEEK_START, completed=False, sets=9)
    regenerated_input = Workout(
        id="new", user_id=_USER_ID, week_start=_WEEK_START, sessions=[fresh_same_day]
    )
    constraints_repo, fitness_repo, readiness_repo, provider, workout_repo = _repos(
        previous=previous, regenerated=regenerated_input
    )

    result = await regenerate_week(
        _USER_ID, _WEEK_START, constraints_repo, fitness_repo, readiness_repo, provider,
        workout_repo,
    )

    assert result.sessions == [completed]
    workout_repo.save.assert_awaited_once_with(result)


async def test_incomplete_sessions_are_replaced_by_regenerated_ones() -> None:
    fresh = _session(_WEEK_START, completed=False, sets=5)
    regenerated_input = Workout(
        id="new", user_id=_USER_ID, week_start=_WEEK_START, sessions=[fresh]
    )
    constraints_repo, fitness_repo, readiness_repo, provider, workout_repo = _repos(
        previous=None, regenerated=regenerated_input
    )

    result = await regenerate_week(
        _USER_ID, _WEEK_START, constraints_repo, fitness_repo, readiness_repo, provider,
        workout_repo,
    )

    assert result.sessions == [fresh]


async def test_raises_when_constraints_missing() -> None:
    constraints_repo, fitness_repo, readiness_repo, provider, workout_repo = _repos(
        constraints=None
    )

    with pytest.raises(PrerequisitesMissingError):
        await regenerate_week(
            _USER_ID, _WEEK_START, constraints_repo, fitness_repo, readiness_repo, provider,
            workout_repo,
        )

    provider.generate_weekly_plan.assert_not_awaited()


async def test_raises_when_fitness_level_and_initial_perceived_fitness_both_missing() -> None:
    constraints_repo, fitness_repo, readiness_repo, provider, workout_repo = _repos(
        constraints=_CONSTRAINTS, fitness_level=None
    )

    with pytest.raises(PrerequisitesMissingError):
        await regenerate_week(
            _USER_ID, _WEEK_START, constraints_repo, fitness_repo, readiness_repo, provider,
            workout_repo,
        )

    provider.generate_weekly_plan.assert_not_awaited()


async def test_raises_when_readiness_missing() -> None:
    constraints_repo, fitness_repo, readiness_repo, provider, workout_repo = _repos(
        readiness=None
    )

    with pytest.raises(PrerequisitesMissingError):
        await regenerate_week(
            _USER_ID, _WEEK_START, constraints_repo, fitness_repo, readiness_repo, provider,
            workout_repo,
        )

    provider.generate_weekly_plan.assert_not_awaited()
