from __future__ import annotations

import json
from urllib.parse import urlencode

import httpx

from conditioner.core.domain.google_token import GoogleTokenResponse
from conditioner.core.interfaces.google_oauth_provider import GoogleOAuthProvider
from conditioner.shared.constants import (
    GOOGLE_FITNESS_SCOPES,
    GOOGLE_IDENTITY_SCOPES,
    GOOGLE_USERINFO_URL,
)


class GoogleOAuthClient(GoogleOAuthProvider):
    """httpx-based GoogleOAuthProvider, backed by a downloaded client secrets file."""

    def __init__(
        self,
        client_secrets_path: str,
        redirect_uri: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        with open(client_secrets_path) as f:
            web_config = json.load(f)["web"]
        self._client_id: str = web_config["client_id"]
        self._client_secret: str = web_config["client_secret"]
        self._auth_uri: str = web_config["auth_uri"]
        self._token_uri: str = web_config["token_uri"]
        self._redirect_uri = redirect_uri
        self._transport = transport

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_IDENTITY_SCOPES + GOOGLE_FITNESS_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{self._auth_uri}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> GoogleTokenResponse:
        payload = await self._post_token(
            {
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": self._redirect_uri,
                "grant_type": "authorization_code",
            }
        )
        return self._to_domain(payload)

    async def refresh_access_token(self, refresh_token: str) -> GoogleTokenResponse:
        payload = await self._post_token(
            {
                "refresh_token": refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "refresh_token",
            }
        )
        return self._to_domain(payload)

    async def get_user_email(self, access_token: str) -> str:
        async with httpx.AsyncClient(transport=self._transport) as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return str(response.json()["email"])

    async def _post_token(self, data: dict[str, str]) -> dict[str, object]:
        async with httpx.AsyncClient(transport=self._transport) as client:
            response = await client.post(self._token_uri, data=data)
            response.raise_for_status()
            payload: dict[str, object] = response.json()
            return payload

    @staticmethod
    def _to_domain(payload: dict[str, object]) -> GoogleTokenResponse:
        return GoogleTokenResponse(
            access_token=str(payload["access_token"]),
            refresh_token=str(payload["refresh_token"]) if "refresh_token" in payload else None,
            expires_in_seconds=int(payload["expires_in"]),  # type: ignore[call-overload]
            scope=str(payload.get("scope", "")),
        )
