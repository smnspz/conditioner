from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from conditioner.core.domain.wearable_metrics import WearableDailyMetrics


class MetricsRepository(ABC):
    """Port for persisting and retrieving objective wearable metrics."""

    @abstractmethod
    async def save(self, metrics: WearableDailyMetrics) -> None:
        """Create or update a user's metrics for a given day."""

    @abstractmethod
    async def get_by_date(self, user_id: str, day: date) -> WearableDailyMetrics | None:
        """Fetch a user's metrics for a single day, or None if not found."""

    @abstractmethod
    async def get_range(
        self, user_id: str, start: date, end: date
    ) -> list[WearableDailyMetrics]:
        """Fetch a user's metrics for an inclusive date range, ordered by date."""
