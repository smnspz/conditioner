from datetime import date as Date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from conditioner.api.dependencies import (
    get_constraints_repository,
    get_current_user_id,
    get_readiness_repository,
    get_workout_generation_provider,
    get_workout_repository,
)
from conditioner.core.domain.workout.workout import Workout
from conditioner.core.interfaces.readiness.readiness_repository import ReadinessRepository
from conditioner.core.interfaces.workout.constraints_repository import ConstraintsRepository
from conditioner.core.interfaces.workout.workout_generation_provider import (
    WorkoutGenerationProvider,
)
from conditioner.core.interfaces.workout.workout_repository import WorkoutRepository
from conditioner.core.services.workout.generate_weekly_plan import (
    PrerequisitesMissingError,
    generate_weekly_plan,
)

router = APIRouter(prefix="/workouts", tags=["workouts"])


class ExerciseOut(BaseModel):
    """Serialized exercise returned to the client."""

    id: str
    name: str
    modality: str
    sets: int | None
    reps: int | None
    duration_minutes: float | None
    target_load: float | None


class SessionOut(BaseModel):
    """Serialized session returned to the client."""

    id: str
    date: Date
    exercises: list[ExerciseOut]
    completed: bool


class WorkoutOut(BaseModel):
    """Serialized weekly workout plan returned to the client."""

    id: str
    week_start: Date
    sessions: list[SessionOut]


def _to_out(workout: Workout) -> WorkoutOut:
    return WorkoutOut(
        id=workout.id,
        week_start=workout.week_start,
        sessions=[
            SessionOut(
                id=session.id,
                date=session.date,
                completed=session.completed,
                exercises=[
                    ExerciseOut(
                        id=exercise.id,
                        name=exercise.name,
                        modality=exercise.modality.value,
                        sets=exercise.sets,
                        reps=exercise.reps,
                        duration_minutes=exercise.duration_minutes,
                        target_load=exercise.target_load,
                    )
                    for exercise in session.exercises
                ],
            )
            for session in workout.sessions
        ],
    )


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
    return _to_out(workout)


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
    return _to_out(workout)
