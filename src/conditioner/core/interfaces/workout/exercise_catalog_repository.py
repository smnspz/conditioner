from __future__ import annotations

from abc import ABC, abstractmethod

from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry


class ExerciseCatalogRepository(ABC):
    """Read-only port for the exercise catalog.

    The catalog is seeded by migrations and never written to at runtime.
    """

    @abstractmethod
    async def list_all(self) -> list[ExerciseCatalogEntry]:
        """Return all catalog entries ordered by id."""

    @abstractmethod
    async def filter_by_gear(self, available_gear: list[str]) -> list[ExerciseCatalogEntry]:
        """Return entries whose required_gear is a subset of available_gear plus bodyweight.

        An exercise with an empty required_gear list is always included (bodyweight-only).
        """

    @abstractmethod
    async def get_by_ids(self, ids: list[str]) -> list[ExerciseCatalogEntry]:
        """Return catalog entries matching the given ids."""
