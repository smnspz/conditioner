import pytest

from conditioner.core.services.auth.access_tokens import AccessTokenService, InvalidAccessToken
from conditioner.core.services.auth.jwt_tokens import JwtSigner
from conditioner.core.services.auth.oauth_state import OAuthStateService


def test_issue_and_verify_round_trips_user_id() -> None:
    service = AccessTokenService(JwtSigner("secret"))

    token = service.issue("user-1")

    assert service.verify(token) == "user-1"


def test_verify_rejects_garbage_token() -> None:
    service = AccessTokenService(JwtSigner("secret"))

    with pytest.raises(InvalidAccessToken):
        service.verify("garbage")


def test_verify_rejects_token_of_a_different_type() -> None:
    signer = JwtSigner("secret")
    access_service = AccessTokenService(signer)
    state_service = OAuthStateService(signer)

    oauth_state_token = state_service.issue()

    with pytest.raises(InvalidAccessToken):
        access_service.verify(oauth_state_token)
