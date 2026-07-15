from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from conditioner.core.domain.readiness.readiness import ReadinessScore
from conditioner.core.domain.workout.constraints import WorkoutConstraints
from conditioner.core.domain.workout.workout import Exercise, ExerciseModality, Session

# Prompt/structured-output shape shared by every WorkoutGenerationProvider adapter, so
# each adapter only owns the mechanics of calling its own AI API.
#
# Exercise schema is a discriminated union on modality rather than one model with every
# field optional. Models are unreliable at following a natural-language instruction like
# "leave sets/reps null for cardio" — plain optional fields let them omit everything. Making
# sets/reps and duration_minutes required-per-variant turns that into a syntactic constraint
# the structured-output engine enforces, which measurably fixed the compliance gap in testing.


class StrengthExerciseSchema(BaseModel):
    """Structured-output schema for a strength exercise: sets/reps, no duration."""

    name: str
    # Plain str literal, not the ExerciseModality enum — pydantic's discriminated-union
    # tag matching doesn't coerce a JSON string against a plain (non-str) Enum literal.
    modality: Literal["strength"] = "strength"
    sets: int
    reps: int
    target_load: float | None = None


class CardioExerciseSchema(BaseModel):
    """Structured-output schema for a cardio exercise: duration, no sets/reps."""

    name: str
    modality: Literal["cardio"] = "cardio"
    duration_minutes: float
    target_load: float | None = None


class MobilityExerciseSchema(BaseModel):
    """Structured-output schema for a mobility exercise: duration, no sets/reps."""

    name: str
    modality: Literal["mobility"] = "mobility"
    duration_minutes: float
    target_load: float | None = None


ExerciseSchema = Annotated[
    StrengthExerciseSchema | CardioExerciseSchema | MobilityExerciseSchema,
    Field(discriminator="modality"),
]


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

    equipment = ", ".join(constraints.equipment) or "none (bodyweight only)"
    return (
        f"Generate a weekly conditioning plan starting {week_start.isoformat()}.\n"
        f"Goal: {constraints.goal.value}.\n"
        f"Available equipment: {equipment}.\n"
        f"Available minutes per weekday (0=Monday..6=Sunday): "
        f"{constraints.available_minutes_by_weekday}.\n"
        f"Current readiness: {readiness.score}/100 ({readiness.zone.value}).\n"
        "Only schedule sessions on weekdays with available minutes, and keep each "
        "session within its day's time budget.\n"
        f"Only use the listed equipment ({equipment}) and bodyweight exercises — never "
        "prescribe an exercise requiring equipment that isn't listed."
    )


def _to_exercise(
    schema: StrengthExerciseSchema | CardioExerciseSchema | MobilityExerciseSchema,
) -> Exercise:
    """Map a discriminated exercise schema variant to a domain Exercise."""

    if isinstance(schema, StrengthExerciseSchema):
        return Exercise(
            id=str(uuid4()),
            name=schema.name,
            modality=ExerciseModality(schema.modality),
            sets=schema.sets,
            reps=schema.reps,
            target_load=schema.target_load,
        )

    # Return cardio/mobility exercise, duration-based rather than sets/reps
    return Exercise(
        id=str(uuid4()),
        name=schema.name,
        modality=ExerciseModality(schema.modality),
        duration_minutes=schema.duration_minutes,
        target_load=schema.target_load,
    )


def sessions_from_plan(week_start: date, plan: WeeklyPlanSchema) -> list[Session]:
    """Map a generated weekly plan schema to domain Sessions."""

    return [
        Session(
            id=str(uuid4()),
            date=week_start + timedelta(days=session.day_offset),
            exercises=[_to_exercise(exercise) for exercise in session.exercises],
        )
        for session in plan.sessions
    ]
