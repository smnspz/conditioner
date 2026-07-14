from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GoogleCredentials:
    """OAuth credentials used to call the Google Health API on a user's behalf.

    Attributes:
        user_id: The user these credentials belong to.
        access_token: Short-lived OAuth access token.
        refresh_token: Long-lived token used to obtain new access tokens.
        expires_at: When the access token expires.
        scopes: OAuth scopes granted by the user.
    """

    user_id: str
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: list[str]
