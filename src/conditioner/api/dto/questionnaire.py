from datetime import date as Date
from typing import Annotated

from pydantic import BaseModel, Field


class QuestionnaireRequest(BaseModel):
    """Daily subjective questionnaire submission.

    Attributes:
        date: The day this response describes; defaults to today.
        fatigue: Perceived fatigue on waking, 0 (fresh) to 10 (exhausted).
        soreness: Muscle soreness/DOMS, 0 (none) to 10 (strong pain).
        stress: Mental/emotional stress, 0 (calm) to 10 (very high).
        sleep_quality: Perceived sleep quality, 0 (terrible) to 10 (excellent).
        is_sick: Whether the user flagged illness, cold, or joint pain.
    """

    date: Date = Field(default_factory=Date.today)
    fatigue: Annotated[int, Field(ge=0, le=10)]
    soreness: Annotated[int, Field(ge=0, le=10)]
    stress: Annotated[int, Field(ge=0, le=10)]
    sleep_quality: Annotated[int, Field(ge=0, le=10)]
    is_sick: bool = False


class QuestionnaireResponseOut(BaseModel):
    """Serialized questionnaire response returned to the client."""

    date: Date
    fatigue: int
    soreness: int
    stress: int
    sleep_quality: int
    is_sick: bool
