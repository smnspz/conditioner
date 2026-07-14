from datetime import UTC, date, datetime, time

from conditioner.core.adapters.persistence.sqlite.metrics_repository import (
    SqliteMetricsRepository,
)
from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.domain.user import User
from conditioner.core.domain.wearable_metrics import WearableDailyMetrics


async def _seed_user(db_path: str, user_id: str) -> None:
    await SqliteUserRepository(db_path).save(
        User(id=user_id, email=f"{user_id}@example.com", created_at=datetime.now(UTC))
    )


async def test_save_and_get_by_date_round_trips(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteMetricsRepository(db_path)
    metrics = WearableDailyMetrics(
        user_id="user-1",
        date=date(2026, 1, 1),
        hrv_rmssd=45.2,
        resting_heart_rate=52.0,
        sleep_duration_hours=7.5,
        sleep_efficiency_pct=91.0,
        sleep_onset=time(23, 15),
        wake_time=time(6, 45),
        waso_minutes=12.0,
        training_load=120.0,
        steps=8500,
        alcohol_flag=True,
        late_eating_flag=False,
    )

    await repo.save(metrics)

    assert await repo.get_by_date("user-1", date(2026, 1, 1)) == metrics


async def test_get_range_returns_ordered_metrics(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteMetricsRepository(db_path)
    for day in (date(2026, 1, 3), date(2026, 1, 1), date(2026, 1, 2)):
        await repo.save(WearableDailyMetrics(user_id="user-1", date=day, steps=1000))

    results = await repo.get_range("user-1", date(2026, 1, 1), date(2026, 1, 2))

    assert [metrics.date for metrics in results] == [date(2026, 1, 1), date(2026, 1, 2)]


async def test_get_by_date_returns_none_when_missing(db_path: str) -> None:
    repo = SqliteMetricsRepository(db_path)
    assert await repo.get_by_date("missing", date(2026, 1, 1)) is None
