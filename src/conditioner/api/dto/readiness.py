from datetime import date as Date

from pydantic import BaseModel


class ReadinessScoreOut(BaseModel):
    """Serialized readiness score returned to the client."""

    date: Date
    score: int
    zone: str
