from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from conditioner.core.domain.fitness.fitness_level import FitnessLevel


class FitnessLevelRepository(ABC):
    """Port for persisting and retrieving weekly fitness level assessments."""

    @abstractmethod
    async def save(self, fitness_level: FitnessLevel) -> None:
        """Create or update a user's fitness level for a given week."""

    @abstractmethod
    async def get_by_week(self, user_id: str, week_start: date) -> FitnessLevel | None:
        """Fetch a user's fitness level for a specific week, or None if not assessed yet."""
