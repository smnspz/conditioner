from __future__ import annotations

from datetime import date, timedelta

from conditioner.core.domain.workout.workout import Workout
from conditioner.core.interfaces.readiness.readiness_repository import ReadinessRepository
from conditioner.core.interfaces.workout.workout_repository import WorkoutRepository
from conditioner.core.services.workout.adjust_for_readiness import adjust_remaining_sessions
from conditioner.core.services.workout.generate_weekly_plan import PrerequisitesMissingError


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


async def adjust_daily_sessions(
    user_id: str,
    day: date,
    readiness_repository: ReadinessRepository,
    workout_repository: WorkoutRepository,
) -> Workout:
    """Scale the user's not-yet-completed sessions from day onward by that day's readiness zone.

    Refuses (PrerequisitesMissingError) if there's no readiness score or no workout for the week.
    """

    readiness = await readiness_repository.get_by_date(user_id, day)
    if readiness is None:
        raise PrerequisitesMissingError("No readiness score available for this date")

    workout = await workout_repository.get_by_week(user_id, _week_start(day))
    if workout is None:
        raise PrerequisitesMissingError("No workout plan exists for this week")

    adjusted = adjust_remaining_sessions(workout, day, readiness.zone)
    await workout_repository.save(adjusted)
    return adjusted
