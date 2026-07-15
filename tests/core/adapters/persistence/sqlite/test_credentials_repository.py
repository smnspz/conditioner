from datetime import UTC, datetime

import aiosqlite
from cryptography.fernet import Fernet

from conditioner.core.adapters.persistence.sqlite.credentials_repository import (
    SqliteCredentialsRepository,
)
from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.domain.auth.credentials import GoogleCredentials
from conditioner.core.domain.auth.user import User
from conditioner.core.services.auth.token_cipher import TokenCipher


def _cipher() -> TokenCipher:
    return TokenCipher(Fernet.generate_key().decode())


async def _seed_user(db_path: str, user_id: str) -> None:
    await SqliteUserRepository(db_path).save(
        User(id=user_id, email=f"{user_id}@example.com", created_at=datetime.now(UTC))
    )


async def test_save_and_get_by_user_id_round_trips(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteCredentialsRepository(db_path, _cipher())
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
    repo = SqliteCredentialsRepository(db_path, _cipher())
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
    repo = SqliteCredentialsRepository(db_path, _cipher())
    assert await repo.get_by_user_id("missing") is None


async def test_tokens_are_encrypted_at_rest(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteCredentialsRepository(db_path, _cipher())
    await repo.save(
        GoogleCredentials(
            user_id="user-1",
            access_token="plaintext-access-token",
            refresh_token="plaintext-refresh-token",
            expires_at=datetime(2026, 1, 1, tzinfo=UTC),
            scopes=["fitness.read"],
        )
    )

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT access_token, refresh_token FROM google_credentials WHERE user_id = ?",
            ("user-1",),
        )
        row = await cursor.fetchone()

    assert row is not None
    assert "plaintext-access-token" not in row[0]
    assert "plaintext-refresh-token" not in row[1]
