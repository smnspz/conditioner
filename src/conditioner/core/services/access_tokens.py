from __future__ import annotations

from datetime import timedelta

from conditioner.core.services.jwt_tokens import JwtError, JwtSigner

ACCESS_TOKEN_TTL = timedelta(hours=12)


class InvalidAccessToken(Exception):
    """Raised when a bearer token is missing, malformed, expired, or of the wrong type."""


class AccessTokenService:
    """Issues and verifies the Bearer tokens returned to API clients."""

    def __init__(self, signer: JwtSigner) -> None:
        self._signer = signer

    def issue(self, user_id: str) -> str:
        """Issue a new Bearer token authenticating the given user."""
        return self._signer.sign({"sub": user_id, "type": "access"}, ACCESS_TOKEN_TTL)

    def verify(self, token: str) -> str:
        """Verify a Bearer token and return the user id it authenticates."""
        try:
            claims = self._signer.verify(token)
        except JwtError as exc:
            raise InvalidAccessToken(str(exc)) from exc
        if claims.get("type") != "access":
            raise InvalidAccessToken("not an access token")
        return str(claims["sub"])
