from conditioner.core.adapters.ai.workout_prompt import build_weekly_plan_schema
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
