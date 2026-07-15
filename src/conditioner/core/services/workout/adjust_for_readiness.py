from __future__ import annotations

from copy import deepcopy
from datetime import date

from conditioner.core.domain.readiness.readiness import ReadinessZone
from conditioner.core.domain.workout.workout import Session, Workout

# Load multiplier applied per readiness zone.
_LOAD_FACTOR_BY_ZONE: dict[ReadinessZone, float] = {
    ReadinessZone.PEAK: 1.0,
    ReadinessZone.GOOD: 1.0,
    ReadinessZone.MODERATE: 0.75,
    ReadinessZone.LIGHT: 0.4,
    ReadinessZone.REST: 0.0,
}


def _scale_int(value: int | None, factor: float) -> int | None:
    return None if value is None else round(value * factor)


def _scale_float(value: float | None, factor: float) -> float | None:
    return None if value is None else value * factor


def _adjust_session(session: Session, zone: ReadinessZone) -> Session:
    factor = _LOAD_FACTOR_BY_ZONE[zone]
    adjusted = deepcopy(session)
    if zone is ReadinessZone.REST:
        adjusted.exercises = []
        return adjusted
    for exercise in adjusted.exercises:
        exercise.sets = _scale_int(exercise.sets, factor)
        exercise.reps = _scale_int(exercise.reps, factor)
        exercise.duration_minutes = _scale_float(exercise.duration_minutes, factor)
        exercise.target_load = _scale_float(exercise.target_load, factor)
    return adjusted


def adjust_remaining_sessions(workout: Workout, from_date: date, zone: ReadinessZone) -> Workout:
    """Scale load in a workout's not-yet-completed sessions on/after from_date by readiness zone.

    Completed sessions and sessions before from_date are left untouched.
    """

    adjusted = deepcopy(workout)
    adjusted.sessions = [
        _adjust_session(session, zone)
        if session.date >= from_date and not session.completed
        else session
        for session in adjusted.sessions
    ]
    return adjusted
