from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from conditioner.core.domain.readiness import ReadinessScore


class ReadinessRepository(ABC):
    """Port for persisting and retrieving computed readiness scores."""

    @abstractmethod
    async def save(self, score: ReadinessScore) -> None:
        """Create or update a user's readiness score for a given day."""

    @abstractmethod
    async def get_by_date(self, user_id: str, day: date) -> ReadinessScore | None:
        """Fetch a user's readiness score for a single day, or None if not found."""

    @abstractmethod
    async def get_range(self, user_id: str, start: date, end: date) -> list[ReadinessScore]:
        """Fetch a user's readiness scores for an inclusive date range, ordered by date."""
