from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt


class JwtError(Exception):
    """Raised when a JWT cannot be decoded, is malformed, or has expired."""


class JwtSigner:
    """Signs and verifies JWTs used for our own bearer tokens and short-lived OAuth state."""

    def __init__(self, secret_key: str, algorithm: str = "HS256") -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm

    def sign(self, claims: dict[str, object], expires_in: timedelta) -> str:
        payload = {**claims, "exp": datetime.now(UTC) + expires_in}
        return str(jwt.encode(payload, self._secret_key, algorithm=self._algorithm))

    def verify(self, token: str) -> dict[str, object]:
        try:
            return dict(jwt.decode(token, self._secret_key, algorithms=[self._algorithm]))
        except JWTError as exc:
            raise JwtError(str(exc)) from exc
