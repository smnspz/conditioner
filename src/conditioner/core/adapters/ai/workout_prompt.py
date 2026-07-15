from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, create_model

from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import WorkoutConstraints
from conditioner.core.domain.workout.workout import Exercise, ExerciseModality, Session

# Per-zone volume/intensity guidance injected into the prompt.
_ZONE_GUIDANCE: dict[ReadinessZone, str] = {
    ReadinessZone.PEAK: (
        "Readiness is peak: full volume and intensity, hard sessions are appropriate."
    ),
    ReadinessZone.GOOD: "Readiness is good: normal training volume and intensity.",
    ReadinessZone.MODERATE: (
        "Readiness is moderate: reduce volume and intensity below normal — fewer "
        "exercises and/or sets than a full session, avoid maximal effort."
    ),
    ReadinessZone.LIGHT: (
        "Readiness is light: light work or active recovery only — fewer exercises than "
        "a normal session, low intensity, no plyometric/explosive/high-impact movements."
    ),
    ReadinessZone.REST: (
        "Readiness is rest: complete rest or gentle mobility only. Do not prescribe any "
        "strength or cardio exercises — only slow mobility/stretching work, or an empty "
        "session if that's more appropriate."
    ),
}


def _fitness_level_line(fitness_level: FitnessLevel) -> str:
    """Return the fitness-level line for the prompt.

    Fitness level drives exercise difficulty and complexity tier:
    - 1–3 (beginner): simple foundational movements, low complexity, technique focus.
    - 4–6 (intermediate): standard progression, moderate complexity and volume.
    - 7–10 (advanced): complex movements, high volume and intensity potential.
    """

    score = fitness_level.score
    if score <= 3:
        tier = "beginner"
        guidance = (
            "Choose simple, foundational movements. Prioritise technique over load. "
            "Keep volume low and avoid complex or high-skill exercises."
        )
    elif score <= 6:
        tier = "intermediate"
        guidance = (
            "Use standard exercise progressions with moderate complexity and volume. "
            "A balanced mix of compound and accessory movements is appropriate."
        )
    else:
        tier = "advanced"
        guidance = (
            "Complex, high-skill movements are appropriate. Higher volume and intensity "
            "potential — challenge the user with demanding exercise selection."
        )

    # Return the formatted fitness level line
    return f"Fitness level: {score}/10 ({tier}). {guidance}"

# Structured-output schema shared by all WorkoutGenerationProvider adapters; exercise
# is a discriminated union on modality.


class StrengthExerciseSchema(BaseModel):
    """Structured-output schema for a strength exercise: sets/reps, no duration."""

    name: str
    # Discriminator tag as a plain str literal, not an enum.
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


def build_weekly_plan_schema(constraints: WorkoutConstraints) -> type[WeeklyPlanSchema]:
    """Build a per-request structured-output schema constraining each exercise's equipment
    to what the user actually has available (plus bodyweight).

    Equipment can't be a static field on StrengthExerciseSchema etc. — the allowed set is
    per-user (constraints.equipment), not known until request time — so the exercise/session/
    plan schema classes are rebuilt per call via create_model, subclassing the static base
    classes so isinstance checks in _to_exercise still work on the dynamic instances.
    """

    # Set allowed equipment values, deduped, bodyweight always allowed
    allowed = tuple(dict.fromkeys([*constraints.equipment, "bodyweight"]))

    dyn_strength = create_model(
        "StrengthExerciseSchema",
        __base__=StrengthExerciseSchema,
        equipment=(Literal[allowed], ...),
    )
    dyn_cardio = create_model(
        "CardioExerciseSchema",
        __base__=CardioExerciseSchema,
        equipment=(Literal[allowed], ...),
    )
    dyn_mobility = create_model(
        "MobilityExerciseSchema",
        __base__=MobilityExerciseSchema,
        equipment=(Literal[allowed], ...),
    )
    dyn_exercise = Annotated[
        dyn_strength | dyn_cardio | dyn_mobility,
        Field(discriminator="modality"),
    ]
    dyn_session = create_model(
        "SessionSchema", __base__=SessionSchema, exercises=(list[dyn_exercise], ...)
    )

    # Return the per-request weekly plan schema class
    return create_model(
        "WeeklyPlanSchema", __base__=WeeklyPlanSchema, sessions=(list[dyn_session], ...)
    )


def build_prompt(
    week_start: date,
    constraints: WorkoutConstraints,
    fitness_level: FitnessLevel,
    readiness: ReadinessScore | None,
) -> str:
    """Build the text prompt describing this week's constraints, fitness level, and readiness.

    fitness_level (weekly self-report, 1–10) sets the difficulty and complexity tier.
    readiness (daily computed score, 0–100) adjusts volume and intensity within that tier.
    readiness may be None for a user's first-ever generation before any wearable or
    questionnaire data exists; the prompt notes this and defers entirely to fitness level.
    """

    equipment = ", ".join(constraints.equipment) or "none (bodyweight only)"

    if readiness is None:
        readiness_line = (
            "Readiness: no data yet (first week). "
            "Calibrate intensity conservatively — stay well within the user's capacity."
        )
    else:
        readiness_line = (
            f"Readiness: {readiness.score}/100 ({readiness.zone.value}). "
            f"{_ZONE_GUIDANCE[readiness.zone]}"
        )

    return (
        f"Generate a weekly conditioning plan starting {week_start.isoformat()}.\n"
        f"Goal: {constraints.goal.value}.\n"
        f"Available equipment: {equipment}.\n"
        f"Available minutes per weekday (0=Monday..6=Sunday): "
        f"{constraints.available_minutes_by_weekday}.\n"
        f"{_fitness_level_line(fitness_level)}\n"
        f"{readiness_line}\n"
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

    # Return cardio/mobility exercise
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
