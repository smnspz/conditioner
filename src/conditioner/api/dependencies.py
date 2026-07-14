from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from conditioner.core.adapters.google.oauth_client import GoogleOAuthClient
from conditioner.core.adapters.persistence.sqlite.credentials_repository import (
    SqliteCredentialsRepository,
)
from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.interfaces.credentials_repository import CredentialsRepository
from conditioner.core.interfaces.google_oauth_provider import GoogleOAuthProvider
from conditioner.core.interfaces.user_repository import UserRepository
from conditioner.core.services.access_tokens import AccessTokenService, InvalidAccessToken
from conditioner.core.services.jwt_tokens import JwtSigner
from conditioner.core.services.oauth_state import OAuthStateService
from conditioner.core.services.token_cipher import TokenCipher
from conditioner.shared.config import Settings, get_settings

_bearer_scheme = HTTPBearer()


def get_user_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserRepository:
    return SqliteUserRepository(settings.database_path)


def get_token_cipher(settings: Annotated[Settings, Depends(get_settings)]) -> TokenCipher:
    return TokenCipher(settings.token_encryption_key)


def get_credentials_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    cipher: Annotated[TokenCipher, Depends(get_token_cipher)],
) -> CredentialsRepository:
    return SqliteCredentialsRepository(settings.database_path, cipher)


def get_google_oauth_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GoogleOAuthProvider:
    return GoogleOAuthClient(
        client_secrets_path=settings.google_client_secrets_path,
        redirect_uri=settings.google_redirect_uri,
    )


def get_jwt_signer(settings: Annotated[Settings, Depends(get_settings)]) -> JwtSigner:
    return JwtSigner(settings.jwt_secret_key)


def get_access_token_service(
    signer: Annotated[JwtSigner, Depends(get_jwt_signer)],
) -> AccessTokenService:
    return AccessTokenService(signer)


def get_oauth_state_service(
    signer: Annotated[JwtSigner, Depends(get_jwt_signer)],
) -> OAuthStateService:
    return OAuthStateService(signer)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    token_service: Annotated[AccessTokenService, Depends(get_access_token_service)],
) -> str:
    try:
        return token_service.verify(credentials.credentials)
    except InvalidAccessToken as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc
