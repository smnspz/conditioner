from __future__ import annotations

from datetime import datetime

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.user import User
from conditioner.core.interfaces.user_repository import UserRepository


class SqliteUserRepository(UserRepository):
    """SQLite-backed implementation of UserRepository."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def save(self, user: User) -> None:
        async with connect(self._db_path) as conn:
            await conn.execute(
                """
                INSERT INTO users (id, email, created_at, consent_given_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    email = excluded.email,
                    created_at = excluded.created_at,
                    consent_given_at = excluded.consent_given_at
                """,
                (
                    user.id,
                    user.email,
                    user.created_at.isoformat(),
                    user.consent_given_at.isoformat() if user.consent_given_at else None,
                ),
            )
            await conn.commit()

    async def get_by_id(self, user_id: str) -> User | None:
        async with connect(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            return self._to_domain(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        async with connect(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = await cursor.fetchone()
            return self._to_domain(row) if row else None

    @staticmethod
    def _to_domain(row: aiosqlite.Row) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            created_at=datetime.fromisoformat(row["created_at"]),
            consent_given_at=(
                datetime.fromisoformat(row["consent_given_at"])
                if row["consent_given_at"]
                else None
            ),
        )
