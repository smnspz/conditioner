from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class ReadinessZone(Enum):
    """Operational zone a readiness score falls into, on the 0-100 scale."""

    PEAK = "peak"
    GOOD = "good"
    MODERATE = "moderate"
    LIGHT = "light"
    REST = "rest"

    @classmethod
    def from_score(cls, score: int) -> ReadinessZone:
        """Map a 0-100 readiness score to its operational zone."""
        if score >= 80:
            return cls.PEAK
        if score >= 65:
            return cls.GOOD
        if score >= 50:
            return cls.MODERATE
        if score >= 35:
            return cls.LIGHT
        return cls.REST


@dataclass
class ReadinessScore:
    """A user's computed training readiness for a single day.

    Attributes:
        user_id: The user this score belongs to.
        date: The calendar day this score describes.
        score: The final readiness value, 0-100.
        zone: The operational zone the score falls into.
    """

    user_id: str
    date: date
    score: int
    zone: ReadinessZone
