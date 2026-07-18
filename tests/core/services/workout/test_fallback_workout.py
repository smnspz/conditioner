from datetime import date

from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry
from conditioner.core.domain.workout.workout import BlockType, ExerciseModality
from conditioner.core.services.workout.fallback_workout import build_fallback_workout

_USER_ID = "user-1"
_WEEK_START = date(2026, 7, 14)
_CONSTRAINTS = WorkoutConstraints(
    user_id=_USER_ID,
    equipment=[],
    goal=TrainingGoal.MMA_CONDITIONING,
    available_minutes_by_weekday={0: 45, 2: 45, 4: 45},
)


def _catalog(n: int = 10) -> list[ExerciseCatalogEntry]:
    patterns = ["push", "pull", "hinge", "squat", "core", "cardio", "push", "pull", "squat", "core"]
    return [
        ExerciseCatalogEntry(
            id=f"bw_ex_{i}",
            name=f"Exercise {i}",
            modality=ExerciseModality.STRENGTH,
            movement_pattern=patterns[i % len(patterns)],
            difficulty=1,
        )
        for i in range(n)
    ]


def test_fallback_workout_is_structurally_valid() -> None:
    fitness = FitnessLevel(user_id=_USER_ID, week_start=_WEEK_START, score=5)
    workout = build_fallback_workout(_USER_ID, _WEEK_START, _CONSTRAINTS, fitness, _catalog())

    assert workout.user_id == _USER_ID
    assert workout.week_start == _WEEK_START
    assert len(workout.sessions) > 0
    for session in workout.sessions:
        assert session.blocks
        for block in session.blocks:
            assert block.exercises
            for ex in block.exercises:
                assert ex.sets >= 1
                assert ex.reps is not None or ex.duration_seconds is not None


def test_fallback_uses_only_catalog_ids() -> None:
    fitness = FitnessLevel(user_id=_USER_ID, week_start=_WEEK_START, score=5)
    catalog = _catalog()
    valid_ids = {e.id for e in catalog}

    workout = build_fallback_workout(_USER_ID, _WEEK_START, _CONSTRAINTS, fitness, catalog)

    for session in workout.sessions:
        for block in session.blocks:
            for ex in block.exercises:
                assert ex.exercise_id in valid_ids


def test_fallback_uses_main_block_type() -> None:
    fitness = FitnessLevel(user_id=_USER_ID, week_start=_WEEK_START, score=5)
    workout = build_fallback_workout(_USER_ID, _WEEK_START, _CONSTRAINTS, fitness, _catalog())

    for session in workout.sessions:
        assert all(b.type == BlockType.MAIN for b in session.blocks)


def test_fallback_beginner_uses_lower_volume() -> None:
    beginner = FitnessLevel(user_id=_USER_ID, week_start=_WEEK_START, score=2)
    advanced = FitnessLevel(user_id=_USER_ID, week_start=_WEEK_START, score=9)
    catalog = _catalog()

    beginner_workout = build_fallback_workout(_USER_ID, _WEEK_START, _CONSTRAINTS, beginner, catalog)
    advanced_workout = build_fallback_workout(_USER_ID, _WEEK_START, _CONSTRAINTS, advanced, catalog)

    def total_sets(workout):
        return sum(
            ex.sets
            for s in workout.sessions for b in s.blocks for ex in b.exercises
        )

    assert total_sets(beginner_workout) <= total_sets(advanced_workout)
