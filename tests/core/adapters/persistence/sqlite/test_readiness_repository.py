from datetime import UTC, date, datetime

from conditioner.core.adapters.persistence.sqlite.readiness_repository import (
    SqliteReadinessRepository,
)
from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.domain.auth.user import User
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone


async def _seed_user(db_path: str, user_id: str) -> None:
    await SqliteUserRepository(db_path).save(
        User(id=user_id, email=f"{user_id}@example.com", created_at=datetime.now(UTC))
    )


async def test_save_and_get_by_date_round_trips(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteReadinessRepository(db_path)
    score = ReadinessScore(
        user_id="user-1", date=date(2026, 1, 1), score=72, zone=ReadinessZone.GOOD
    )

    await repo.save(score)

    assert await repo.get_by_date("user-1", date(2026, 1, 1)) == score


async def test_get_range_returns_ordered_scores(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteReadinessRepository(db_path)
    for day, value in ((date(2026, 1, 3), 90), (date(2026, 1, 1), 40), (date(2026, 1, 2), 60)):
        await repo.save(
            ReadinessScore(
                user_id="user-1", date=day, score=value, zone=ReadinessZone.from_score(value)
            )
        )

    results = await repo.get_range("user-1", date(2026, 1, 1), date(2026, 1, 2))

    assert [(r.date, r.score) for r in results] == [
        (date(2026, 1, 1), 40),
        (date(2026, 1, 2), 60),
    ]


async def test_get_by_date_returns_none_when_missing(db_path: str) -> None:
    repo = SqliteReadinessRepository(db_path)
    assert await repo.get_by_date("missing", date(2026, 1, 1)) is None
