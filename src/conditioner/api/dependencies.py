from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from conditioner.core.adapters.ai.cloudflare.workout_generation_provider import (
    CloudflareAIWorkoutGenerationProvider,
)
from conditioner.core.adapters.ai.gemini.workout_generation_provider import (
    GeminiWorkoutGenerationProvider,
)
from conditioner.core.adapters.google.oauth_client import GoogleOAuthClient
from conditioner.core.adapters.persistence.d1.client import D1Client
from conditioner.core.adapters.persistence.d1.constraints_repository import (
    D1ConstraintsRepository,
)
from conditioner.core.adapters.persistence.d1.credentials_repository import (
    D1CredentialsRepository,
)
from conditioner.core.adapters.persistence.d1.equipment_repository import D1EquipmentRepository
from conditioner.core.adapters.persistence.d1.exercise_catalog_repository import (
    D1ExerciseCatalogRepository,
)
from conditioner.core.adapters.persistence.d1.metrics_repository import D1MetricsRepository
from conditioner.core.adapters.persistence.d1.questionnaire_repository import (
    D1QuestionnaireRepository,
)
from conditioner.core.adapters.persistence.d1.fitness_level_repository import (
    D1FitnessLevelRepository,
)
from conditioner.core.adapters.persistence.d1.readiness_repository import D1ReadinessRepository
from conditioner.core.adapters.persistence.d1.user_repository import D1UserRepository
from conditioner.core.adapters.persistence.d1.workout_repository import D1WorkoutRepository
from conditioner.core.adapters.persistence.sqlite.constraints_repository import (
    SqliteConstraintsRepository,
)
from conditioner.core.adapters.persistence.sqlite.credentials_repository import (
    SqliteCredentialsRepository,
)
from conditioner.core.adapters.persistence.sqlite.equipment_repository import (
    SqliteEquipmentRepository,
)
from conditioner.core.adapters.persistence.sqlite.exercise_catalog_repository import (
    SqliteExerciseCatalogRepository,
)
from conditioner.core.adapters.persistence.sqlite.metrics_repository import (
    SqliteMetricsRepository,
)
from conditioner.core.adapters.persistence.sqlite.questionnaire_repository import (
    SqliteQuestionnaireRepository,
)
from conditioner.core.adapters.persistence.sqlite.fitness_level_repository import (
    SqliteFitnessLevelRepository,
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
from conditioner.core.interfaces.fitness.fitness_level_repository import FitnessLevelRepository
from conditioner.core.interfaces.readiness.readiness_repository import ReadinessRepository
from conditioner.core.interfaces.wearables.metrics_repository import MetricsRepository
from conditioner.core.interfaces.workout.constraints_repository import ConstraintsRepository
from conditioner.core.interfaces.workout.equipment_repository import EquipmentRepository
from conditioner.core.interfaces.workout.exercise_catalog_repository import (
    ExerciseCatalogRepository,
)
from conditioner.core.interfaces.workout.workout_generation_provider import (
    WorkoutGenerationProvider,
)
from conditioner.core.interfaces.workout.workout_repository import WorkoutRepository
from conditioner.core.services.auth.access_tokens import AccessTokenService, InvalidAccessToken
from conditioner.core.services.auth.jwt_tokens import JwtSigner
from conditioner.core.services.auth.oauth_state import OAuthStateService
from conditioner.core.services.auth.token_cipher import TokenCipher
from conditioner.shared.config import (
    PersistenceEngine,
    Settings,
    WorkoutGenerationEngine,
    get_settings,
)
from conditioner.shared.constants import Constants


def get_d1_client(settings: Annotated[Settings, Depends(get_settings)]) -> D1Client | None:
    """Resolve the D1 REST client when persistence_engine is D1, else None."""

    if settings.persistence_engine != PersistenceEngine.D1:
        return None

    if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "CONDITIONER_CLOUDFLARE_ACCOUNT_ID and CONDITIONER_CLOUDFLARE_API_TOKEN "
                "must be set when persistence_engine is 'd1'"
            ),
        )
    if not settings.cloudflare_d1_database_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "CONDITIONER_CLOUDFLARE_D1_DATABASE_ID must be set when "
                "persistence_engine is 'd1'"
            ),
        )

    # Return D1 REST client
    return D1Client(
        account_id=settings.cloudflare_account_id,
        database_id=settings.cloudflare_d1_database_id,
        api_token=settings.cloudflare_api_token,
    )


def get_user_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    d1_client: Annotated[D1Client | None, Depends(get_d1_client)] = None,
) -> UserRepository:
    """Resolve the active user repository, per persistence_engine."""

    if settings.persistence_engine == PersistenceEngine.D1:
        # Return D1-backed user repository
        return D1UserRepository(d1_client)  # type: ignore[arg-type]

    # Return SQLite-backed user repository
    return SqliteUserRepository(settings.database_path)


def get_token_cipher(settings: Annotated[Settings, Depends(get_settings)]) -> TokenCipher:
    """Resolve the token encryption cipher."""

    # Return token cipher
    return TokenCipher(settings.token_encryption_key)


def get_credentials_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    cipher: Annotated[TokenCipher, Depends(get_token_cipher)],
    d1_client: Annotated[D1Client | None, Depends(get_d1_client)] = None,
) -> CredentialsRepository:
    """Resolve the active credentials repository, per persistence_engine."""

    if settings.persistence_engine == PersistenceEngine.D1:
        # Return D1-backed credentials repository
        return D1CredentialsRepository(d1_client, cipher)  # type: ignore[arg-type]

    # Return SQLite-backed credentials repository
    return SqliteCredentialsRepository(settings.database_path, cipher)


def get_constraints_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    d1_client: Annotated[D1Client | None, Depends(get_d1_client)] = None,
) -> ConstraintsRepository:
    """Resolve the active workout constraints repository, per persistence_engine."""

    if settings.persistence_engine == PersistenceEngine.D1:
        # Return D1-backed constraints repository
        return D1ConstraintsRepository(d1_client)  # type: ignore[arg-type]

    # Return SQLite-backed constraints repository
    return SqliteConstraintsRepository(settings.database_path)


def get_equipment_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    d1_client: Annotated[D1Client | None, Depends(get_d1_client)] = None,
) -> EquipmentRepository:
    """Resolve the active equipment catalog repository, per persistence_engine."""

    if settings.persistence_engine == PersistenceEngine.D1:
        # Return D1-backed equipment repository
        return D1EquipmentRepository(d1_client)  # type: ignore[arg-type]

    # Return SQLite-backed equipment repository
    return SqliteEquipmentRepository(settings.database_path)


def get_exercise_catalog_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    d1_client: Annotated[D1Client | None, Depends(get_d1_client)] = None,
) -> ExerciseCatalogRepository:
    """Resolve the active exercise catalog repository, per persistence_engine."""

    if settings.persistence_engine == PersistenceEngine.D1:
        # Return D1-backed exercise catalog repository
        return D1ExerciseCatalogRepository(d1_client)  # type: ignore[arg-type]

    # Return SQLite-backed exercise catalog repository
    return SqliteExerciseCatalogRepository(settings.database_path)


def get_fitness_level_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    d1_client: Annotated[D1Client | None, Depends(get_d1_client)] = None,
) -> FitnessLevelRepository:
    """Resolve the active fitness level repository, per persistence_engine."""

    if settings.persistence_engine == PersistenceEngine.D1:
        # Return D1-backed fitness level repository
        return D1FitnessLevelRepository(d1_client)  # type: ignore[arg-type]

    # Return SQLite-backed fitness level repository
    return SqliteFitnessLevelRepository(settings.database_path)


def get_workout_generation_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> WorkoutGenerationProvider:
    """Resolve the active workout generation provider, per workout_generation_engine."""

    if settings.workout_generation_engine == WorkoutGenerationEngine.CLOUDFLARE:
        if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "CONDITIONER_CLOUDFLARE_ACCOUNT_ID and CONDITIONER_CLOUDFLARE_API_TOKEN "
                    "must be set when workout_generation_engine is 'cloudflare'"
                ),
            )
        # Return Cloudflare-backed workout generation provider
        return CloudflareAIWorkoutGenerationProvider(
            account_id=settings.cloudflare_account_id, api_token=settings.cloudflare_api_token
        )

    # Return Gemini-backed workout generation provider
    return GeminiWorkoutGenerationProvider(settings.gemini_api_key)


def get_workout_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    d1_client: Annotated[D1Client | None, Depends(get_d1_client)] = None,
) -> WorkoutRepository:
    """Resolve the active workout repository, per persistence_engine."""

    if settings.persistence_engine == PersistenceEngine.D1:
        # Return D1-backed workout repository
        return D1WorkoutRepository(d1_client)  # type: ignore[arg-type]

    # Return SQLite-backed workout repository
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
    d1_client: Annotated[D1Client | None, Depends(get_d1_client)] = None,
) -> QuestionnaireRepository:
    """Resolve the active questionnaire repository, per persistence_engine."""

    if settings.persistence_engine == PersistenceEngine.D1:
        # Return D1-backed questionnaire repository
        return D1QuestionnaireRepository(d1_client)  # type: ignore[arg-type]

    # Return SQLite-backed questionnaire repository
    return SqliteQuestionnaireRepository(settings.database_path)


def get_metrics_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    d1_client: Annotated[D1Client | None, Depends(get_d1_client)] = None,
) -> MetricsRepository:
    """Resolve the active wearable metrics repository, per persistence_engine."""

    if settings.persistence_engine == PersistenceEngine.D1:
        # Return D1-backed metrics repository
        return D1MetricsRepository(d1_client)  # type: ignore[arg-type]

    # Return SQLite-backed metrics repository
    return SqliteMetricsRepository(settings.database_path)


def get_readiness_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    d1_client: Annotated[D1Client | None, Depends(get_d1_client)] = None,
) -> ReadinessRepository:
    """Resolve the active readiness score repository, per persistence_engine."""

    if settings.persistence_engine == PersistenceEngine.D1:
        # Return D1-backed readiness repository
        return D1ReadinessRepository(d1_client)  # type: ignore[arg-type]

    # Return SQLite-backed readiness repository
    return SqliteReadinessRepository(settings.database_path)


async def get_current_user_id(
    token_service: Annotated[AccessTokenService, Depends(get_access_token_service)],
    access_token: Annotated[str | None, Cookie(alias=Constants.access_token_cookie_name())] = None,
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
