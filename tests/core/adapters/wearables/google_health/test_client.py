from datetime import date

import pytest

from conditioner.core.adapters.wearables.google_health.client import _build_metrics


@pytest.fixture
def sample_points():
    """One day's worth of raw API data points for 2024-08-14."""
    hrv = [{
        "dailyHeartRateVariability": {
            "date": {"year": 2024, "month": 8, "day": 14},
            "deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds": 42.5,
            "averageHeartRateVariabilityMilliseconds": 45.0,
        }
    }]
    rhr = [{
        "dailyRestingHeartRate": {
            "date": {"year": 2024, "month": 8, "day": 14},
            "beatsPerMinute": "58",
        }
    }]
    # Sleep session: started previous evening, ends morning of target date
    sleep = [{
        "sleep": {
            "interval": {
                "startTime": "2024-08-13T22:30:00Z",
                "endTime": "2024-08-14T06:30:00Z",
            },
            "summary": {
                "minutesAsleep": "450",
                "minutesInSleepPeriod": "480",
                "minutesAwake": "30",
            },
            "stages": [
                {"type": "AWAKE", "startTime": "2024-08-13T22:30:00Z", "endTime": "2024-08-13T22:45:00Z"},
                {"type": "LIGHT", "startTime": "2024-08-13T22:45:00Z", "endTime": "2024-08-14T02:00:00Z"},
                {"type": "DEEP", "startTime": "2024-08-14T02:00:00Z", "endTime": "2024-08-14T04:00:00Z"},
                {"type": "REM", "startTime": "2024-08-14T04:00:00Z", "endTime": "2024-08-14T06:30:00Z"},
            ],
        }
    }]
    steps = [{
        "steps": {
            "startTime": "2024-08-14T00:00:00Z",
            "endTime": "2024-08-15T00:00:00Z",
            "count": "8432",
        }
    }]
    return hrv, rhr, sleep, steps


def test_build_metrics_maps_all_fields(sample_points):
    hrv, rhr, sleep, steps = sample_points
    result = _build_metrics("user-1", date(2024, 8, 14), date(2024, 8, 14), hrv, rhr, sleep, steps)

    assert len(result) == 1
    m = result[0]
    assert m.user_id == "user-1"
    assert m.date == date(2024, 8, 14)
    # HRV: deep-sleep RMSSD preferred over average
    assert m.hrv_rmssd == 42.5
    assert m.resting_heart_rate == 58.0
    assert m.sleep_duration_hours == pytest.approx(450 / 60)
    assert m.sleep_efficiency_pct == pytest.approx(450 / 480 * 100)
    assert m.waso_minutes == 30.0
    assert m.steps == 8432
    # Sleep onset = first non-awake stage (LIGHT at 22:45)
    assert m.sleep_onset is not None
    assert m.sleep_onset.hour == 22 and m.sleep_onset.minute == 45
    # Wake time = session end (06:30)
    assert m.wake_time is not None
    assert m.wake_time.hour == 6 and m.wake_time.minute == 30


def test_build_metrics_missing_day_returns_none_fields():
    """Days with no data produce a metrics object with all optional fields as None/False."""
    result = _build_metrics("user-1", date(2024, 8, 14), date(2024, 8, 14), [], [], [], [])

    assert len(result) == 1
    m = result[0]
    assert m.hrv_rmssd is None
    assert m.resting_heart_rate is None
    assert m.sleep_duration_hours is None
    assert m.steps is None


def test_build_metrics_prefers_longest_sleep_session():
    """When two sleep sessions fall on the same wake-up date, the longer one is used."""
    short = {
        "sleep": {
            "interval": {"startTime": "2024-08-13T23:00:00Z", "endTime": "2024-08-14T04:00:00Z"},
            "summary": {"minutesAsleep": "280", "minutesInSleepPeriod": "300", "minutesAwake": "20"},
            "stages": [],
        }
    }
    long = {
        "sleep": {
            "interval": {"startTime": "2024-08-13T22:00:00Z", "endTime": "2024-08-14T06:30:00Z"},
            "summary": {"minutesAsleep": "450", "minutesInSleepPeriod": "510", "minutesAwake": "60"},
            "stages": [],
        }
    }
    result = _build_metrics("user-1", date(2024, 8, 14), date(2024, 8, 14), [], [], [short, long], [])

    assert result[0].sleep_duration_hours == pytest.approx(450 / 60)


def test_build_metrics_multi_day_range():
    """Date range of N days produces exactly N metrics in order."""
    result = _build_metrics("user-1", date(2024, 8, 14), date(2024, 8, 16), [], [], [], [])

    assert len(result) == 3
    assert [m.date for m in result] == [date(2024, 8, 14), date(2024, 8, 15), date(2024, 8, 16)]


def test_build_metrics_falls_back_to_average_hrv():
    """Uses averageHeartRateVariabilityMilliseconds when deep-sleep RMSSD is absent."""
    hrv = [{
        "dailyHeartRateVariability": {
            "date": {"year": 2024, "month": 8, "day": 14},
            "averageHeartRateVariabilityMilliseconds": 45.0,
        }
    }]
    result = _build_metrics("user-1", date(2024, 8, 14), date(2024, 8, 14), hrv, [], [], [])

    assert result[0].hrv_rmssd == 45.0
