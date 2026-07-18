from __future__ import annotations

from datetime import date

from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.workout.workout import Workout
from conditioner.core.interfaces.fitness.fitness_level_repository import FitnessLevelRepository
from conditioner.core.interfaces.readiness.readiness_repository import ReadinessRepository
from conditioner.core.interfaces.workout.constraints_repository import ConstraintsRepository
from conditioner.core.interfaces.workout.exercise_catalog_repository import (
    ExerciseCatalogRepository,
)
from conditioner.core.interfaces.workout.workout_generation_provider import (
    WorkoutGenerationProvider,
)
from conditioner.core.interfaces.workout.workout_repository import WorkoutRepository


class PrerequisitesMissingError(Exception):
    """Raised when a user is missing constraints, fitness level, or readiness to generate from."""


async def generate_weekly_plan(
    user_id: str,
    week_start: date,
    constraints_repository: ConstraintsRepository,
    fitness_level_repository: FitnessLevelRepository,
    readiness_repository: ReadinessRepository,
    generation_provider: WorkoutGenerationProvider,
    workout_repository: WorkoutRepository,
    catalog_repository: ExerciseCatalogRepository,
) -> Workout:
    """Generate and persist a user's weekly workout plan.

    Requires constraints and a fitness level (weekly survey). The fitness level falls back to
    constraints.initial_perceived_fitness for the first week before the user has submitted a
    survey. Readiness is optional — it may be absent for a user's very first generation before
    any wearable or questionnaire data exists.
    Raises PrerequisitesMissingError if no exercises are available for the user's gear.
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

        # Seed fitness level from the onboarding value until the user submits a survey
        fitness_level = FitnessLevel(
            user_id=user_id,
            week_start=week_start,
            score=constraints.initial_perceived_fitness,
        )

    # Get the user's readiness score for the week's start date (may be absent for first week)
    readiness = await readiness_repository.get_by_date(user_id, week_start)

    # Get the gear-filtered exercise catalog for this user
    catalog_entries = await catalog_repository.filter_by_gear(constraints.equipment)
    if len(catalog_entries) < 5:
        raise PrerequisitesMissingError(
            "Not enough exercises available for the given equipment — "
            f"found {len(catalog_entries)}, minimum is 5"
        )

    # Get the generated plan from the AI provider
    workout = await generation_provider.generate_weekly_plan(
        user_id, week_start, constraints, fitness_level, readiness, catalog_entries
    )
    await workout_repository.save(workout)

    # Return the generated workout
    return workout
