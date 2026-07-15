from __future__ import annotations

import json
from urllib.parse import urlencode

import httpx

from conditioner.core.domain.auth.google_token import GoogleTokenResponse
from conditioner.core.interfaces.auth.google_oauth_provider import GoogleOAuthProvider
from conditioner.shared.constants import Constants


class GoogleOAuthClient(GoogleOAuthProvider):
    """httpx-based GoogleOAuthProvider, backed by a downloaded client secrets file."""

    def __init__(
        self,
        client_secrets_path: str,
        redirect_uri: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        with open(client_secrets_path) as f:
            # Get web config section from secrets file
            web_config = json.load(f)["web"]

        # Initializations
        self._client_id: str = web_config["client_id"]
        self._client_secret: str = web_config["client_secret"]
        self._auth_uri: str = web_config["auth_uri"]
        self._token_uri: str = web_config["token_uri"]
        self._redirect_uri = redirect_uri
        self._transport = transport

    def get_authorization_url(self, state: str) -> str:
        """Build the Google OAuth consent URL with required scopes and state."""

        # Set query parameters for the OAuth consent URL
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(
                Constants.google_identity_scopes() + Constants.google_health_scopes()
            ),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }

        # Return full authorization URL
        return f"{self._auth_uri}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> GoogleTokenResponse:
        """Exchange an authorization code for Google OAuth tokens."""

        # Get token response from Google
        payload = await self._post_token(
            {
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": self._redirect_uri,
                "grant_type": "authorization_code",
            }
        )

        # Return domain token object
        return self._to_domain(payload)

    async def refresh_access_token(self, refresh_token: str) -> GoogleTokenResponse:
        """Use a refresh token to obtain a fresh access token from Google."""

        # Get refreshed token response from Google
        payload = await self._post_token(
            {
                "refresh_token": refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "refresh_token",
            }
        )

        # Return domain token object
        return self._to_domain(payload)

    async def get_user_email(self, access_token: str) -> str:
        """Fetch the authenticated user's email address from the Google userinfo endpoint."""

        async with httpx.AsyncClient(transport=self._transport) as client:
            # Get userinfo response from Google
            response = await client.get(
                Constants.google_userinfo_url(),
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()

            # Return user's email address
            return str(response.json()["email"])

    async def _post_token(self, data: dict[str, str]) -> dict[str, object]:
        """POST form data to the Google token endpoint and return the parsed JSON response."""

        async with httpx.AsyncClient(transport=self._transport) as client:
            # Get token endpoint response
            response = await client.post(self._token_uri, data=data)
            response.raise_for_status()

            # Set parsed JSON payload
            payload: dict[str, object] = response.json()

            # Return raw token payload
            return payload

    @staticmethod
    def _to_domain(payload: dict[str, object]) -> GoogleTokenResponse:
        """Convert a raw Google token payload dict into a GoogleTokenResponse domain object."""

        # Return mapped domain token response
        return GoogleTokenResponse(
            access_token=str(payload["access_token"]),
            refresh_token=str(payload["refresh_token"]) if "refresh_token" in payload else None,
            expires_in_seconds=int(payload["expires_in"]),  # type: ignore[call-overload]
            scope=str(payload.get("scope", "")),
        )
