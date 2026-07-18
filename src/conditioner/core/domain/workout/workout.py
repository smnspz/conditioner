from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class ExerciseModality(Enum):
    """Broad category of an exercise, used to reason about load and adjustments."""

    STRENGTH = "strength"
    CARDIO = "cardio"
    MOBILITY = "mobility"


class BlockType(Enum):
    """Phase of a training session a block belongs to."""

    WARMUP = "warmup"
    MAIN = "main"
    FINISHER = "finisher"
    COOLDOWN = "cooldown"


@dataclass
class BlockExercise:
    """A single prescribed exercise within a block.

    Attributes:
        id: Unique identifier assigned at generation time.
        exercise_id: Stable catalog ID (e.g. 'bw_push_up').
        exercise_name: Display name denormalized from the catalog at generation time.
        sets: Number of sets prescribed.
        reps: Reps per set; None for time-based exercises.
        duration_seconds: Duration per set; None for rep-based exercises.
        rest_seconds: Rest between sets in seconds.
        intensity_cue: Qualitative intensity instruction (e.g. 'RPE 7', 'controlled tempo').
        notes: Optional exercise-specific note.
    """

    id: str
    exercise_id: str
    exercise_name: str
    sets: int = 1
    reps: int | None = None
    duration_seconds: int | None = None
    rest_seconds: int = 60
    intensity_cue: str = ""
    notes: str = ""


@dataclass
class Block:
    """A phase segment of a training session (e.g. warmup, main work, cooldown).

    Attributes:
        id: Unique identifier.
        type: Phase classification (warmup / main / finisher / cooldown).
        estimated_minutes: Expected duration of the block in minutes.
        exercises: Exercises prescribed within this block.
    """

    id: str
    type: BlockType
    estimated_minutes: int
    exercises: list[BlockExercise] = field(default_factory=list)


@dataclass
class Session:
    """A single training session scheduled for a specific day.

    Attributes:
        id: Unique identifier.
        date: The calendar day this session is scheduled for.
        blocks: Ordered list of blocks making up the session.
        completed: Whether the user has completed this session.
    """

    id: str
    date: date
    blocks: list[Block] = field(default_factory=list)
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
