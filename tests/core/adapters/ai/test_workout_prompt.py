from datetime import date

from conditioner.core.adapters.ai.workout_prompt import build_prompt, build_weekly_plan_schema
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints


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


_WEEK_START = date(2026, 7, 14)
_BASE_CONSTRAINTS = WorkoutConstraints(
    user_id="user-1",
    equipment=["dumbbells"],
    goal=TrainingGoal.MMA_CONDITIONING,
    available_minutes_by_weekday={0: 60, 1: 60, 2: 60, 3: 60, 4: 60},
)


def test_build_prompt_with_readiness_includes_score_and_zone() -> None:
    readiness = ReadinessScore(
        user_id="user-1", date=_WEEK_START, score=75, zone=ReadinessZone.GOOD
    )

    prompt = build_prompt(_WEEK_START, _BASE_CONSTRAINTS, readiness)

    assert "75/100" in prompt
    assert "good" in prompt
    assert "initial perceived fitness" not in prompt


def test_build_prompt_without_readiness_uses_initial_fitness_guidance() -> None:
    constraints = WorkoutConstraints(
        user_id="user-1",
        equipment=["dumbbells"],
        goal=TrainingGoal.MMA_CONDITIONING,
        available_minutes_by_weekday={0: 60, 1: 60, 2: 60, 3: 60, 4: 60},
        initial_perceived_fitness=2,
    )

    prompt = build_prompt(_WEEK_START, constraints, readiness=None)

    assert "2/10" in prompt
    assert "low" in prompt
    assert "rest day" in prompt
    assert "75/100" not in prompt


def test_build_prompt_low_fitness_mentions_midweek_rest_and_no_weekend() -> None:
    constraints = WorkoutConstraints(
        user_id="user-1",
        equipment=[],
        goal=TrainingGoal.MMA_CONDITIONING,
        available_minutes_by_weekday={},
        initial_perceived_fitness=1,
    )

    prompt = build_prompt(_WEEK_START, constraints, readiness=None)

    assert "Wednesday" in prompt
    assert "Saturday" in prompt or "Sunday" in prompt or "weekend" in prompt.lower()


def test_build_prompt_high_fitness_mentions_full_schedule() -> None:
    constraints = WorkoutConstraints(
        user_id="user-1",
        equipment=[],
        goal=TrainingGoal.MMA_CONDITIONING,
        available_minutes_by_weekday={},
        initial_perceived_fitness=9,
    )

    prompt = build_prompt(_WEEK_START, constraints, readiness=None)

    assert "9/10" in prompt
    assert "high" in prompt
