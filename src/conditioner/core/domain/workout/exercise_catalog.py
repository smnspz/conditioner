from __future__ import annotations

from dataclasses import dataclass, field

from conditioner.core.domain.workout.workout import ExerciseModality


@dataclass
class ExerciseCatalogEntry:
    """A single entry in the exercise catalog — a backend-controlled, named movement.

    Exercises are pre-seeded and never authored at runtime. The AI must pick exercise_id
    values from the filtered catalog; it cannot invent its own names or gear mappings.

    Attributes:
        id: Stable slug, e.g. 'resistance_band_row'. Never changes after seeding.
        name: Human-readable display name, e.g. 'Resistance Band Row'.
        modality: Broad category — strength, cardio, or mobility.
        required_gear: Equipment IDs that must be in the user's kit for this exercise.
            Empty list means the exercise is bodyweight-only (no gear required).
        optional_gear: Equipment IDs that can enhance the exercise but are not required.
        difficulty: Skill/intensity tier — 1 (beginner), 2 (intermediate), 3 (advanced).
        primary_muscles: Muscle groups targeted, e.g. ['lats', 'biceps'].
        movement_pattern: Canonical movement category for session-variety planning.
            One of: push, pull, hinge, squat, carry, core, cardio, mobility.
        tags: Additional descriptors, e.g. ['compound', 'explosive', 'upper_body'].
    """

    id: str
    name: str
    modality: ExerciseModality
    required_gear: list[str] = field(default_factory=list)
    optional_gear: list[str] = field(default_factory=list)
    difficulty: int = 1
    primary_muscles: list[str] = field(default_factory=list)
    movement_pattern: str = ""
    tags: list[str] = field(default_factory=list)
