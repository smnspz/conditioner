from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from conditioner.api.dependencies import (
    get_access_token_service,
    get_credentials_repository,
    get_google_oauth_provider,
    get_oauth_state_service,
    get_user_repository,
)
from conditioner.core.domain.credentials import GoogleCredentials
from conditioner.core.domain.user import User
from conditioner.core.interfaces.credentials_repository import CredentialsRepository
from conditioner.core.interfaces.google_oauth_provider import GoogleOAuthProvider
from conditioner.core.interfaces.user_repository import UserRepository
from conditioner.core.services.access_tokens import AccessTokenService
from conditioner.core.services.oauth_state import InvalidOAuthState, OAuthStateService
from conditioner.shared.constants import BEARER_TOKEN_SCHEME

router = APIRouter(prefix="/auth/google", tags=["auth"])


class TokenResponse(BaseModel):
    """Bearer token issued after successful OAuth."""

    access_token: str
    token_type: str = BEARER_TOKEN_SCHEME.lower()


@router.get("/login")
def login(
    oauth_provider: Annotated[GoogleOAuthProvider, Depends(get_google_oauth_provider)],
    state_service: Annotated[OAuthStateService, Depends(get_oauth_state_service)],
) -> RedirectResponse:
    """Redirect browser to Google's OAuth consent screen."""
    state = state_service.issue()
    # Get redirect URL to Google OAuth
    return RedirectResponse(url=oauth_provider.get_authorization_url(state))


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    oauth_provider: Annotated[GoogleOAuthProvider, Depends(get_google_oauth_provider)],
    state_service: Annotated[OAuthStateService, Depends(get_oauth_state_service)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    credentials_repository: Annotated[CredentialsRepository, Depends(get_credentials_repository)],
    access_token_service: Annotated[AccessTokenService, Depends(get_access_token_service)],
) -> HTMLResponse:
    try:
        state_service.verify(state)
    except InvalidOAuthState as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state"
        ) from exc

    google_tokens = await oauth_provider.exchange_code(code)
    email = await oauth_provider.get_user_email(google_tokens.access_token)

    user = await user_repository.get_by_email(email)
    if user is None:
        user = User(id=str(uuid.uuid4()), email=email, created_at=datetime.now(UTC))
        await user_repository.save(user)

    previous_credentials = await credentials_repository.get_by_user_id(user.id)
    refresh_token = google_tokens.refresh_token or (
        previous_credentials.refresh_token if previous_credentials else None
    )
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google did not return a refresh token",
        )

    await credentials_repository.save(
        GoogleCredentials(
            user_id=user.id,
            access_token=google_tokens.access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=google_tokens.expires_in_seconds),
            scopes=google_tokens.scope.split(),
        )
    )

    # Issue our Bearer token
    token = access_token_service.issue(user.id)
    # Return success page with token stored in localStorage
    return HTMLResponse(
        content=f"""<!DOCTYPE html>
<html>
<head><title>Conditioner — Authenticated</title></head>
<body>
<h2>Authentication successful</h2>
<p>Your access token has been saved.</p>
<script>
  localStorage.setItem("access_token", "{token}");
</script>
</body>
</html>
"""
    )
