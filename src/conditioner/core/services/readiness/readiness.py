from __future__ import annotations

from datetime import time

from conditioner.core.domain.questionnaire.questionnaire import QuestionnaireResponse
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.wearables.wearable_metrics import WearableDailyMetrics
from conditioner.core.services.readiness.baseline import Baseline

# Neutral sub-score used when a metric is missing and can't be normalized
NEUTRAL_SUB_SCORE = 0.8

SLEEP_TARGET_HOURS = 8.0
SLEEP_DURATION_FLOOR_HOURS = 5.0
SLEEP_DURATION_FLOOR_SCORE = 0.3

CONSECUTIVE_DAYS_PENALTY_THRESHOLD = 3
CONSECUTIVE_DAYS_PENALTY_PER_DAY = 0.02
CONSECUTIVE_DAYS_PENALTY_CAP = 0.15

ACWR_HIGH_THRESHOLD = 1.5
ACWR_VERY_HIGH_THRESHOLD = 2.0
ACWR_PENALTY_HIGH = 0.05
ACWR_PENALTY_VERY_HIGH = 0.10

SICK_PENALTY = 0.20


def normalize_hrv(today: float | None, baseline: float | None) -> float:
    """Normalize today's HRV against baseline to a 0-1 sub-score (higher is better)."""

    if today is None or not baseline:
        return NEUTRAL_SUB_SCORE

    # Set relative deviation from baseline
    delta = (today - baseline) / baseline

    if delta >= 0.05:
        return 1.0
    if delta >= -0.05:
        return 0.8
    if delta >= -0.10:
        return 0.6
    return 0.3


def normalize_rhr(today: float | None, baseline: float | None) -> float:
    """Normalize today's resting heart rate against baseline (lower is better)."""

    if today is None or not baseline:
        return NEUTRAL_SUB_SCORE

    # Set relative deviation from baseline
    delta = (today - baseline) / baseline

    if delta <= -0.05:
        return 1.0
    if delta <= 0.05:
        return 0.8
    if delta <= 0.10:
        return 0.6
    return 0.3


def normalize_sleep(metrics: WearableDailyMetrics, baseline: Baseline) -> float:
    """Normalize sleep duration, efficiency, and schedule regularity to a 0-1 sub-score."""

    return (
        0.5 * _sleep_duration_score(metrics.sleep_duration_hours)
        + 0.3 * _sleep_efficiency_score(metrics.sleep_efficiency_pct)
        + 0.2 * _sleep_regularity_score(metrics, baseline)
    )


def _sleep_duration_score(hours: float | None) -> float:
    if hours is None:
        return NEUTRAL_SUB_SCORE

    # Set duration score relative to target, floored when severely short
    score = min(1.0, hours / SLEEP_TARGET_HOURS)
    if hours < SLEEP_DURATION_FLOOR_HOURS:
        score = max(score, SLEEP_DURATION_FLOOR_SCORE)
    return score


def _sleep_efficiency_score(efficiency_pct: float | None) -> float:
    if efficiency_pct is None:
        return NEUTRAL_SUB_SCORE
    if efficiency_pct > 90:
        return 1.0
    if efficiency_pct >= 85:
        return 0.8
    if efficiency_pct >= 80:
        return 0.6
    return 0.3


def _sleep_regularity_score(metrics: WearableDailyMetrics, baseline: Baseline) -> float:
    deviations = [
        d
        for d in (
            _minutes_deviation(metrics.sleep_onset, baseline.sleep_onset),
            _minutes_deviation(metrics.wake_time, baseline.wake_time),
        )
        if d is not None
    ]
    if not deviations:
        return NEUTRAL_SUB_SCORE

    # Set worst-case deviation between sleep onset and wake time
    deviation = max(deviations)
    if deviation <= 60:
        return 1.0
    if deviation <= 120:
        return 0.6
    return 0.3


def _minutes_deviation(today: time | None, baseline: time | None) -> float | None:
    if today is None or baseline is None:
        return None

    # Set absolute deviation in minutes, wrapped around the 24h clock
    today_minutes = today.hour * 60 + today.minute
    baseline_minutes = baseline.hour * 60 + baseline.minute
    diff = abs(today_minutes - baseline_minutes)
    return min(diff, 24 * 60 - diff)


def normalize_wellbeing(questionnaire: QuestionnaireResponse) -> float:
    """Aggregate the subjective questionnaire answers into a 0-1 wellbeing sub-score."""

    # Set each subjective sub-score, 0 = worst, 1 = best
    s_fatigue = 1 - questionnaire.fatigue / 10
    s_soreness = 1 - questionnaire.soreness / 10
    s_stress = 1 - questionnaire.stress / 10
    s_sleep_subjective = questionnaire.sleep_quality / 10

    # Return weighted subjective wellbeing
    return 0.4 * s_fatigue + 0.3 * s_soreness + 0.2 * s_stress + 0.1 * s_sleep_subjective


def _consecutive_days_penalty(consecutive_training_days: int) -> float:
    excess_days = max(0, consecutive_training_days - CONSECUTIVE_DAYS_PENALTY_THRESHOLD)
    return min(CONSECUTIVE_DAYS_PENALTY_CAP, excess_days * CONSECUTIVE_DAYS_PENALTY_PER_DAY)


def _load_penalty(acwr: float | None) -> float:
    if acwr is None or acwr <= ACWR_HIGH_THRESHOLD:
        return 0.0
    if acwr <= ACWR_VERY_HIGH_THRESHOLD:
        return ACWR_PENALTY_HIGH
    return ACWR_PENALTY_VERY_HIGH


def compute_readiness(
    user_id: str,
    metrics: WearableDailyMetrics,
    questionnaire: QuestionnaireResponse,
    baseline: Baseline,
    consecutive_training_days: int,
    acwr: float | None,
) -> ReadinessScore:
    """Compute a user's daily training readiness score per the aggregation formula."""

    # Get each metric's normalized sub-score
    s_hrv = normalize_hrv(metrics.hrv_rmssd, baseline.hrv_rmssd)
    s_rhr = normalize_rhr(metrics.resting_heart_rate, baseline.resting_heart_rate)
    s_sleep = normalize_sleep(metrics, baseline)
    s_wellbeing = normalize_wellbeing(questionnaire)
    s_soreness = 1 - questionnaire.soreness / 10

    # Set base readiness as the weighted average of all sub-scores
    base = 0.30 * s_hrv + 0.25 * s_sleep + 0.20 * s_wellbeing + 0.15 * s_soreness + 0.10 * s_rhr

    # Set load penalties for accumulated fatigue
    penalty_days = _consecutive_days_penalty(consecutive_training_days)
    penalty_load = _load_penalty(acwr)

    # Set final readiness fraction, floored at 0
    fraction = max(0.0, base - penalty_days - penalty_load)
    if questionnaire.is_sick:
        fraction = max(0.0, fraction - SICK_PENALTY)

    # Set scaled 0-100 score
    score = round(100 * fraction)

    # Return computed readiness score
    return ReadinessScore(
        user_id=user_id,
        date=metrics.date,
        score=score,
        zone=ReadinessZone.from_score(score),
    )
