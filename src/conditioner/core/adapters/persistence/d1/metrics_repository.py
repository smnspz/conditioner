from __future__ import annotations

from datetime import date, time

from conditioner.core.adapters.persistence.d1.client import D1Client, JsonRow
from conditioner.core.domain.wearables.wearable_metrics import WearableDailyMetrics
from conditioner.core.interfaces.wearables.metrics_repository import MetricsRepository


class D1MetricsRepository(MetricsRepository):
    """Cloudflare D1-backed implementation of MetricsRepository."""

    def __init__(self, client: D1Client) -> None:
        # Initializations
        self._client = client

    async def save(self, metrics: WearableDailyMetrics) -> None:
        """Upsert a day's wearable metrics for a user."""

        await self._client.execute(
            """
            INSERT INTO wearable_daily_metrics (
                user_id, date, hrv_rmssd, resting_heart_rate, sleep_duration_hours,
                sleep_efficiency_pct, sleep_onset, wake_time, waso_minutes,
                training_load, steps, alcohol_flag, late_eating_flag
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id, date) DO UPDATE SET
                hrv_rmssd = excluded.hrv_rmssd,
                resting_heart_rate = excluded.resting_heart_rate,
                sleep_duration_hours = excluded.sleep_duration_hours,
                sleep_efficiency_pct = excluded.sleep_efficiency_pct,
                sleep_onset = excluded.sleep_onset,
                wake_time = excluded.wake_time,
                waso_minutes = excluded.waso_minutes,
                training_load = excluded.training_load,
                steps = excluded.steps,
                alcohol_flag = excluded.alcohol_flag,
                late_eating_flag = excluded.late_eating_flag
            """,
            (
                metrics.user_id,
                metrics.date.isoformat(),
                metrics.hrv_rmssd,
                metrics.resting_heart_rate,
                metrics.sleep_duration_hours,
                metrics.sleep_efficiency_pct,
                metrics.sleep_onset.isoformat() if metrics.sleep_onset else None,
                metrics.wake_time.isoformat() if metrics.wake_time else None,
                metrics.waso_minutes,
                metrics.training_load,
                metrics.steps,
                int(metrics.alcohol_flag),
                int(metrics.late_eating_flag),
            ),
        )

    async def get_by_date(self, user_id: str, day: date) -> WearableDailyMetrics | None:
        """Fetch wearable metrics for a single day."""

        # Get metrics row for user and date
        rows = await self._client.query(
            "SELECT * FROM wearable_daily_metrics WHERE user_id = ? AND date = ?",
            (user_id, day.isoformat()),
        )
        return self._to_domain(rows[0]) if rows else None

    async def get_range(
        self, user_id: str, start: date, end: date
    ) -> list[WearableDailyMetrics]:
        """Fetch wearable metrics for an inclusive date range, ordered by date."""

        # Get metrics rows for the date range
        rows = await self._client.query(
            """
            SELECT * FROM wearable_daily_metrics
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date
            """,
            (user_id, start.isoformat(), end.isoformat()),
        )
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: JsonRow) -> WearableDailyMetrics:
        """Map a result row to a WearableDailyMetrics domain object."""

        # Return mapped wearable metrics domain object
        return WearableDailyMetrics(
            user_id=row["user_id"],
            date=date.fromisoformat(row["date"]),
            hrv_rmssd=row["hrv_rmssd"],
            resting_heart_rate=row["resting_heart_rate"],
            sleep_duration_hours=row["sleep_duration_hours"],
            sleep_efficiency_pct=row["sleep_efficiency_pct"],
            sleep_onset=time.fromisoformat(row["sleep_onset"]) if row["sleep_onset"] else None,
            wake_time=time.fromisoformat(row["wake_time"]) if row["wake_time"] else None,
            waso_minutes=row["waso_minutes"],
            training_load=row["training_load"],
            steps=row["steps"],
            alcohol_flag=bool(row["alcohol_flag"]),
            late_eating_flag=bool(row["late_eating_flag"]),
        )
