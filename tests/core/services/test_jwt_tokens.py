from datetime import timedelta

import pytest

from conditioner.core.services.auth.jwt_tokens import JwtError, JwtSigner


def test_sign_and_verify_round_trips_claims() -> None:
    signer = JwtSigner("secret")

    token = signer.sign({"sub": "user-1"}, timedelta(minutes=5))
    claims = signer.verify(token)

    assert claims["sub"] == "user-1"


def test_verify_rejects_token_signed_with_different_key() -> None:
    token = JwtSigner("secret-a").sign({"sub": "user-1"}, timedelta(minutes=5))

    with pytest.raises(JwtError):
        JwtSigner("secret-b").verify(token)


def test_verify_rejects_expired_token() -> None:
    token = JwtSigner("secret").sign({"sub": "user-1"}, timedelta(seconds=-1))

    with pytest.raises(JwtError):
        JwtSigner("secret").verify(token)


def test_verify_rejects_malformed_token() -> None:
    with pytest.raises(JwtError):
        JwtSigner("secret").verify("not-a-jwt")
