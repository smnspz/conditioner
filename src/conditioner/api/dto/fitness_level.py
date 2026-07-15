from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field

from conditioner.core.domain.fitness.fitness_level import FitnessLevel


class FitnessLevelRequest(BaseModel):
    """Weekly fitness level submission.

    Attributes:
        score: Self-reported fitness on a 1–10 scale (1 = very unfit, 10 = peak athlete).
    """

    score: Annotated[int, Field(ge=1, le=10)]

    def to_domain(self, user_id: str, week_start: date) -> FitnessLevel:
        """Build a domain FitnessLevel for the given user and week."""

        return FitnessLevel(user_id=user_id, week_start=week_start, score=self.score)


class FitnessLevelOut(BaseModel):
    """Serialized fitness level returned to the client."""

    week_start: date
    score: int

    @classmethod
    def from_domain(cls, fitness_level: FitnessLevel) -> FitnessLevelOut:
        """Build from a domain FitnessLevel."""

        # Return serialized fitness level
        return cls(week_start=fitness_level.week_start, score=fitness_level.score)
