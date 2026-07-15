import pytest
from fastapi import HTTPException

from conditioner.api.dependencies import get_workout_generation_provider
from conditioner.core.adapters.ai.cloudflare.workout_generation_provider import (
    CloudflareAIWorkoutGenerationProvider,
)
from conditioner.core.adapters.ai.gemini.workout_generation_provider import (
    GeminiWorkoutGenerationProvider,
)
from conditioner.shared.config import Settings, WorkoutGenerationEngine


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "jwt_secret_key": "secret",
        "token_encryption_key": "key",
        "gemini_api_key": "gemini-key",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_defaults_to_gemini() -> None:
    provider = get_workout_generation_provider(_settings())

    assert isinstance(provider, GeminiWorkoutGenerationProvider)


def test_uses_cloudflare_when_selected_with_credentials() -> None:
    provider = get_workout_generation_provider(
        _settings(
            workout_generation_engine=WorkoutGenerationEngine.CLOUDFLARE,
            cloudflare_account_id="acct-1",
            cloudflare_api_token="token-1",
        )
    )

    assert isinstance(provider, CloudflareAIWorkoutGenerationProvider)


def test_raises_when_cloudflare_selected_without_credentials() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_workout_generation_provider(
            _settings(workout_generation_engine=WorkoutGenerationEngine.CLOUDFLARE)
        )

    assert exc_info.value.status_code == 500
