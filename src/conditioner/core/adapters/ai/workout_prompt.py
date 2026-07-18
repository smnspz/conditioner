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
            "Keep volume low and avoid complex or high-skill exercises. "
            "Beginner does NOT mean rest or mobility only — prescribe real training "
            "sessions with basic strength and cardio movements appropriate for a novice."
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
    """Structured-output schema for a single generated session.

    Attributes:
        day_offset: Days from week_start (0=Monday).
        warmup_exercises: Optional warm-up block before main exercises.
        exercises: Main exercises for the session.
        cooldown_exercises: Optional cool-down block after main exercises.
    """

    day_offset: int
    warmup_exercises: list[ExerciseSchema] = []
    exercises: list[ExerciseSchema] = []
    cooldown_exercises: list[ExerciseSchema] = []


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
        "SessionSchema",
        __base__=SessionSchema,
        warmup_exercises=(list[dyn_exercise], []),
        exercises=(list[dyn_exercise], []),
        cooldown_exercises=(list[dyn_exercise], []),
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

    equipment_ids = constraints.equipment
    equipment = ", ".join(equipment_ids) or "none (bodyweight only)"

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

    # Equipment-specific notes injected when the user has certain gear available
    equipment_notes = ""
    if "resistance_bands" in equipment_ids:
        equipment_notes += (
            "\nResistance bands are a full strength-training tool — band rows, band presses, "
            "band squats, band deadlifts, band curls, band tricep extensions, etc. are all "
            "appropriate strength exercises. Do not default to cardio or mobility only when "
            "bands are the primary available equipment."
        )

    # Warm-up/cool-down instruction section
    if constraints.include_warmup_cooldown:
        warmup_cooldown_section = (
            "\nEach session must include:\n"
            "  - A warmup_exercises block: 5–10 minutes of light mobility or low-intensity "
            "cardio to prepare for the session.\n"
            "  - A cooldown_exercises block: 5–10 minutes of static stretching or gentle "
            "mobility to close the session.\n"
            "Keep warm-up and cool-down exercises distinct from the main exercises block."
        )
    else:
        warmup_cooldown_section = (
            "\nLeave warmup_exercises and cooldown_exercises empty — "
            "the user does not want structured warm-up or cool-down blocks."
        )

    # Return the full generation prompt
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
        "prescribe an exercise requiring equipment that isn't listed. "
        "Do not include any equipment name in an exercise name unless that equipment "
        "appears in the allowed list above (e.g. never write 'Kettlebell Swing' if "
        "kettlebells are not listed).\n"
        "Set the equipment field on each exercise to the specific piece of equipment "
        "actually used (e.g. 'resistance_bands', 'dumbbells'). Only set it to "
        "'bodyweight' when the exercise genuinely requires no equipment at all.\n"
        "Vary the session focus across days — do not repeat the same exercise selection "
        "across multiple days. Rotate through lower-body, upper-body, full-body, "
        "conditioning, and recovery-focused sessions as appropriate for the week."
        f"{equipment_notes}"
        f"{warmup_cooldown_section}"
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
            warmup_exercises=[_to_exercise(ex) for ex in session.warmup_exercises],
            exercises=[_to_exercise(ex) for ex in session.exercises],
            cooldown_exercises=[_to_exercise(ex) for ex in session.cooldown_exercises],
        )
        for session in plan.sessions
    ]
