from __future__ import annotations

from datetime import date, datetime, time, timedelta

import httpx

from conditioner.core.domain.credentials import GoogleCredentials
from conditioner.core.domain.wearable_metrics import WearableDailyMetrics
from conditioner.core.interfaces.wearable_provider import WearableDataProvider
from conditioner.shared.constants import GOOGLE_HEALTH_BASE_URL

# Sleep stage types that count as time asleep
_ASLEEP_TYPES = frozenset({"LIGHT", "DEEP", "REM", "ASLEEP"})


class GoogleHealthClient(WearableDataProvider):
    """WearableDataProvider backed by the Google Health REST API v4.

    Uses the stored access token as-is; the caller must ensure it is not expired.
    Sleep sessions are queried from the previous evening to correctly capture
    overnight sessions that end on the target date.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def fetch(
        self,
        user_id: str,
        credentials: GoogleCredentials,
        start: date,
        end: date,
    ) -> list[WearableDailyMetrics]:
        """Fetch daily wearable metrics from Google Health for an inclusive date range."""

        # Initializations
        headers = {"Authorization": f"Bearer {credentials.access_token}"}

        # Set exclusive end date for range queries
        end_excl = end + timedelta(days=1)

        async with httpx.AsyncClient(transport=self._transport) as client:
            # Set HRV filter string for the date range
            hrv_filter = (
                f'dailyHeartRateVariability.date >= "{start}"'
                f' AND dailyHeartRateVariability.date < "{end_excl}"'
            )

            # Get HRV data points
            hrv = await self._list(client, headers, "daily-heart-rate-variability", hrv_filter)

            # Set RHR filter string for the date range
            rhr_filter = (
                f'dailyRestingHeartRate.date >= "{start}"'
                f' AND dailyRestingHeartRate.date < "{end_excl}"'
            )

            # Get RHR data points
            rhr = await self._list(client, headers, "daily-resting-heart-rate", rhr_filter)

            # Query from previous evening to capture sessions that start before midnight
            prev_evening = (start - timedelta(days=1)).isoformat()

            # Set sleep filter string spanning overnight sessions
            sleep_filter = (
                f'sleep.interval.start_time >= "{prev_evening}T18:00:00Z"'
                f' AND sleep.interval.start_time < "{end_excl.isoformat()}T12:00:00Z"'
            )

            # Get sleep data points
            sleep = await self._list(client, headers, "sleep", sleep_filter)

            # Get daily step counts
            steps = await self._daily_roll_up(client, headers, "steps", start, end_excl)

        # Return mapped metrics list
        return _build_metrics(user_id, start, end, hrv, rhr, sleep, steps)

    async def _list(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        data_type: str,
        filter_str: str,
    ) -> list[dict]:
        """Fetch all data points for a data type, following pagination."""

        # Initializations
        url = f"{GOOGLE_HEALTH_BASE_URL}/users/me/dataTypes/{data_type}/dataPoints"
        params: dict[str, str | int] = {"filter": filter_str, "pageSize": 1000}
        points: list[dict] = []

        while True:
            # Get page of data points
            r = await client.get(url, headers=headers, params=params)
            r.raise_for_status()

            # Set parsed response body
            body = r.json()
            points.extend(body.get("dataPoints", []))

            # Get next page token if present
            token = body.get("nextPageToken")
            if not token:
                break

            # Set page token for next request
            params["pageToken"] = str(token)

        # Return all collected data points
        return points

    async def _daily_roll_up(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        data_type: str,
        start: date,
        end_excl: date,
    ) -> list[dict]:
        """Fetch one rolled-up data point per day for a given type and date range."""

        url = f"{GOOGLE_HEALTH_BASE_URL}/users/me/dataTypes/{data_type}/dataPoints:dailyRollUp"

        # Set request body with date range and daily window
        body = {
            "range": {
                "startTime": f"{start.isoformat()}T00:00:00Z",
                "endTime": f"{end_excl.isoformat()}T00:00:00Z",
            },
            "windowSizeDays": 1,
        }

        # Get daily roll-up response
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()

        # Return daily rolled-up data points
        return list(r.json().get("dataPoints", []))


def _build_metrics(
    user_id: str,
    start: date,
    end: date,
    hrv_points: list[dict],
    rhr_points: list[dict],
    sleep_points: list[dict],
    steps_points: list[dict],
) -> list[WearableDailyMetrics]:
    """Map raw API data points to one WearableDailyMetrics per day in the range."""

    # Index daily data types by date
    # Set HRV lookup keyed by date
    hrv_by_date = {
        _date_from_struct(p["dailyHeartRateVariability"]["date"]): p
        for p in hrv_points
        if "dailyHeartRateVariability" in p
    }

    # Set RHR lookup keyed by date
    rhr_by_date = {
        _date_from_struct(p["dailyRestingHeartRate"]["date"]): p
        for p in rhr_points
        if "dailyRestingHeartRate" in p
    }

    # Set steps lookup keyed by date
    steps_by_date = {_date_from_steps(p): p for p in steps_points if "steps" in p}

    # Index sleep sessions by wake-up date; prefer the longest session when multiple exist
    # Set sleep lookup keyed by wake date
    sleep_by_date: dict[date, dict] = {}
    for p in sleep_points:
        s = p.get("sleep", {})
        end_time_str = s.get("interval", {}).get("endTime")
        if not end_time_str:
            continue

        # Get wake-up date for this session
        day = _parse_ts(end_time_str).date()

        # Get existing session for this date if any
        existing = sleep_by_date.get(day)
        if existing is None or _sleep_minutes(s) > _sleep_minutes(existing.get("sleep", {})):
            # Set longest sleep session for this date
            sleep_by_date[day] = p

    # Build one metric per day in the inclusive range
    # Accumulates per-day metrics
    result: list[WearableDailyMetrics] = []
    day = start
    while day <= end:
        result.append(
            _build_day(
                user_id, day,
                hrv_by_date.get(day),
                rhr_by_date.get(day),
                sleep_by_date.get(day),
                steps_by_date.get(day),
            )
        )
        day += timedelta(days=1)

    # Return per-day metrics for the full range
    return result


def _build_day(
    user_id: str,
    day: date,
    hrv_point: dict | None,
    rhr_point: dict | None,
    sleep_point: dict | None,
    steps_point: dict | None,
) -> WearableDailyMetrics:
    """Build a single day's WearableDailyMetrics from raw API data points."""

    # Extract HRV RMSSD — deep-sleep value preferred; fall back to daily average
    hrv: float | None = None
    if hrv_point:
        # Get HRV data object
        d = hrv_point["dailyHeartRateVariability"]

        # Set HRV value, preferring deep-sleep RMSSD
        hrv = (
            d.get("deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds")
            or d.get("averageHeartRateVariabilityMilliseconds")
        )

    # Extract resting heart rate
    rhr: float | None = None
    if rhr_point:
        # Get beats-per-minute value
        bpm = rhr_point["dailyRestingHeartRate"].get("beatsPerMinute")

        # Set RHR as float or None
        rhr = float(bpm) if bpm is not None else None

    # Extract step count
    steps: int | None = None
    if steps_point:
        # Get raw step count value
        count = steps_point["steps"].get("count")

        # Set step count as int or None
        steps = int(count) if count is not None else None

    # Extract sleep metrics from session summary and stages
    sleep_hours: float | None = None
    sleep_efficiency: float | None = None
    sleep_onset: time | None = None
    wake_time: time | None = None
    waso: float | None = None
    if sleep_point:
        # Get sleep session data
        s = sleep_point["sleep"]

        # Get sleep summary dict
        summary = s.get("summary", {})

        # Set minutes asleep
        minutes_asleep = int(summary["minutesAsleep"]) if summary.get("minutesAsleep") else 0

        # Set total minutes in the sleep period
        minutes_in_period = (
            int(summary["minutesInSleepPeriod"]) if summary.get("minutesInSleepPeriod") else 0
        )

        # Set minutes awake (WASO)
        minutes_awake = int(summary["minutesAwake"]) if summary.get("minutesAwake") else 0

        if minutes_asleep:
            # Set sleep duration in hours
            sleep_hours = minutes_asleep / 60
        if minutes_asleep and minutes_in_period:
            # Set sleep efficiency %
            sleep_efficiency = minutes_asleep / minutes_in_period * 100
        if minutes_awake:
            # Set wake-after-sleep-onset in minutes
            waso = float(minutes_awake)

        # Sleep onset = start of first asleep stage; wake time = end of sleep session
        # Get list of sleep stage segments
        stages = s.get("stages", [])

        # Get first asleep stage
        first_asleep = next((st for st in stages if st.get("type") in _ASLEEP_TYPES), None)
        if first_asleep:
            # Set sleep onset time
            sleep_onset = _parse_ts(first_asleep["startTime"]).replace(tzinfo=None).timetz()

        # Get sleep session end timestamp
        end_str = s.get("interval", {}).get("endTime")
        if end_str:
            # Set wake time
            wake_time = _parse_ts(end_str).replace(tzinfo=None).timetz()

    # Return daily metrics domain object
    return WearableDailyMetrics(
        user_id=user_id,
        date=day,
        hrv_rmssd=hrv,
        resting_heart_rate=rhr,
        sleep_duration_hours=sleep_hours,
        sleep_efficiency_pct=sleep_efficiency,
        sleep_onset=sleep_onset,
        wake_time=wake_time,
        waso_minutes=waso,
        steps=steps,
    )


def _date_from_struct(d: dict) -> date:
    """Convert a Google Health Date object {year, month, day} to a Python date."""

    return date(d["year"], d["month"], d["day"])


def _date_from_steps(point: dict) -> date:
    """Extract the date from a steps dailyRollUp point via its startTime."""

    start_str = point["steps"].get("startTime", "")
    return _parse_ts(start_str).date() if start_str else date.min


def _sleep_minutes(sleep_data: dict) -> int:
    """Return minutes asleep from a sleep session's data, used for session ranking."""

    return int(sleep_data.get("summary", {}).get("minutesAsleep") or 0)


def _parse_ts(ts: str) -> datetime:
    """Parse an RFC-3339 timestamp string to an aware UTC datetime."""

    return datetime.fromisoformat(ts.replace("Z", "+00:00"))
