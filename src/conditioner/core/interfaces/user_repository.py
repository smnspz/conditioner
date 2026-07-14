from __future__ import annotations

from abc import ABC, abstractmethod

from conditioner.core.domain.user import User


class UserRepository(ABC):
    """Port for persisting and retrieving users."""

    @abstractmethod
    async def save(self, user: User) -> None:
        """Create or update a user."""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        """Fetch a user by id, or None if not found."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email, or None if not found."""
