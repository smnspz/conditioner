from __future__ import annotations

import logging
from datetime import date, timedelta
from uuid import uuid4

from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.workout.constraints import WorkoutConstraints
from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry
from conditioner.core.domain.workout.workout import Block, BlockExercise, BlockType, Session, Workout

logger = logging.getLogger(__name__)

# Movement patterns that form the backbone of a well-rounded session.
_PRIORITY_PATTERNS = ["push", "pull", "hinge", "squat", "core", "cardio"]


def _pick_exercises(
    catalog: list[ExerciseCatalogEntry],
    max_difficulty: int,
    count: int,
) -> list[ExerciseCatalogEntry]:
    """Select up to count exercises covering diverse movement patterns, filtered by difficulty."""

    eligible = [e for e in catalog if e.movement_pattern != "mobility" and e.difficulty <= max_difficulty]
    eligible.sort(key=lambda e: (e.id,))

    seen_patterns: set[str] = set()
    picked: list[ExerciseCatalogEntry] = []

    # First pass: one exercise per priority pattern
    for pattern in _PRIORITY_PATTERNS:
        if len(picked) >= count:
            break
        for entry in eligible:
            if entry.movement_pattern == pattern and pattern not in seen_patterns:
                picked.append(entry)
                seen_patterns.add(pattern)
                break

    # Second pass: fill remaining slots from remaining eligible exercises
    for entry in eligible:
        if len(picked) >= count:
            break
        if entry not in picked:
            picked.append(entry)

    return picked[:count]


def build_fallback_workout(
    user_id: str,
    week_start: date,
    constraints: WorkoutConstraints,
    fitness_level: FitnessLevel,
    catalog_entries: list[ExerciseCatalogEntry],
) -> Workout:
    """Build a deterministic fallback workout when AI generation fails.

    Selects exercises sorted by id for stability. Targets 3 sessions covering
    different movement pattern groupings. One template per fitness tier:
    - Beginner (1–3): 3 sets x 8 reps, 3 exercises per session.
    - Intermediate (4–6): 3 sets x 10 reps, 4 exercises per session.
    - Advanced (7–10): 4 sets x 12 reps, 5 exercises per session.
    """

    logger.warning("generation.fallback_triggered user=%s week=%s", user_id, week_start)

    score = fitness_level.score
    if score <= 3:
        max_difficulty, sets, reps, ex_per_session = 1, 3, 8, 3
    elif score <= 6:
        max_difficulty, sets, reps, ex_per_session = 2, 3, 10, 4
    else:
        max_difficulty, sets, reps, ex_per_session = 3, 4, 12, 5

    # Pick exercises for the week, cycling through different ones per session
    all_exercises = _pick_exercises(catalog_entries, max_difficulty, ex_per_session * 3)

    sessions: list[Session] = []
    scheduled_days = sorted(
        day for day, minutes in constraints.available_minutes_by_weekday.items() if minutes > 0
    )[:3]

    for i, day_offset in enumerate(scheduled_days):
        # Rotate exercise slice per session
        start = (i * ex_per_session) % max(1, len(all_exercises))
        slice_ = (all_exercises * 2)[start : start + ex_per_session]

        exercises = [
            BlockExercise(
                id=str(uuid4()),
                exercise_id=e.id,
                exercise_name=e.name,
                sets=sets,
                reps=reps,
                rest_seconds=60,
                intensity_cue="Controlled tempo",
            )
            for e in slice_
        ]
        session_minutes = constraints.available_minutes_by_weekday.get(day_offset, 30)
        sessions.append(
            Session(
                id=str(uuid4()),
                date=week_start + timedelta(days=day_offset),
                blocks=[
                    Block(
                        id=str(uuid4()),
                        type=BlockType.MAIN,
                        estimated_minutes=session_minutes,
                        exercises=exercises,
                    )
                ],
            )
        )

    # Return the deterministic fallback workout
    return Workout(
        id=str(uuid4()),
        user_id=user_id,
        week_start=week_start,
        sessions=sessions,
    )
