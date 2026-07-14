from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from conditioner.core.domain.questionnaire import QuestionnaireResponse


class QuestionnaireRepository(ABC):
    """Port for persisting and retrieving daily questionnaire responses."""

    @abstractmethod
    async def save(self, response: QuestionnaireResponse) -> None:
        """Create or update a user's questionnaire response for a given day."""

    @abstractmethod
    async def get_by_date(self, user_id: str, day: date) -> QuestionnaireResponse | None:
        """Fetch a user's questionnaire response for a single day, or None if not found."""
