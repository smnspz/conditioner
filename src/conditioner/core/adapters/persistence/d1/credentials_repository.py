from __future__ import annotations

from datetime import datetime

from conditioner.core.adapters.persistence.d1.client import D1Client, JsonRow
from conditioner.core.domain.auth.credentials import GoogleCredentials
from conditioner.core.interfaces.auth.credentials_repository import CredentialsRepository
from conditioner.core.services.auth.token_cipher import TokenCipher


class D1CredentialsRepository(CredentialsRepository):
    """Cloudflare D1-backed implementation of CredentialsRepository.

    Access and refresh tokens are encrypted at rest via the given cipher.
    """

    def __init__(self, client: D1Client, cipher: TokenCipher) -> None:
        # Initializations
        self._client = client
        self._cipher = cipher

    async def save(self, credentials: GoogleCredentials) -> None:
        """Upsert Google credentials for a user, encrypting tokens at rest."""

        await self._client.execute(
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

    async def get_by_user_id(self, user_id: str) -> GoogleCredentials | None:
        """Fetch stored Google credentials for a user, decrypted."""

        # Get credentials row for this user
        rows = await self._client.query(
            "SELECT * FROM google_credentials WHERE user_id = ?", (user_id,)
        )
        return self._to_domain(rows[0]) if rows else None

    def _to_domain(self, row: JsonRow) -> GoogleCredentials:
        """Map a result row to a GoogleCredentials domain object, decrypting tokens."""

        # Return decrypted credentials domain object
        return GoogleCredentials(
            user_id=row["user_id"],
            access_token=self._cipher.decrypt(row["access_token"]),
            refresh_token=self._cipher.decrypt(row["refresh_token"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            scopes=row["scopes"].split(",") if row["scopes"] else [],
        )
