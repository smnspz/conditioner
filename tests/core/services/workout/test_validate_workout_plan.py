from datetime import date

from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry
from conditioner.core.domain.workout.workout import Block, BlockExercise, BlockType, ExerciseModality, Session, Workout
from conditioner.core.services.workout.validate_workout_plan import ValidationError, validate_workout_plan

_CATALOG = {
    "bw_squat": ExerciseCatalogEntry(
        id="bw_squat", name="Bodyweight Squat",
        modality=ExerciseModality.STRENGTH, movement_pattern="squat",
    ),
    "bw_burpee": ExerciseCatalogEntry(
        id="bw_burpee", name="Burpee",
        modality=ExerciseModality.CARDIO, movement_pattern="cardio",
    ),
}


def _exercise(exercise_id: str = "bw_squat", sets: int = 3, reps: int | None = 10,
              duration_seconds: int | None = None) -> BlockExercise:
    return BlockExercise(
        id="ex-1",
        exercise_id=exercise_id,
        exercise_name="X",
        sets=sets,
        reps=reps,
        duration_seconds=duration_seconds,
    )


def _block(exercises: list[BlockExercise] | None = None, estimated_minutes: int = 30) -> Block:
    return Block(
        id="b-1",
        type=BlockType.MAIN,
        estimated_minutes=estimated_minutes,
        exercises=exercises if exercises is not None else [_exercise()],
    )


def _session(blocks: list[Block] | None = None) -> Session:
    return Session(id="s-1", date=date(2026, 7, 14), blocks=blocks if blocks is not None else [_block()])


def _workout(*sessions: Session) -> Workout:
    return Workout(id="w-1", user_id="u-1", week_start=date(2026, 7, 14), sessions=list(sessions))


def test_valid_plan_returns_no_errors() -> None:
    assert validate_workout_plan(_workout(_session()), _CATALOG, 30) == []


def test_unknown_exercise_id_is_flagged() -> None:
    session = _session([_block([_exercise("made_up_id")])])
    errors = validate_workout_plan(_workout(session), _CATALOG, 30)

    codes = {e.code for e in errors}
    assert "UNKNOWN_EXERCISE" in codes


def test_empty_session_is_flagged() -> None:
    session = _session([])
    errors = validate_workout_plan(_workout(session), _CATALOG, 30)

    assert any(e.code == "EMPTY_SESSION" for e in errors)


def test_empty_block_is_flagged() -> None:
    session = _session([_block([])])
    errors = validate_workout_plan(_workout(session), _CATALOG, 30)

    assert any(e.code == "EMPTY_BLOCK" for e in errors)


def test_duration_out_of_range_is_flagged() -> None:
    session = _session([_block(estimated_minutes=60)])
    errors = validate_workout_plan(_workout(session), _CATALOG, session_duration_minutes=30)

    assert any(e.code == "DURATION_OUT_OF_RANGE" for e in errors)


def test_duration_within_tolerance_passes() -> None:
    session = _session([_block(estimated_minutes=35)])
    errors = validate_workout_plan(
        _workout(session), _CATALOG, session_duration_minutes=30, duration_tolerance_minutes=10
    )

    assert not any(e.code == "DURATION_OUT_OF_RANGE" for e in errors)


def test_sets_less_than_one_is_flagged() -> None:
    session = _session([_block([_exercise(sets=0)])])
    errors = validate_workout_plan(_workout(session), _CATALOG, 30)

    assert any(e.code == "INVALID_SETS_REPS" for e in errors)


def test_neither_reps_nor_duration_is_flagged() -> None:
    ex = BlockExercise(id="x", exercise_id="bw_squat", exercise_name="X",
                       sets=3, reps=None, duration_seconds=None)
    session = _session([_block([ex])])
    errors = validate_workout_plan(_workout(session), _CATALOG, 30)

    assert any(e.code == "INVALID_SETS_REPS" for e in errors)


def test_duration_seconds_exercise_is_valid() -> None:
    ex = BlockExercise(id="x", exercise_id="bw_burpee", exercise_name="Burpee",
                       sets=3, reps=None, duration_seconds=30)
    session = _session([_block([ex])])
    errors = validate_workout_plan(_workout(session), _CATALOG, 30)

    assert errors == []


def test_multiple_sessions_validated_independently() -> None:
    good = _session()
    bad = _session([_block([_exercise("ghost_id")])])
    errors = validate_workout_plan(_workout(good, bad), _CATALOG, 30)

    assert len(errors) == 1
    assert "/sessions/1/" in errors[0].path
