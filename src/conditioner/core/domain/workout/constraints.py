from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TrainingGoal(Enum):
    """A user's training objective, used to steer workout generation."""

    MMA_CONDITIONING = "mma_conditioning"


@dataclass
class WorkoutConstraints:
    """A user's constraints for generating and adjusting their weekly workouts.

    Attributes:
        user_id: The user these constraints belong to.
        equipment: The equipment the user has available to train with.
        goal: The user's training objective.
        available_minutes_by_weekday: Minutes available to train on each weekday,
            keyed 0 (Monday) through 6 (Sunday). Missing keys mean no session that day.
    """

    user_id: str
    equipment: list[str]
    goal: TrainingGoal
    available_minutes_by_weekday: dict[int, int] = field(default_factory=dict[int, int])
