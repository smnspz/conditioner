from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from conditioner.core.domain.workout.workout import Workout


class WorkoutRepository(ABC):
    """Port for persisting and retrieving weekly workout plans."""

    @abstractmethod
    async def save(self, workout: Workout) -> None:
        """Create or update a workout plan, replacing its sessions and exercises."""

    @abstractmethod
    async def get_by_id(self, workout_id: str) -> Workout | None:
        """Fetch a workout plan by id, or None if not found."""

    @abstractmethod
    async def get_by_week(self, user_id: str, week_start: date) -> Workout | None:
        """Fetch a user's workout plan for the week starting on the given day."""
