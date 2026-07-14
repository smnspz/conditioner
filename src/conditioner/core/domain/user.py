from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    """A registered user, authenticated via Google OAuth.

    Attributes:
        id: Unique identifier.
        email: The user's email address, as returned by Google.
        created_at: When the user first registered.
        consent_given_at: When the user consented to health data processing, or None if not given.
    """

    id: str
    email: str
    created_at: datetime
    consent_given_at: datetime | None = None
