from __future__ import annotations

from datetime import timedelta

from conditioner.core.services.jwt_tokens import JwtError, JwtSigner

OAUTH_STATE_TTL = timedelta(minutes=5)


class InvalidOAuthState(Exception):
    """Raised when an OAuth state token is missing, malformed, expired, or of the wrong type."""


class OAuthStateService:
    """Issues and verifies short-lived, signed CSRF state tokens for the OAuth callback."""

    def __init__(self, signer: JwtSigner) -> None:
        self._signer = signer

    def issue(self) -> str:
        """Issue a new state token to embed in the authorization request."""

        return self._signer.sign({"type": "oauth_state"}, OAUTH_STATE_TTL)

    def verify(self, state: str) -> None:
        """Verify a state token returned by the OAuth callback, raising if invalid."""

        try:
            claims = self._signer.verify(state)
        except JwtError as exc:
            raise InvalidOAuthState(str(exc)) from exc
        if claims.get("type") != "oauth_state":
            raise InvalidOAuthState("not an oauth state token")
