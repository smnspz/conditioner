from __future__ import annotations

from datetime import datetime

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.credentials import GoogleCredentials
from conditioner.core.interfaces.credentials_repository import CredentialsRepository
from conditioner.core.services.token_cipher import TokenCipher


class SqliteCredentialsRepository(CredentialsRepository):
    """SQLite-backed implementation of CredentialsRepository.

    Access and refresh tokens are encrypted at rest via the given cipher.
    """

    def __init__(self, db_path: str, cipher: TokenCipher) -> None:
        self._db_path = db_path
        self._cipher = cipher

    async def save(self, credentials: GoogleCredentials) -> None:
        async with connect(self._db_path) as conn:
            await conn.execute(
                """
                INSERT INTO google_credentials
                    (user_id, access_token, refresh_token, expires_at, scopes)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (user_id) DO UPDATE SET
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    expires_at = excluded.expires_at,
                    scopes = excluded.scopes
                """,
                (
                    credentials.user_id,
                    self._cipher.encrypt(credentials.access_token),
                    self._cipher.encrypt(credentials.refresh_token),
                    credentials.expires_at.isoformat(),
                    ",".join(credentials.scopes),
                ),
            )
            await conn.commit()

    async def get_by_user_id(self, user_id: str) -> GoogleCredentials | None:
        async with connect(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM google_credentials WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return self._to_domain(row) if row else None

    def _to_domain(self, row: aiosqlite.Row) -> GoogleCredentials:
        return GoogleCredentials(
            user_id=row["user_id"],
            access_token=self._cipher.decrypt(row["access_token"]),
            refresh_token=self._cipher.decrypt(row["refresh_token"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            scopes=row["scopes"].split(",") if row["scopes"] else [],
        )
