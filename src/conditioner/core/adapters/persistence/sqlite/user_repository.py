from __future__ import annotations

from datetime import datetime

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.auth.user import User
from conditioner.core.interfaces.auth.user_repository import UserRepository


class SqliteUserRepository(UserRepository):
    """SQLite-backed implementation of UserRepository."""

    def __init__(self, db_path: str) -> None:
        # Initializations
        self._db_path = db_path

    async def save(self, user: User) -> None:
        """Upsert a user record."""

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
        """Fetch a user by their unique ID."""

        async with connect(self._db_path) as conn:
            # Get user row by ID
            cursor = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))

            # Get single result row
            row = await cursor.fetchone()

            # Return domain object or None
            return self._to_domain(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by their email address."""

        async with connect(self._db_path) as conn:
            # Get user row by email
            cursor = await conn.execute("SELECT * FROM users WHERE email = ?", (email,))

            # Get single result row
            row = await cursor.fetchone()

            # Return domain object or None
            return self._to_domain(row) if row else None

    @staticmethod
    def _to_domain(row: aiosqlite.Row) -> User:
        """Map a database row to a User domain object."""

        # Return mapped user domain object
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
