import pytest

from conditioner.core.services.access_tokens import AccessTokenService
from conditioner.core.services.jwt_tokens import JwtSigner
from conditioner.core.services.oauth_state import InvalidOAuthState, OAuthStateService


def test_issue_and_verify_accepts_a_freshly_issued_state() -> None:
    service = OAuthStateService(JwtSigner("secret"))

    state = service.issue()

    service.verify(state)  # should not raise


def test_verify_rejects_garbage_state() -> None:
    service = OAuthStateService(JwtSigner("secret"))

    with pytest.raises(InvalidOAuthState):
        service.verify("garbage")


def test_verify_rejects_a_token_of_a_different_type() -> None:
    signer = JwtSigner("secret")
    state_service = OAuthStateService(signer)
    access_token = AccessTokenService(signer).issue("user-1")

    with pytest.raises(InvalidOAuthState):
        state_service.verify(access_token)
