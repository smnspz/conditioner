from __future__ import annotations

from datetime import date

from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.workout.workout import Workout
from conditioner.core.interfaces.fitness.fitness_level_repository import FitnessLevelRepository
from conditioner.core.interfaces.readiness.readiness_repository import ReadinessRepository
from conditioner.core.interfaces.workout.constraints_repository import ConstraintsRepository
from conditioner.core.interfaces.workout.workout_generation_provider import (
    WorkoutGenerationProvider,
)
from conditioner.core.interfaces.workout.workout_repository import WorkoutRepository
from conditioner.core.services.workout.generate_weekly_plan import PrerequisitesMissingError


async def regenerate_week(
    user_id: str,
    week_start: date,
    constraints_repository: ConstraintsRepository,
    fitness_level_repository: FitnessLevelRepository,
    readiness_repository: ReadinessRepository,
    generation_provider: WorkoutGenerationProvider,
    workout_repository: WorkoutRepository,
) -> Workout:
    """Regenerate a user's weekly plan against current constraints, keeping completed sessions.

    Refuses (PrerequisitesMissingError) if constraints, a fitness level, or a readiness score
    for the week's start date are missing. Sessions already marked completed in the prior plan
    are kept as-is instead of being replaced by the newly generated ones for the same date.
    """

    # Get the user's constraints
    constraints = await constraints_repository.get_by_user_id(user_id)
    if constraints is None:
        raise PrerequisitesMissingError("Workout constraints are not set")

    # Get the user's weekly fitness level, falling back to the initial perceived fitness seed
    fitness_level = await fitness_level_repository.get_by_week(user_id, week_start)
    if fitness_level is None:
        if constraints.initial_perceived_fitness is None:
            raise PrerequisitesMissingError(
                "No fitness level set for this week and no initial perceived fitness configured"
            )

        # Seed fitness level from the onboarding value
        fitness_level = FitnessLevel(
            user_id=user_id,
            week_start=week_start,
            score=constraints.initial_perceived_fitness,
        )

    # Get the user's readiness score for the week's start date
    readiness = await readiness_repository.get_by_date(user_id, week_start)
    if readiness is None:
        raise PrerequisitesMissingError("No readiness score available for this date")

    # Get the previous plan to preserve completed sessions
    previous = await workout_repository.get_by_week(user_id, week_start)
    completed_by_date = (
        {session.date: session for session in previous.sessions if session.completed}
        if previous is not None
        else {}
    )

    # Get the regenerated plan from the AI provider
    regenerated = await generation_provider.generate_weekly_plan(
        user_id, week_start, constraints, fitness_level, readiness
    )
    regenerated.sessions = [
        completed_by_date.get(session.date, session) for session in regenerated.sessions
    ]
    await workout_repository.save(regenerated)

    # Return the regenerated workout
    return regenerated
