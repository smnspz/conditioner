from __future__ import annotations

from abc import ABC, abstractmethod

from conditioner.core.domain.workout.constraints import WorkoutConstraints


class ConstraintsRepository(ABC):
    """Port for persisting and retrieving a user's workout constraints."""

    @abstractmethod
    async def save(self, constraints: WorkoutConstraints) -> None:
        """Create or update the stored constraints for a user."""

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> WorkoutConstraints | None:
        """Fetch a user's stored constraints, or None if not found."""
