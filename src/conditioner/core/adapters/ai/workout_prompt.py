from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from pydantic import BaseModel

from conditioner.core.domain.readiness.readiness import ReadinessScore
from conditioner.core.domain.workout.constraints import WorkoutConstraints
from conditioner.core.domain.workout.workout import Exercise, ExerciseModality, Session

# Prompt/structured-output shape shared by every WorkoutGenerationProvider adapter, so
# each adapter only owns the mechanics of calling its own AI API.


class ExerciseSchema(BaseModel):
    """Structured-output schema for a single generated exercise."""

    name: str
    modality: ExerciseModality
    sets: int | None = None
    reps: int | None = None
    duration_minutes: float | None = None
    target_load: float | None = None


class SessionSchema(BaseModel):
    """Structured-output schema for a single generated session."""

    day_offset: int
    exercises: list[ExerciseSchema]


class WeeklyPlanSchema(BaseModel):
    """Structured-output schema for a generated weekly plan."""

    sessions: list[SessionSchema]


def build_prompt(
    week_start: date, constraints: WorkoutConstraints, readiness: ReadinessScore
) -> str:
    """Build the text prompt describing this week's constraints and readiness."""

    return (
        f"Generate a weekly conditioning plan starting {week_start.isoformat()}.\n"
        f"Goal: {constraints.goal.value}.\n"
        f"Available equipment: {', '.join(constraints.equipment) or 'none'}.\n"
        f"Available minutes per weekday (0=Monday..6=Sunday): "
        f"{constraints.available_minutes_by_weekday}.\n"
        f"Current readiness: {readiness.score}/100 ({readiness.zone.value}).\n"
        "Only schedule sessions on weekdays with available minutes, and keep each "
        "session within its day's time budget."
    )


def sessions_from_plan(week_start: date, plan: WeeklyPlanSchema) -> list[Session]:
    """Map a generated weekly plan schema to domain Sessions."""

    return [
        Session(
            id=str(uuid4()),
            date=week_start + timedelta(days=session.day_offset),
            exercises=[
                Exercise(
                    id=str(uuid4()),
                    name=exercise.name,
                    modality=exercise.modality,
                    sets=exercise.sets,
                    reps=exercise.reps,
                    duration_minutes=exercise.duration_minutes,
                    target_load=exercise.target_load,
                )
                for exercise in session.exercises
            ],
        )
        for session in plan.sessions
    ]
