from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time


@dataclass
class WearableDailyMetrics:
    """Objective tracker data for a single user-day, as ingested from a wearable provider.

    Attributes:
        user_id: The user these metrics belong to.
        date: The calendar day these metrics describe.
        hrv_rmssd: Nightly heart rate variability (RMSSD), in milliseconds.
        resting_heart_rate: Morning resting heart rate, in beats per minute.
        sleep_duration_hours: Total sleep duration, in hours.
        sleep_efficiency_pct: Percentage of time in bed spent asleep.
        sleep_onset: Time the user fell asleep.
        wake_time: Time the user woke up.
        waso_minutes: Total minutes awake after sleep onset.
        training_load: Daily training load (e.g. TRIMP).
        steps: Total steps taken.
        alcohol_flag: Whether alcohol intake was logged for the day.
        late_eating_flag: Whether late-evening eating was logged for the day.
    """

    user_id: str
    date: date
    hrv_rmssd: float | None = None
    resting_heart_rate: float | None = None
    sleep_duration_hours: float | None = None
    sleep_efficiency_pct: float | None = None
    sleep_onset: time | None = None
    wake_time: time | None = None
    waso_minutes: float | None = None
    training_load: float | None = None
    steps: int | None = None
    alcohol_flag: bool = False
    late_eating_flag: bool = False
