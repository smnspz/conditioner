from datetime import date as Date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from conditioner.api.dependencies import (
    get_constraints_repository,
    get_current_user_id,
    get_readiness_repository,
    get_workout_generation_provider,
    get_workout_repository,
)
from conditioner.api.dto.workouts import WorkoutOut
from conditioner.core.interfaces.readiness.readiness_repository import ReadinessRepository
from conditioner.core.interfaces.workout.constraints_repository import ConstraintsRepository
from conditioner.core.interfaces.workout.workout_generation_provider import (
    WorkoutGenerationProvider,
)
from conditioner.core.interfaces.workout.workout_repository import WorkoutRepository
from conditioner.core.services.workout.adjust_daily_sessions import adjust_daily_sessions
from conditioner.core.services.workout.generate_weekly_plan import (
    PrerequisitesMissingError,
    generate_weekly_plan,
)
from conditioner.core.services.workout.regenerate_week import regenerate_week

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.post("/{week_start}/generate", response_model=WorkoutOut)
async def generate(
    week_start: Date,
    user_id: Annotated[str, Depends(get_current_user_id)],
    constraints_repository: Annotated[
        ConstraintsRepository, Depends(get_constraints_repository)
    ],
    readiness_repository: Annotated[ReadinessRepository, Depends(get_readiness_repository)],
    generation_provider: Annotated[
        WorkoutGenerationProvider, Depends(get_workout_generation_provider)
    ],
    workout_repository: Annotated[WorkoutRepository, Depends(get_workout_repository)],
) -> WorkoutOut:
    """Generate and persist the authenticated user's weekly workout plan."""

    try:
        workout = await generate_weekly_plan(
            user_id,
            week_start,
            constraints_repository,
            readiness_repository,
            generation_provider,
            workout_repository,
        )
    except PrerequisitesMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    # Return the generated workout plan
    return WorkoutOut.from_domain(workout)


@router.post("/{week_start}/regenerate", response_model=WorkoutOut)
async def regenerate(
    week_start: Date,
    user_id: Annotated[str, Depends(get_current_user_id)],
    constraints_repository: Annotated[
        ConstraintsRepository, Depends(get_constraints_repository)
    ],
    readiness_repository: Annotated[ReadinessRepository, Depends(get_readiness_repository)],
    generation_provider: Annotated[
        WorkoutGenerationProvider, Depends(get_workout_generation_provider)
    ],
    workout_repository: Annotated[WorkoutRepository, Depends(get_workout_repository)],
) -> WorkoutOut:
    """Regenerate the authenticated user's weekly plan, e.g. after constraints changed."""

    try:
        workout = await regenerate_week(
            user_id,
            week_start,
            constraints_repository,
            readiness_repository,
            generation_provider,
            workout_repository,
        )
    except PrerequisitesMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    # Return the regenerated workout plan
    return WorkoutOut.from_domain(workout)


@router.post("/{day}/adjust", response_model=WorkoutOut)
async def adjust(
    day: Date,
    user_id: Annotated[str, Depends(get_current_user_id)],
    readiness_repository: Annotated[ReadinessRepository, Depends(get_readiness_repository)],
    workout_repository: Annotated[WorkoutRepository, Depends(get_workout_repository)],
) -> WorkoutOut:
    """Scale the authenticated user's remaining sessions from day onward by that day's readiness."""

    try:
        workout = await adjust_daily_sessions(
            user_id, day, readiness_repository, workout_repository
        )
    except PrerequisitesMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    # Return the adjusted workout plan
    return WorkoutOut.from_domain(workout)


@router.get("/{week_start}", response_model=WorkoutOut)
async def get_by_week(
    week_start: Date,
    user_id: Annotated[str, Depends(get_current_user_id)],
    workout_repository: Annotated[WorkoutRepository, Depends(get_workout_repository)],
) -> WorkoutOut:
    """Fetch the authenticated user's workout plan for the week starting on the given day."""

    # Get the stored workout plan for this week
    workout = await workout_repository.get_by_week(user_id, week_start)
    if workout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    # Return the stored workout plan
    return WorkoutOut.from_domain(workout)
