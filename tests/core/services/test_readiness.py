from datetime import date, time

from conditioner.core.domain.questionnaire import QuestionnaireResponse
from conditioner.core.domain.readiness import ReadinessZone
from conditioner.core.domain.wearable_metrics import WearableDailyMetrics
from conditioner.core.services.baseline import (
    Baseline,
    acute_chronic_load_ratio,
    compute_baseline,
    consecutive_training_days,
)
from conditioner.core.services.readiness import (
    compute_readiness,
    normalize_hrv,
    normalize_rhr,
)

_BASELINE = Baseline(
    hrv_rmssd=60.0,
    resting_heart_rate=50.0,
    sleep_onset=time(23, 0),
    wake_time=time(7, 0),
)


def _metrics(**overrides: object) -> WearableDailyMetrics:
    defaults = dict(
        user_id="user-1",
        date=date(2024, 8, 14),
        hrv_rmssd=60.0,
        resting_heart_rate=50.0,
        sleep_duration_hours=8.0,
        sleep_efficiency_pct=92.0,
        sleep_onset=time(23, 0),
        wake_time=time(7, 0),
    )
    defaults.update(overrides)
    return WearableDailyMetrics(**defaults)  # type: ignore[arg-type]


def _questionnaire(**overrides: object) -> QuestionnaireResponse:
    defaults = dict(
        user_id="user-1",
        date=date(2024, 8, 14),
        fatigue=2,
        soreness=2,
        stress=2,
        sleep_quality=8,
    )
    defaults.update(overrides)
    return QuestionnaireResponse(**defaults)  # type: ignore[arg-type]


def test_normalize_hrv_thresholds() -> None:
    assert normalize_hrv(63, 60) == 1.0
    assert normalize_hrv(60, 60) == 0.8
    assert normalize_hrv(56, 60) == 0.6
    assert normalize_hrv(52, 60) == 0.3
    assert normalize_hrv(None, 60) == 0.8


def test_normalize_rhr_thresholds() -> None:
    assert normalize_rhr(47, 50) == 1.0
    assert normalize_rhr(50, 50) == 0.8
    assert normalize_rhr(53, 50) == 0.6
    assert normalize_rhr(57, 50) == 0.3


def test_compute_readiness_ideal_day_is_peak_zone() -> None:
    score = compute_readiness(
        "user-1", _metrics(), _questionnaire(), _BASELINE,
        consecutive_training_days=1, acwr=1.0,
    )

    assert score.zone == ReadinessZone.PEAK
    assert 80 <= score.score <= 100


def test_compute_readiness_sick_flag_applies_penalty() -> None:
    healthy = compute_readiness(
        "user-1", _metrics(), _questionnaire(), _BASELINE,
        consecutive_training_days=1, acwr=1.0,
    )
    sick = compute_readiness(
        "user-1", _metrics(), _questionnaire(is_sick=True), _BASELINE,
        consecutive_training_days=1, acwr=1.0,
    )

    assert sick.score < healthy.score


def test_compute_readiness_consecutive_days_penalty_reduces_score() -> None:
    rested = compute_readiness(
        "user-1", _metrics(), _questionnaire(), _BASELINE,
        consecutive_training_days=1, acwr=1.0,
    )
    fatigued = compute_readiness(
        "user-1", _metrics(), _questionnaire(), _BASELINE,
        consecutive_training_days=10, acwr=1.0,
    )

    assert fatigued.score < rested.score


def test_compute_readiness_high_acwr_reduces_score() -> None:
    normal_load = compute_readiness(
        "user-1", _metrics(), _questionnaire(), _BASELINE,
        consecutive_training_days=1, acwr=1.0,
    )
    high_load = compute_readiness(
        "user-1", _metrics(), _questionnaire(), _BASELINE,
        consecutive_training_days=1, acwr=2.5,
    )

    assert high_load.score < normal_load.score


def test_compute_baseline_averages_recent_history() -> None:
    history = [_metrics(date=date(2024, 8, d), hrv_rmssd=float(50 + d)) for d in range(1, 8)]

    baseline = compute_baseline(history)

    assert baseline.hrv_rmssd == sum(50 + d for d in range(1, 8)) / 7


def test_consecutive_training_days_stops_at_rest_day() -> None:
    history = [
        _metrics(date=date(2024, 8, 1), training_load=50.0),
        _metrics(date=date(2024, 8, 2), training_load=0.0),
        _metrics(date=date(2024, 8, 3), training_load=40.0),
        _metrics(date=date(2024, 8, 4), training_load=45.0),
    ]

    assert consecutive_training_days(history) == 2


def test_acute_chronic_load_ratio_requires_chronic_history() -> None:
    short_history = [_metrics(date=date(2024, 8, d), training_load=50.0) for d in range(1, 5)]

    assert acute_chronic_load_ratio(short_history) is None
