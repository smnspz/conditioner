from datetime import date

from conditioner.core.domain.readiness.readiness import ReadinessZone
from conditioner.core.domain.workout.workout import Block, BlockExercise, BlockType, Session, Workout
from conditioner.core.services.workout.adjust_for_readiness import adjust_remaining_sessions

_TODAY = date(2026, 7, 15)


def _workout(*sessions: Session) -> Workout:
    return Workout(id="workout-1", user_id="user-1", week_start=_TODAY, sessions=list(sessions))


def _main_block(sets: int = 4, reps: int = 10) -> Block:
    return Block(
        id="block-main",
        type=BlockType.MAIN,
        estimated_minutes=30,
        exercises=[
            BlockExercise(
                id="ex-1",
                exercise_id="bw_squat",
                exercise_name="Bodyweight Squat",
                sets=sets,
                reps=reps,
            )
        ],
    )


def _warmup_block() -> Block:
    return Block(
        id="block-warmup",
        type=BlockType.WARMUP,
        estimated_minutes=5,
        exercises=[
            BlockExercise(
                id="ex-w",
                exercise_id="mob_hip_circle",
                exercise_name="Hip Circle",
                sets=1,
                duration_seconds=60,
            )
        ],
    )


def _session(day: date, *, completed: bool = False, sets: int = 4) -> Session:
    return Session(
        id=f"session-{day}",
        date=day,
        completed=completed,
        blocks=[_main_block(sets=sets)],
    )


def test_peak_and_good_zones_leave_load_unchanged() -> None:
    workout = _workout(_session(_TODAY))

    for zone in (ReadinessZone.PEAK, ReadinessZone.GOOD):
        adjusted = adjust_remaining_sessions(workout, _TODAY, zone)
        assert adjusted.sessions[0].blocks[0].exercises[0].sets == 4


def test_moderate_zone_scales_sets_down() -> None:
    adjusted = adjust_remaining_sessions(_workout(_session(_TODAY)), _TODAY, ReadinessZone.MODERATE)

    # 4 * 0.75 = 3
    assert adjusted.sessions[0].blocks[0].exercises[0].sets == 3


def test_rest_zone_drops_main_blocks() -> None:
    session = Session(
        id="s", date=_TODAY, blocks=[_warmup_block(), _main_block()]
    )
    adjusted = adjust_remaining_sessions(_workout(session), _TODAY, ReadinessZone.REST)

    remaining_types = [b.type for b in adjusted.sessions[0].blocks]
    assert BlockType.MAIN not in remaining_types
    assert BlockType.WARMUP in remaining_types


def test_warmup_blocks_are_untouched_on_scaling() -> None:
    session = Session(
        id="s", date=_TODAY, blocks=[_warmup_block(), _main_block(sets=4)]
    )
    adjusted = adjust_remaining_sessions(_workout(session), _TODAY, ReadinessZone.MODERATE)

    warmup = next(b for b in adjusted.sessions[0].blocks if b.type == BlockType.WARMUP)
    assert warmup.exercises[0].sets == 1


def test_completed_sessions_are_untouched() -> None:
    completed = _session(_TODAY, completed=True)
    workout = _workout(completed)

    adjusted = adjust_remaining_sessions(workout, _TODAY, ReadinessZone.REST)

    assert adjusted.sessions[0].blocks[0].exercises[0].sets == 4


def test_sessions_before_from_date_are_untouched() -> None:
    past = _session(date(2026, 7, 13))
    workout = _workout(past)

    adjusted = adjust_remaining_sessions(workout, _TODAY, ReadinessZone.REST)

    assert adjusted.sessions[0].blocks[0].exercises[0].sets == 4
