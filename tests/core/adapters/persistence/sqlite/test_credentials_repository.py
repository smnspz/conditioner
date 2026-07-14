from datetime import UTC, datetime

from conditioner.core.adapters.persistence.sqlite.credentials_repository import (
    SqliteCredentialsRepository,
)
from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.domain.credentials import GoogleCredentials
from conditioner.core.domain.user import User


async def _seed_user(db_path: str, user_id: str) -> None:
    await SqliteUserRepository(db_path).save(
        User(id=user_id, email=f"{user_id}@example.com", created_at=datetime.now(UTC))
    )


async def test_save_and_get_by_user_id_round_trips(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteCredentialsRepository(db_path)
    credentials = GoogleCredentials(
        user_id="user-1",
        access_token="access-token",
        refresh_token="refresh-token",
        expires_at=datetime(2026, 1, 1, tzinfo=UTC),
        scopes=["fitness.read", "fitness.sleep.read"],
    )

    await repo.save(credentials)

    assert await repo.get_by_user_id("user-1") == credentials


async def test_save_upserts_existing_credentials(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteCredentialsRepository(db_path)
    expires_at = datetime(2026, 1, 1, tzinfo=UTC)
    await repo.save(
        GoogleCredentials(
            user_id="user-1",
            access_token="old-token",
            refresh_token="refresh-token",
            expires_at=expires_at,
            scopes=["fitness.read"],
        )
    )

    refreshed = GoogleCredentials(
        user_id="user-1",
        access_token="new-token",
        refresh_token="refresh-token",
        expires_at=expires_at,
        scopes=["fitness.read"],
    )
    await repo.save(refreshed)

    assert await repo.get_by_user_id("user-1") == refreshed


async def test_get_by_user_id_returns_none_when_missing(db_path: str) -> None:
    repo = SqliteCredentialsRepository(db_path)
    assert await repo.get_by_user_id("missing") is None
