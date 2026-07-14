from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class QuestionnaireResponse:
    """A user's subjective daily questionnaire answers.

    Attributes:
        user_id: The user who submitted the response.
        date: The calendar day this response describes.
        fatigue: Perceived fatigue on waking, 0 (fresh) to 10 (exhausted).
        soreness: Muscle soreness/DOMS, 0 (none) to 10 (strong pain).
        stress: Mental/emotional stress, 0 (calm) to 10 (very high).
        sleep_quality: Perceived sleep quality, 0 (terrible) to 10 (excellent).
        is_sick: Whether the user flagged illness, cold, or joint pain.
    """

    user_id: str
    date: date
    fatigue: int
    soreness: int
    stress: int
    sleep_quality: int
    is_sick: bool = False
