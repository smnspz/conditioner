from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

from conditioner.api.dependencies import (
    get_access_token_service,
    get_credentials_repository,
    get_google_oauth_provider,
    get_oauth_state_service,
    get_user_repository,
)
from conditioner.core.domain.auth.credentials import GoogleCredentials
from conditioner.core.domain.auth.user import User
from conditioner.core.interfaces.auth.credentials_repository import CredentialsRepository
from conditioner.core.interfaces.auth.google_oauth_provider import GoogleOAuthProvider
from conditioner.core.interfaces.auth.user_repository import UserRepository
from conditioner.core.services.auth.access_tokens import AccessTokenService
from conditioner.core.services.auth.oauth_state import InvalidOAuthState, OAuthStateService
from conditioner.shared.config import Settings, get_settings
from conditioner.shared.constants import Constants

router = APIRouter(prefix="/auth/google", tags=["auth"])


@router.get("/login")
def login(
    oauth_provider: Annotated[GoogleOAuthProvider, Depends(get_google_oauth_provider)],
    state_service: Annotated[OAuthStateService, Depends(get_oauth_state_service)],
) -> RedirectResponse:
    """Redirect browser to Google's OAuth consent screen."""

    # Get signed state token for CSRF protection
    state = state_service.issue()

    # Return redirect to Google OAuth consent screen
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
    settings: Annotated[Settings, Depends(get_settings)],
) -> HTMLResponse:
    try:
        state_service.verify(state)
    except InvalidOAuthState as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state"
        ) from exc

    # Get Google tokens from auth code
    google_tokens = await oauth_provider.exchange_code(code)

    # Get user email from Google
    email = await oauth_provider.get_user_email(google_tokens.access_token)

    # Get existing user by email
    user = await user_repository.get_by_email(email)
    if user is None:
        # Create new user
        user = User(id=str(uuid.uuid4()), email=email, created_at=datetime.now(UTC))
        await user_repository.save(user)

    # Get stored credentials for this user
    previous_credentials = await credentials_repository.get_by_user_id(user.id)

    # Set refresh token, falling back to stored one if Google omitted it
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

    # Get signed Bearer token for this user
    token = access_token_service.issue(user.id)

    # Return authentication success page, token delivered via HttpOnly cookie
    response = HTMLResponse(
        content="""<!DOCTYPE html>
<html>
<head><title>Conditioner — Authenticated</title></head>
<body>
<h2>Authentication successful</h2>
<p>You may close this window.</p>
</body>
</html>
"""
    )
    response.set_cookie(
        key=Constants.access_token_cookie_name(),
        value=token,
        httponly=True,
        secure=not settings.dev_mode,
        samesite="lax",
    )

    # Return the response
    return response
