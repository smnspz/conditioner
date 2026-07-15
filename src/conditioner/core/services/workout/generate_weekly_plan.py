from __future__ import annotations

from datetime import date

from conditioner.core.domain.workout.workout import Workout
from conditioner.core.interfaces.readiness.readiness_repository import ReadinessRepository
from conditioner.core.interfaces.workout.constraints_repository import ConstraintsRepository
from conditioner.core.interfaces.workout.workout_generation_provider import (
    WorkoutGenerationProvider,
)
from conditioner.core.interfaces.workout.workout_repository import WorkoutRepository


class PrerequisitesMissingError(Exception):
    """Raised when a user has no constraints or no readiness score to generate from."""


async def generate_weekly_plan(
    user_id: str,
    week_start: date,
    constraints_repository: ConstraintsRepository,
    readiness_repository: ReadinessRepository,
    generation_provider: WorkoutGenerationProvider,
    workout_repository: WorkoutRepository,
) -> Workout:
    """Generate and persist a user's weekly workout plan.

    For the first-ever generation (no readiness score yet), falls back to
    constraints.initial_perceived_fitness to inform starting difficulty and session
    structure. Refuses to generate if constraints are missing or if neither a
    readiness score nor an initial perceived fitness is available.
    """

    # Get the user's constraints
    constraints = await constraints_repository.get_by_user_id(user_id)
    if constraints is None:
        raise PrerequisitesMissingError("Workout constraints are not set")

    # Get the user's readiness score for the week's start date
    readiness = await readiness_repository.get_by_date(user_id, week_start)

    if readiness is None and constraints.initial_perceived_fitness is None:
        raise PrerequisitesMissingError(
            "No readiness score available and no initial perceived fitness set"
        )

    # Get the generated plan from the AI provider
    workout = await generation_provider.generate_weekly_plan(
        user_id, week_start, constraints, readiness
    )
    await workout_repository.save(workout)

    # Return the generated workout
    return workout
