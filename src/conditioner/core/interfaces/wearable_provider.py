from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from conditioner.core.domain.credentials import GoogleCredentials
from conditioner.core.domain.wearable_metrics import WearableDailyMetrics


class WearableDataProvider(ABC):
    """Port for fetching daily objective metrics from a health data provider."""

    @abstractmethod
    async def fetch(
        self,
        user_id: str,
        credentials: GoogleCredentials,
        start: date,
        end: date,
    ) -> list[WearableDailyMetrics]:
        """Fetch daily wearable metrics for user over an inclusive date range."""
