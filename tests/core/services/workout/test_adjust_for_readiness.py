from datetime import date

from conditioner.core.domain.readiness.readiness import ReadinessZone
from conditioner.core.domain.workout.workout import Exercise, ExerciseModality, Session, Workout
from conditioner.core.services.workout.adjust_for_readiness import adjust_remaining_sessions

_TODAY = date(2026, 7, 15)


def _workout(*sessions: Session) -> Workout:
    return Workout(id="workout-1", user_id="user-1", week_start=_TODAY, sessions=list(sessions))


def _session(day: date, *, completed: bool = False, sets: int = 4) -> Session:
    return Session(
        id=f"session-{day}",
        date=day,
        completed=completed,
        exercises=[
            Exercise(
                id="exercise-1",
                name="Back squat",
                modality=ExerciseModality.STRENGTH,
                sets=sets,
                reps=10,
                duration_minutes=None,
                target_load=100.0,
            )
        ],
    )


def test_peak_and_good_zones_leave_load_unchanged() -> None:
    workout = _workout(_session(_TODAY))

    for zone in (ReadinessZone.PEAK, ReadinessZone.GOOD):
        adjusted = adjust_remaining_sessions(workout, _TODAY, zone)
        assert adjusted.sessions[0].exercises[0].sets == 4
        assert adjusted.sessions[0].exercises[0].target_load == 100.0


def test_moderate_zone_scales_load_down() -> None:
    adjusted = adjust_remaining_sessions(_workout(_session(_TODAY)), _TODAY, ReadinessZone.MODERATE)

    assert adjusted.sessions[0].exercises[0].sets == 3
    assert adjusted.sessions[0].exercises[0].target_load == 75.0


def test_rest_zone_clears_exercises() -> None:
    adjusted = adjust_remaining_sessions(_workout(_session(_TODAY)), _TODAY, ReadinessZone.REST)

    assert adjusted.sessions[0].exercises == []


def test_completed_sessions_are_untouched() -> None:
    completed = _session(_TODAY, completed=True)
    workout = _workout(completed)

    adjusted = adjust_remaining_sessions(workout, _TODAY, ReadinessZone.REST)

    assert adjusted.sessions[0].exercises[0].sets == 4


def test_sessions_before_from_date_are_untouched() -> None:
    past = _session(date(2026, 7, 13))
    workout = _workout(past)

    adjusted = adjust_remaining_sessions(workout, _TODAY, ReadinessZone.REST)

    assert adjusted.sessions[0].exercises[0].sets == 4
