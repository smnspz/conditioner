from __future__ import annotations

from datetime import datetime

from conditioner.core.adapters.persistence.d1.client import D1Client, JsonRow
from conditioner.core.domain.auth.user import User
from conditioner.core.interfaces.auth.user_repository import UserRepository


class D1UserRepository(UserRepository):
    """Cloudflare D1-backed implementation of UserRepository."""

    def __init__(self, client: D1Client) -> None:
        # Initializations
        self._client = client

    async def save(self, user: User) -> None:
        """Upsert a user record."""

        await self._client.execute(
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

    async def get_by_id(self, user_id: str) -> User | None:
        """Fetch a user by their unique ID."""

        # Get user row by ID
        rows = await self._client.query("SELECT * FROM users WHERE id = ?", (user_id,))
        return self._to_domain(rows[0]) if rows else None

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by their email address."""

        # Get user row by email
        rows = await self._client.query("SELECT * FROM users WHERE email = ?", (email,))
        return self._to_domain(rows[0]) if rows else None

    @staticmethod
    def _to_domain(row: JsonRow) -> User:
        """Map a result row to a User domain object."""

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
