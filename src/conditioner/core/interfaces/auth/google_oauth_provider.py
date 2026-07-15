from __future__ import annotations

from abc import ABC, abstractmethod

from conditioner.core.domain.auth.google_token import GoogleTokenResponse


class GoogleOAuthProvider(ABC):
    """Port for the Google OAuth 2.0 authorization code flow."""

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Build the URL the user is redirected to in order to grant consent."""

    @abstractmethod
    async def exchange_code(self, code: str) -> GoogleTokenResponse:
        """Exchange an authorization code for access and refresh tokens."""

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> GoogleTokenResponse:
        """Obtain a new access token using a previously issued refresh token."""

    @abstractmethod
    async def get_user_email(self, access_token: str) -> str:
        """Fetch the email address of the user who authorized the given access token."""
