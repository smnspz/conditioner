from __future__ import annotations

from copy import deepcopy
from datetime import date

from conditioner.core.domain.readiness.readiness import ReadinessZone
from conditioner.core.domain.workout.workout import Block, BlockType, Session, Workout

# Load multiplier applied per readiness zone.
_LOAD_FACTOR_BY_ZONE: dict[ReadinessZone, float] = {
    ReadinessZone.PEAK: 1.0,
    ReadinessZone.GOOD: 1.0,
    ReadinessZone.MODERATE: 0.75,
    ReadinessZone.LIGHT: 0.4,
    ReadinessZone.REST: 0.0,
}

# Block types that carry training load (scaled or dropped on low readiness).
_LOAD_BLOCK_TYPES = {BlockType.MAIN, BlockType.FINISHER}


def _scale_int(value: int | None, factor: float) -> int | None:
    return None if value is None else max(1, round(value * factor))


def _adjust_block(block: Block, factor: float) -> Block:
    adjusted = deepcopy(block)
    for exercise in adjusted.exercises:
        exercise.sets = _scale_int(exercise.sets, factor)
        exercise.reps = _scale_int(exercise.reps, factor)
        if exercise.duration_seconds is not None:
            exercise.duration_seconds = _scale_int(exercise.duration_seconds, factor)
    return adjusted


def _adjust_session(session: Session, zone: ReadinessZone) -> Session:
    factor = _LOAD_FACTOR_BY_ZONE[zone]
    adjusted = deepcopy(session)
    if zone is ReadinessZone.REST:
        # Keep only warmup/cooldown; drop load-bearing blocks
        adjusted.blocks = [b for b in adjusted.blocks if b.type not in _LOAD_BLOCK_TYPES]
        return adjusted
    adjusted.blocks = [
        _adjust_block(b, factor) if b.type in _LOAD_BLOCK_TYPES else b
        for b in adjusted.blocks
    ]
    return adjusted


def adjust_remaining_sessions(workout: Workout, from_date: date, zone: ReadinessZone) -> Workout:
    """Scale load in a workout's not-yet-completed sessions on/after from_date by readiness zone.

    MAIN and FINISHER blocks are scaled; WARMUP/COOLDOWN blocks are left untouched.
    On REST zone, MAIN and FINISHER blocks are dropped entirely.
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
