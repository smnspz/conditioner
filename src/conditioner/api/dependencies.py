from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from conditioner.core.adapters.ai.gemini.workout_generation_provider import (
    GeminiWorkoutGenerationProvider,
)
from conditioner.core.adapters.google.oauth_client import GoogleOAuthClient
from conditioner.core.adapters.persistence.sqlite.constraints_repository import (
    SqliteConstraintsRepository,
)
from conditioner.core.adapters.persistence.sqlite.credentials_repository import (
    SqliteCredentialsRepository,
)
from conditioner.core.adapters.persistence.sqlite.metrics_repository import (
    SqliteMetricsRepository,
)
from conditioner.core.adapters.persistence.sqlite.questionnaire_repository import (
    SqliteQuestionnaireRepository,
)
from conditioner.core.adapters.persistence.sqlite.readiness_repository import (
    SqliteReadinessRepository,
)
from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.adapters.persistence.sqlite.workout_repository import (
    SqliteWorkoutRepository,
)
from conditioner.core.interfaces.auth.credentials_repository import CredentialsRepository
from conditioner.core.interfaces.auth.google_oauth_provider import GoogleOAuthProvider
from conditioner.core.interfaces.auth.user_repository import UserRepository
from conditioner.core.interfaces.questionnaire.questionnaire_repository import (
    QuestionnaireRepository,
)
from conditioner.core.interfaces.readiness.readiness_repository import ReadinessRepository
from conditioner.core.interfaces.wearables.metrics_repository import MetricsRepository
from conditioner.core.interfaces.workout.constraints_repository import ConstraintsRepository
from conditioner.core.interfaces.workout.workout_generation_provider import (
    WorkoutGenerationProvider,
)
from conditioner.core.interfaces.workout.workout_repository import WorkoutRepository
from conditioner.core.services.auth.access_tokens import AccessTokenService, InvalidAccessToken
from conditioner.core.services.auth.jwt_tokens import JwtSigner
from conditioner.core.services.auth.oauth_state import OAuthStateService
from conditioner.core.services.auth.token_cipher import TokenCipher
from conditioner.shared.config import Settings, get_settings
from conditioner.shared.constants import ACCESS_TOKEN_COOKIE_NAME


def get_user_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserRepository:
    """Resolve the SQLite-backed user repository."""

    # Return user repository
    return SqliteUserRepository(settings.database_path)


def get_token_cipher(settings: Annotated[Settings, Depends(get_settings)]) -> TokenCipher:
    """Resolve the token encryption cipher."""

    # Return token cipher
    return TokenCipher(settings.token_encryption_key)


def get_credentials_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    cipher: Annotated[TokenCipher, Depends(get_token_cipher)],
) -> CredentialsRepository:
    """Resolve the SQLite-backed credentials repository."""

    # Return credentials repository
    return SqliteCredentialsRepository(settings.database_path, cipher)


def get_constraints_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConstraintsRepository:
    """Resolve the SQLite-backed workout constraints repository."""

    # Return constraints repository
    return SqliteConstraintsRepository(settings.database_path)


def get_workout_generation_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> WorkoutGenerationProvider:
    """Resolve the Gemini-backed workout generation provider."""

    # Return workout generation provider
    return GeminiWorkoutGenerationProvider(settings.gemini_api_key)


def get_workout_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> WorkoutRepository:
    """Resolve the SQLite-backed workout repository."""

    # Return workout repository
    return SqliteWorkoutRepository(settings.database_path)


def get_google_oauth_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GoogleOAuthProvider:
    """Resolve the Google OAuth client."""

    # Return Google OAuth provider
    return GoogleOAuthClient(
        client_secrets_path=settings.google_client_secrets_path,
        redirect_uri=settings.google_redirect_uri,
    )


def get_jwt_signer(settings: Annotated[Settings, Depends(get_settings)]) -> JwtSigner:
    """Resolve the JWT signer."""

    # Return JWT signer
    return JwtSigner(settings.jwt_secret_key)


def get_access_token_service(
    signer: Annotated[JwtSigner, Depends(get_jwt_signer)],
) -> AccessTokenService:
    """Resolve the access token service."""

    # Return access token service
    return AccessTokenService(signer)


def get_oauth_state_service(
    signer: Annotated[JwtSigner, Depends(get_jwt_signer)],
) -> OAuthStateService:
    """Resolve the OAuth state service."""

    # Return OAuth state service
    return OAuthStateService(signer)


def get_questionnaire_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> QuestionnaireRepository:
    """Resolve the SQLite-backed questionnaire repository."""

    # Return questionnaire repository
    return SqliteQuestionnaireRepository(settings.database_path)


def get_metrics_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> MetricsRepository:
    """Resolve the SQLite-backed wearable metrics repository."""

    # Return metrics repository
    return SqliteMetricsRepository(settings.database_path)


def get_readiness_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadinessRepository:
    """Resolve the SQLite-backed readiness score repository."""

    # Return readiness repository
    return SqliteReadinessRepository(settings.database_path)


async def get_current_user_id(
    token_service: Annotated[AccessTokenService, Depends(get_access_token_service)],
    access_token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE_NAME)] = None,
) -> str:
    """Extract and verify the user ID from the access token cookie."""

    if access_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        # Return verified user ID
        return token_service.verify(access_token)
    except InvalidAccessToken as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc
