from datetime import UTC, datetime

from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.domain.user import User


async def test_save_and_get_by_id_round_trips(db_path: str) -> None:
    repo = SqliteUserRepository(db_path)
    user = User(
        id="user-1",
        email="athlete@example.com",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        consent_given_at=datetime(2026, 1, 2, tzinfo=UTC),
    )

    await repo.save(user)

    fetched = await repo.get_by_id("user-1")
    assert fetched == user


async def test_get_by_email_finds_saved_user(db_path: str) -> None:
    repo = SqliteUserRepository(db_path)
    user = User(id="user-1", email="athlete@example.com", created_at=datetime.now(UTC))

    await repo.save(user)

    assert await repo.get_by_email("athlete@example.com") == user
    assert await repo.get_by_email("nobody@example.com") is None


async def test_save_upserts_existing_user(db_path: str) -> None:
    repo = SqliteUserRepository(db_path)
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    user = User(id="user-1", email="athlete@example.com", created_at=created_at)
    await repo.save(user)

    updated = User(
        id="user-1",
        email="new-email@example.com",
        created_at=created_at,
        consent_given_at=datetime(2026, 1, 3, tzinfo=UTC),
    )
    await repo.save(updated)

    fetched = await repo.get_by_id("user-1")
    assert fetched == updated


async def test_get_by_id_returns_none_when_missing(db_path: str) -> None:
    repo = SqliteUserRepository(db_path)
    assert await repo.get_by_id("missing") is None
