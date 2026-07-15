from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Equipment:
    """A single piece of gear a user can select as available equipment.

    Attributes:
        id: Stable identifier, referenced by WorkoutConstraints.equipment.
        name: Human-readable display name.
    """

    id: str
    name: str
