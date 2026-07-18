from datetime import date
from unittest.mock import AsyncMock

import pytest

from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.workout import Block, BlockExercise, BlockType, Session, Workout
from conditioner.core.services.workout.adjust_daily_sessions import adjust_daily_sessions
from conditioner.core.services.workout.generate_weekly_plan import PrerequisitesMissingError

_USER_ID = "user-1"
_DAY = date(2026, 7, 15)  # Wednesday
_WEEK_START = date(2026, 7, 13)  # Monday
_READINESS = ReadinessScore(user_id=_USER_ID, date=_DAY, score=55, zone=ReadinessZone.MODERATE)
_WORKOUT = Workout(
    id="workout-1",
    user_id=_USER_ID,
    week_start=_WEEK_START,
    sessions=[
        Session(
            id="session-1",
            date=_DAY,
            blocks=[
                Block(
                    id="block-1",
                    type=BlockType.MAIN,
                    estimated_minutes=30,
                    exercises=[
                        BlockExercise(
                            id="ex-1",
                            exercise_id="bw_squat",
                            exercise_name="Bodyweight Squat",
                            sets=4,
                            reps=10,
                        )
                    ],
                )
            ],
        )
    ],
)


def _repos(*, readiness=_READINESS, workout=_WORKOUT):
    readiness_repository = AsyncMock(get_by_date=AsyncMock(return_value=readiness))
    workout_repository = AsyncMock(get_by_week=AsyncMock(return_value=workout))
    return readiness_repository, workout_repository


async def test_adjusts_and_saves_workout_for_the_week() -> None:
    readiness_repo, workout_repo = _repos()

    adjusted = await adjust_daily_sessions(_USER_ID, _DAY, readiness_repo, workout_repo)

    workout_repo.get_by_week.assert_awaited_once_with(_USER_ID, _WEEK_START)
    # 4 sets * 0.75 (MODERATE zone) = 3
    assert adjusted.sessions[0].blocks[0].exercises[0].sets == 3
    workout_repo.save.assert_awaited_once_with(adjusted)


async def test_raises_when_readiness_missing() -> None:
    readiness_repo, workout_repo = _repos(readiness=None)

    with pytest.raises(PrerequisitesMissingError):
        await adjust_daily_sessions(_USER_ID, _DAY, readiness_repo, workout_repo)

    workout_repo.save.assert_not_awaited()


async def test_raises_when_workout_missing() -> None:
    readiness_repo, workout_repo = _repos(workout=None)

    with pytest.raises(PrerequisitesMissingError):
        await adjust_daily_sessions(_USER_ID, _DAY, readiness_repo, workout_repo)

    workout_repo.save.assert_not_awaited()
