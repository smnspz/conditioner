from datetime import date

from conditioner.core.adapters.ai.workout_prompt import build_prompt, build_weekly_plan_schema
from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints

_WEEK_START = date(2026, 7, 14)
_BASE_CONSTRAINTS = WorkoutConstraints(
    user_id="user-1",
    equipment=["dumbbells"],
    goal=TrainingGoal.MMA_CONDITIONING,
    available_minutes_by_weekday={0: 60, 1: 60, 2: 60, 3: 60, 4: 60},
)
_FITNESS_LEVEL = FitnessLevel(user_id="user-1", week_start=_WEEK_START, score=6)
_READINESS = ReadinessScore(user_id="user-1", date=_WEEK_START, score=75, zone=ReadinessZone.GOOD)


def _equipment_enum(schema: object, variant: str) -> set[str]:
    # A single-value Literal renders as "const" in JSON schema, multi-value as "enum"
    defs = schema.model_json_schema()["$defs"]  # type: ignore[attr-defined]
    field = defs[variant]["properties"]["equipment"]
    return set(field["enum"]) if "enum" in field else {field["const"]}


def test_equipment_enum_includes_constraints_equipment_and_bodyweight() -> None:
    constraints = WorkoutConstraints(
        user_id="user-1",
        equipment=["dumbbells", "kettlebell"],
        goal=TrainingGoal.MMA_CONDITIONING,
        available_minutes_by_weekday={},
    )

    schema = build_weekly_plan_schema(constraints)

    assert _equipment_enum(schema, "StrengthExerciseSchema") == {
        "dumbbells",
        "kettlebell",
        "bodyweight",
    }
    assert _equipment_enum(schema, "CardioExerciseSchema") == {
        "dumbbells",
        "kettlebell",
        "bodyweight",
    }


def test_equipment_enum_defaults_to_bodyweight_only() -> None:
    constraints = WorkoutConstraints(
        user_id="user-1",
        equipment=[],
        goal=TrainingGoal.MMA_CONDITIONING,
        available_minutes_by_weekday={},
    )

    schema = build_weekly_plan_schema(constraints)

    assert _equipment_enum(schema, "StrengthExerciseSchema") == {"bodyweight"}


def test_build_prompt_includes_fitness_level_and_readiness() -> None:
    prompt = build_prompt(_WEEK_START, _BASE_CONSTRAINTS, _FITNESS_LEVEL, _READINESS)

    assert "6/10" in prompt
    assert "intermediate" in prompt
    assert "75/100" in prompt
    assert "good" in prompt


def test_build_prompt_with_none_readiness_notes_first_week() -> None:
    prompt = build_prompt(_WEEK_START, _BASE_CONSTRAINTS, _FITNESS_LEVEL, readiness=None)

    assert "6/10" in prompt
    assert "No readiness data yet" in prompt or "no data" in prompt.lower()
    assert "75/100" not in prompt


def test_build_prompt_beginner_fitness_uses_beginner_tier() -> None:
    fitness = FitnessLevel(user_id="user-1", week_start=_WEEK_START, score=2)

    prompt = build_prompt(_WEEK_START, _BASE_CONSTRAINTS, fitness, _READINESS)

    assert "2/10" in prompt
    assert "beginner" in prompt


def test_build_prompt_advanced_fitness_uses_advanced_tier() -> None:
    fitness = FitnessLevel(user_id="user-1", week_start=_WEEK_START, score=9)

    prompt = build_prompt(_WEEK_START, _BASE_CONSTRAINTS, fitness, _READINESS)

    assert "9/10" in prompt
    assert "advanced" in prompt
