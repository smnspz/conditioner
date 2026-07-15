from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import time

from conditioner.core.domain.wearable_metrics import WearableDailyMetrics

BASELINE_WINDOW_DAYS = 14
ACUTE_LOAD_WINDOW_DAYS = 7
CHRONIC_LOAD_WINDOW_DAYS = 28


@dataclass
class Baseline:
    """A user's rolling personal baseline, used to normalize today's metrics.

    Attributes:
        hrv_rmssd: Rolling average nightly HRV (RMSSD), in milliseconds.
        resting_heart_rate: Rolling average morning resting heart rate, in bpm.
        sleep_onset: Rolling average sleep onset time.
        wake_time: Rolling average wake time.
    """

    hrv_rmssd: float | None
    resting_heart_rate: float | None
    sleep_onset: time | None
    wake_time: time | None


def compute_baseline(
    history: list[WearableDailyMetrics], window_days: int = BASELINE_WINDOW_DAYS
) -> Baseline:
    """Compute a rolling personal baseline from a user's most recent metrics history.

    history is expected ordered oldest-to-newest; only the trailing window_days
    entries are used.
    """

    # Get trailing window of metrics
    window = history[-window_days:]

    # Return rolling averages for each baseline component
    return Baseline(
        hrv_rmssd=_average(m.hrv_rmssd for m in window),
        resting_heart_rate=_average(m.resting_heart_rate for m in window),
        sleep_onset=_average_time(m.sleep_onset for m in window),
        wake_time=_average_time(m.wake_time for m in window),
    )


def consecutive_training_days(history: list[WearableDailyMetrics]) -> int:
    """Count trailing consecutive days (most recent first) with a positive training load.

    history is expected ordered oldest-to-newest.
    """

    # Set running count of consecutive training days
    count = 0
    for metrics in reversed(history):
        if not metrics.training_load or metrics.training_load <= 0:
            break
        count += 1

    # Return consecutive training day count
    return count


def acute_chronic_load_ratio(history: list[WearableDailyMetrics]) -> float | None:
    """Compute the acute:chronic training load ratio (ACWR) from recent history.

    Acute load is the last 7 days' average; chronic load is the last 28 days'
    average. history is expected ordered oldest-to-newest. Returns None when
    there isn't enough data to compute a chronic baseline.
    """

    if len(history) < CHRONIC_LOAD_WINDOW_DAYS:
        return None

    # Get acute (7-day) and chronic (28-day) average loads
    acute = _average(m.training_load for m in history[-ACUTE_LOAD_WINDOW_DAYS:])
    chronic = _average(m.training_load for m in history[-CHRONIC_LOAD_WINDOW_DAYS:])
    if acute is None or not chronic:
        return None

    # Return acute:chronic ratio
    return acute / chronic


def _average(values: Iterable[float | None]) -> float | None:
    """Average the non-None values in an iterable of floats, or None if none present."""

    # Set non-None values collected from the iterable
    present = [v for v in values if v is not None]

    # Return average, or None if no data was available
    return sum(present) / len(present) if present else None


def _average_time(values: Iterable[time | None]) -> time | None:
    """Average the non-None values in an iterable of times, or None if none present."""

    # Set non-None minute-of-day values collected from the iterable
    present = [v.hour * 60 + v.minute for v in values if v is not None]
    if not present:
        return None

    # Set average minute-of-day, wrapped to a 24h clock
    avg_minutes = round(sum(present) / len(present)) % (24 * 60)

    # Return averaged time
    return time(hour=avg_minutes // 60, minute=avg_minutes % 60)
