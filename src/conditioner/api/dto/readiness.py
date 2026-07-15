from __future__ import annotations

from datetime import date as Date

from pydantic import BaseModel

from conditioner.core.domain.readiness.readiness import ReadinessScore


class ReadinessScoreOut(BaseModel):
    """Serialized readiness score returned to the client."""

    date: Date
    score: int
    zone: str

    @classmethod
    def from_domain(cls, readiness: ReadinessScore) -> ReadinessScoreOut:
        """Build from a domain ReadinessScore."""

        return cls(date=readiness.date, score=readiness.score, zone=readiness.zone.value)
