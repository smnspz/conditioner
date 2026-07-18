from __future__ import annotations

from datetime import date, timedelta
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, create_model

from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import WorkoutConstraints
from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry
from conditioner.core.domain.workout.workout import Block, BlockExercise, BlockType, Session

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


class BlockExerciseSchema(BaseModel):
    """Structured-output schema for a single exercise within a block.

    Attributes:
        exercise_id: Catalog ID from the allowed list — never invent IDs.
        sets: Number of sets.
        reps: Reps per set; omit for time-based exercises.
        duration_seconds: Duration per set in seconds; omit for rep-based exercises.
        rest_seconds: Rest between sets in seconds.
        intensity_cue: Qualitative intensity note (e.g. 'RPE 7', 'controlled tempo').
        notes: Optional exercise-specific coaching note.
    """

    exercise_id: str
    sets: int = Field(ge=1)
    reps: int | None = None
    duration_seconds: int | None = None
    rest_seconds: int = Field(default=60, ge=0)
    intensity_cue: str = ""
    notes: str = ""


class BlockSchema(BaseModel):
    """Structured-output schema for a block (phase) within a session.

    Attributes:
        type: Phase label — one of 'warmup', 'main', 'finisher', 'cooldown'.
        estimated_minutes: Expected duration of this block in minutes.
        exercises: Exercises prescribed in this block.
    """

    type: Literal["warmup", "main", "finisher", "cooldown"]
    estimated_minutes: int = Field(ge=1)
    exercises: list[BlockExerciseSchema]


class SessionSchema(BaseModel):
    """Structured-output schema for a single generated session.

    Attributes:
        day_offset: Days from week_start (0=Monday).
        blocks: Ordered list of blocks making up the session.
    """

    day_offset: int
    blocks: list[BlockSchema]


class WeeklyPlanSchema(BaseModel):
    """Structured-output schema for a generated weekly plan."""

    sessions: list[SessionSchema]


def build_weekly_plan_schema(
    catalog_entries: list[ExerciseCatalogEntry],
) -> type[WeeklyPlanSchema]:
    """Build a per-request structured-output schema with exercise_id constrained to catalog IDs.

    exercise_id becomes a Literal[*catalog_ids] on BlockExerciseSchema so the model can only
    output IDs that exist in the pre-filtered catalog — structural enforcement, not a prompt hint.
    """

    # Set allowed exercise IDs from the filtered catalog
    allowed_ids = tuple(e.id for e in catalog_entries)
    dyn_exercise = create_model(
        "BlockExerciseSchema",
        __base__=BlockExerciseSchema,
        exercise_id=(Literal[allowed_ids], ...),
    )
    dyn_block = create_model(
        "BlockSchema",
        __base__=BlockSchema,
        exercises=(list[dyn_exercise], ...),
    )
    dyn_session = create_model(
        "SessionSchema",
        __base__=SessionSchema,
        blocks=(list[dyn_block], ...),
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
    catalog_entries: list[ExerciseCatalogEntry],
) -> str:
    """Build the text prompt describing this week's constraints, fitness level, readiness,
    and the pre-filtered exercise catalog the AI must draw from.

    fitness_level (weekly self-report, 1–10) sets the difficulty and complexity tier.
    readiness (daily computed score, 0–100) adjusts volume and intensity within that tier.
    readiness may be None for a user's first-ever generation before any wearable or
    questionnaire data exists; the prompt notes this and defers entirely to fitness level.
    catalog_entries is the gear-filtered catalog — every entry is valid for this user.
    """

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

    # Build compact catalog table (one line per exercise)
    catalog_lines = ["exercise_id | name | modality | movement_pattern | difficulty"]
    for e in sorted(catalog_entries, key=lambda x: x.id):
        catalog_lines.append(
            f"{e.id} | {e.name} | {e.modality.value} | {e.movement_pattern} | {e.difficulty}"
        )
    catalog_section = "\n".join(catalog_lines)

    # Warm-up/cool-down instruction
    if constraints.include_warmup_cooldown:
        warmup_cooldown_instruction = (
            "Each session must include a 'warmup' block (5–10 min, light mobility or cardio) "
            "and a 'cooldown' block (5–10 min, static stretching or gentle mobility). "
            "Keep warmup and cooldown exercises distinct from the main block."
        )
    else:
        warmup_cooldown_instruction = (
            "Do not include 'warmup' or 'cooldown' blocks — "
            "the user does not want structured warm-up or cool-down."
        )

    # Return the full generation prompt
    return (
        f"Generate a weekly conditioning plan starting {week_start.isoformat()}.\n"
        f"Goal: {constraints.goal.value}.\n"
        f"Available minutes per weekday (0=Monday..6=Sunday): "
        f"{constraints.available_minutes_by_weekday}.\n"
        f"{_fitness_level_line(fitness_level)}\n"
        f"{readiness_line}\n"
        "Only schedule sessions on weekdays with available minutes, and keep each "
        "session within its day's time budget.\n"
        "Vary the session focus across days — do not repeat the same exercise selection "
        "across multiple days. Rotate through lower-body, upper-body, full-body, "
        "conditioning, and recovery-focused sessions as appropriate for the week.\n"
        f"{warmup_cooldown_instruction}\n\n"
        "EXERCISE CATALOG — use only exercise_id values from this table. "
        "Do not invent IDs or use IDs not listed here.\n"
        f"{catalog_section}\n\n"
        "For each exercise: set reps OR duration_seconds (not both, not neither). "
        "Strength exercises use sets+reps; cardio/mobility use sets+duration_seconds. "
        "Isometric holds (e.g. plank) use sets+duration_seconds (duration = hold time in seconds)."
    )


def sessions_from_plan(
    week_start: date,
    plan: WeeklyPlanSchema,
    catalog_index: dict[str, ExerciseCatalogEntry],
) -> list[Session]:
    """Map a generated weekly plan schema to domain Sessions.

    catalog_index maps exercise_id to ExerciseCatalogEntry for name denormalization.
    Unknown exercise_ids fall back to the raw ID as the display name.
    """

    sessions: list[Session] = []
    for session_schema in plan.sessions:
        blocks: list[Block] = []
        for block_schema in session_schema.blocks:
            exercises: list[BlockExercise] = []
            for ex in block_schema.exercises:
                entry = catalog_index.get(ex.exercise_id)

                # Denormalize exercise name from catalog; fall back to ID if unknown
                exercise_name = entry.name if entry else ex.exercise_id
                exercises.append(
                    BlockExercise(
                        id=str(uuid4()),
                        exercise_id=ex.exercise_id,
                        exercise_name=exercise_name,
                        sets=ex.sets,
                        reps=ex.reps,
                        duration_seconds=ex.duration_seconds,
                        rest_seconds=ex.rest_seconds,
                        intensity_cue=ex.intensity_cue,
                        notes=ex.notes,
                    )
                )
            blocks.append(
                Block(
                    id=str(uuid4()),
                    type=BlockType(block_schema.type),
                    estimated_minutes=block_schema.estimated_minutes,
                    exercises=exercises,
                )
            )
        sessions.append(
            Session(
                id=str(uuid4()),
                date=week_start + timedelta(days=session_schema.day_offset),
                blocks=blocks,
            )
        )
    return sessions
