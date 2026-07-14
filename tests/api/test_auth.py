from collections.abc import Iterator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from conditioner.api.dependencies import (
    get_access_token_service,
    get_credentials_repository,
    get_google_oauth_provider,
    get_oauth_state_service,
    get_user_repository,
)
from conditioner.api.main import app
from conditioner.core.adapters.persistence.sqlite.credentials_repository import (
    SqliteCredentialsRepository,
)
from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.domain.google_token import GoogleTokenResponse
from conditioner.core.interfaces.google_oauth_provider import GoogleOAuthProvider
from conditioner.core.services.access_tokens import AccessTokenService
from conditioner.core.services.jwt_tokens import JwtSigner
from conditioner.core.services.oauth_state import OAuthStateService
from conditioner.core.services.token_cipher import TokenCipher

_JWT_SIGNER = JwtSigner("test-secret")


class FakeGoogleOAuthProvider(GoogleOAuthProvider):
    def __init__(self) -> None:
        self.exchanged_codes: list[str] = []
        self.next_tokens = GoogleTokenResponse(
            access_token="access-token",
            refresh_token="refresh-token",
            expires_in_seconds=3600,
            scope="scope-a scope-b",
        )
        self.email = "athlete@example.com"

    def get_authorization_url(self, state: str) -> str:
        return f"https://accounts.google.com/o/oauth2/auth?state={state}"

    async def exchange_code(self, code: str) -> GoogleTokenResponse:
        self.exchanged_codes.append(code)
        return self.next_tokens

    async def refresh_access_token(self, refresh_token: str) -> GoogleTokenResponse:
        return self.next_tokens

    async def get_user_email(self, access_token: str) -> str:
        return self.email


@pytest.fixture
def fake_oauth_provider() -> FakeGoogleOAuthProvider:
    return FakeGoogleOAuthProvider()


@pytest.fixture
def client(db_path: str, fake_oauth_provider: FakeGoogleOAuthProvider) -> Iterator[TestClient]:
    cipher = TokenCipher(Fernet.generate_key().decode())
    app.dependency_overrides[get_google_oauth_provider] = lambda: fake_oauth_provider
    app.dependency_overrides[get_user_repository] = lambda: SqliteUserRepository(db_path)
    app.dependency_overrides[get_credentials_repository] = lambda: SqliteCredentialsRepository(
        db_path, cipher
    )
    app.dependency_overrides[get_access_token_service] = lambda: AccessTokenService(_JWT_SIGNER)
    app.dependency_overrides[get_oauth_state_service] = lambda: OAuthStateService(_JWT_SIGNER)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_login_returns_authorization_url_with_state(client: TestClient) -> None:
    response = client.get("/auth/google/login")

    assert response.status_code == 200
    assert "state=" in response.json()["authorization_url"]


def test_callback_creates_user_and_returns_bearer_token(
    client: TestClient, fake_oauth_provider: FakeGoogleOAuthProvider
) -> None:
    state = OAuthStateService(_JWT_SIGNER).issue()

    response = client.get("/auth/google/callback", params={"code": "auth-code", "state": state})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert AccessTokenService(_JWT_SIGNER).verify(body["access_token"])
    assert fake_oauth_provider.exchanged_codes == ["auth-code"]


def test_callback_reuses_existing_user_on_second_login(
    client: TestClient, fake_oauth_provider: FakeGoogleOAuthProvider
) -> None:
    state_service = OAuthStateService(_JWT_SIGNER)
    access_service = AccessTokenService(_JWT_SIGNER)

    first = client.get(
        "/auth/google/callback", params={"code": "auth-code", "state": state_service.issue()}
    )
    second = client.get(
        "/auth/google/callback", params={"code": "auth-code-2", "state": state_service.issue()}
    )

    first_user_id = access_service.verify(first.json()["access_token"])
    second_user_id = access_service.verify(second.json()["access_token"])
    assert first_user_id == second_user_id


def test_callback_rejects_invalid_state(client: TestClient) -> None:
    response = client.get(
        "/auth/google/callback", params={"code": "auth-code", "state": "not-a-real-state"}
    )

    assert response.status_code == 400
