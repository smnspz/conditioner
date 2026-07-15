import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from conditioner.core.adapters.google.oauth_client import GoogleOAuthClient
from conditioner.shared.constants import Constants


@pytest.fixture
def client_secrets_path(tmp_path: Path) -> str:
    path = tmp_path / "client_secret.json"
    path.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "test-client-id",
                    "client_secret": "test-client-secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
        )
    )
    return str(path)


def _token_response_handler(request: httpx.Request) -> httpx.Response:
    body = parse_qs(request.content.decode())
    if body["grant_type"][0] == "authorization_code":
        assert body["code"][0] == "auth-code"
        return httpx.Response(
            200,
            json={
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600,
                "scope": "scope-a scope-b",
            },
        )
    if body["grant_type"][0] == "refresh_token":
        assert body["refresh_token"][0] == "existing-refresh-token"
        return httpx.Response(
            200,
            json={"access_token": "refreshed-access-token", "expires_in": 3600, "scope": ""},
        )
    return httpx.Response(400, json={"error": "unsupported_grant_type"})


def test_get_authorization_url_includes_scopes_and_state(client_secrets_path: str) -> None:
    client = GoogleOAuthClient(client_secrets_path, redirect_uri="http://localhost/callback")

    url = client.get_authorization_url("state-123")

    parsed = parse_qs(urlparse(url).query)
    assert parsed["state"] == ["state-123"]
    assert parsed["client_id"] == ["test-client-id"]
    granted_scopes = set(parsed["scope"][0].split())
    expected_scopes = Constants.google_identity_scopes() + Constants.google_health_scopes()
    assert granted_scopes == set(expected_scopes)


async def test_exchange_code_returns_tokens(client_secrets_path: str) -> None:
    client = GoogleOAuthClient(
        client_secrets_path,
        redirect_uri="http://localhost/callback",
        transport=httpx.MockTransport(_token_response_handler),
    )

    tokens = await client.exchange_code("auth-code")

    assert tokens.access_token == "new-access-token"
    assert tokens.refresh_token == "new-refresh-token"
    assert tokens.expires_in_seconds == 3600
    assert tokens.scope == "scope-a scope-b"


async def test_refresh_access_token_returns_new_access_token(client_secrets_path: str) -> None:
    client = GoogleOAuthClient(
        client_secrets_path,
        redirect_uri="http://localhost/callback",
        transport=httpx.MockTransport(_token_response_handler),
    )

    tokens = await client.refresh_access_token("existing-refresh-token")

    assert tokens.access_token == "refreshed-access-token"
    assert tokens.refresh_token is None


async def test_get_user_email_returns_email_from_userinfo(client_secrets_path: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer some-access-token"
        return httpx.Response(200, json={"email": "athlete@example.com"})

    client = GoogleOAuthClient(
        client_secrets_path,
        redirect_uri="http://localhost/callback",
        transport=httpx.MockTransport(handler),
    )

    email = await client.get_user_email("some-access-token")

    assert email == "athlete@example.com"
