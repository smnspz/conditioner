from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class ExerciseModality(Enum):
    """Broad category of an exercise, used to reason about load and adjustments."""

    STRENGTH = "strength"
    CARDIO = "cardio"
    MOBILITY = "mobility"


@dataclass
class Exercise:
    """A single prescribed exercise within a session.

    Attributes:
        name: Exercise name (e.g. "Back squat").
        modality: Broad category of the exercise.
        sets: Number of sets prescribed.
        reps: Number of reps per set, if rep-based.
        duration_minutes: Duration, if time-based rather than rep-based.
        target_load: Target intensity/load (e.g. % of 1RM, or pace), provider-specific units.
    """

    name: str
    modality: ExerciseModality
    sets: int | None = None
    reps: int | None = None
    duration_minutes: float | None = None
    target_load: float | None = None


@dataclass
class Session:
    """A single training session scheduled for a specific day.

    Attributes:
        date: The calendar day this session is scheduled for.
        exercises: The exercises prescribed for this session.
        completed: Whether the user has completed this session.
    """

    date: date
    exercises: list[Exercise] = field(default_factory=list)
    completed: bool = False


@dataclass
class Workout:
    """A generated weekly workout plan for a user.

    Attributes:
        id: Unique identifier.
        user_id: The user this plan belongs to.
        week_start: The calendar day the week begins.
        sessions: The sessions scheduled for the week.
    """

    id: str
    user_id: str
    week_start: date
    sessions: list[Session] = field(default_factory=list)
