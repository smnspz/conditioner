from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class FitnessLevel:
    """A user's self-reported fitness level for a given week.

    Surveyed once per week and used alongside the daily readiness score to calibrate
    exercise difficulty, complexity, and progression for that week's plan.

    Attributes:
        user_id: The user this assessment belongs to.
        week_start: The Monday starting the week this level was assessed for.
        score: Self-reported fitness on a 1–10 scale (1 = very unfit, 10 = peak athlete).
    """

    user_id: str
    week_start: date
    score: int
