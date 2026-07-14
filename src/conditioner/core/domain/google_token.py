from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GoogleTokenResponse:
    """Tokens and metadata returned by Google after an OAuth code exchange or refresh.

    Attributes:
        access_token: Short-lived token used to call Google APIs.
        refresh_token: Long-lived token used to obtain new access tokens, if issued.
        expires_in_seconds: Seconds until the access token expires.
        scope: Space-separated OAuth scopes granted.
    """

    access_token: str
    refresh_token: str | None
    expires_in_seconds: int
    scope: str
