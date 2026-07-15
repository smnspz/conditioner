from __future__ import annotations

from abc import ABC, abstractmethod

from conditioner.core.domain.auth.credentials import GoogleCredentials


class CredentialsRepository(ABC):
    """Port for persisting and retrieving a user's Google OAuth credentials."""

    @abstractmethod
    async def save(self, credentials: GoogleCredentials) -> None:
        """Create or update the stored credentials for a user."""

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> GoogleCredentials | None:
        """Fetch a user's stored credentials, or None if not found."""
