from datetime import date

from conditioner.core.adapters.ai.workout_prompt import build_prompt, build_weekly_plan_schema
from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry
from conditioner.core.domain.workout.workout import ExerciseModality

_WEEK_START = date(2026, 7, 14)
_BASE_CONSTRAINTS = WorkoutConstraints(
    user_id="user-1",
    equipment=["dumbbells"],
    goal=TrainingGoal.MMA_CONDITIONING,
    available_minutes_by_weekday={0: 60, 1: 60, 2: 60, 3: 60, 4: 60},
)
_FITNESS_LEVEL = FitnessLevel(user_id="user-1", week_start=_WEEK_START, score=6)
_READINESS = ReadinessScore(user_id="user-1", date=_WEEK_START, score=75, zone=ReadinessZone.GOOD)


def _catalog(*ids: str) -> list[ExerciseCatalogEntry]:
    return [
        ExerciseCatalogEntry(
            id=eid,
            name=eid.replace("_", " ").title(),
            modality=ExerciseModality.STRENGTH,
            movement_pattern="squat",
        )
        for eid in ids
    ]


def test_exercise_id_literal_matches_catalog_ids() -> None:
    catalog = _catalog("bw_squat", "bw_push_up", "db_rdl")

    schema = build_weekly_plan_schema(catalog)

    defs = schema.model_json_schema()["$defs"]
    ex_def = defs["BlockExerciseSchema"]
    id_field = ex_def["properties"]["exercise_id"]
    allowed = set(id_field["enum"]) if "enum" in id_field else {id_field["const"]}
    assert allowed == {"bw_squat", "bw_push_up", "db_rdl"}


def test_build_prompt_includes_fitness_level_and_readiness() -> None:
    catalog = _catalog("bw_squat")
    prompt = build_prompt(_WEEK_START, _BASE_CONSTRAINTS, _FITNESS_LEVEL, _READINESS, catalog)

    assert "6/10" in prompt
    assert "intermediate" in prompt
    assert "75/100" in prompt
    assert "good" in prompt


def test_build_prompt_with_none_readiness_notes_first_week() -> None:
    catalog = _catalog("bw_squat")
    prompt = build_prompt(_WEEK_START, _BASE_CONSTRAINTS, _FITNESS_LEVEL, readiness=None,
                          catalog_entries=catalog)

    assert "6/10" in prompt
    assert "No readiness data yet" in prompt or "no data" in prompt.lower()
    assert "75/100" not in prompt


def test_build_prompt_beginner_fitness_uses_beginner_tier() -> None:
    fitness = FitnessLevel(user_id="user-1", week_start=_WEEK_START, score=2)
    catalog = _catalog("bw_squat")

    prompt = build_prompt(_WEEK_START, _BASE_CONSTRAINTS, fitness, _READINESS, catalog)

    assert "2/10" in prompt
    assert "beginner" in prompt


def test_build_prompt_advanced_fitness_uses_advanced_tier() -> None:
    fitness = FitnessLevel(user_id="user-1", week_start=_WEEK_START, score=9)
    catalog = _catalog("bw_squat")

    prompt = build_prompt(_WEEK_START, _BASE_CONSTRAINTS, fitness, _READINESS, catalog)

    assert "9/10" in prompt
    assert "advanced" in prompt


def test_build_prompt_includes_catalog_table() -> None:
    catalog = _catalog("bw_squat", "bw_push_up")

    prompt = build_prompt(_WEEK_START, _BASE_CONSTRAINTS, _FITNESS_LEVEL, _READINESS, catalog)

    assert "bw_squat" in prompt
    assert "bw_push_up" in prompt
    assert "exercise_id" in prompt
