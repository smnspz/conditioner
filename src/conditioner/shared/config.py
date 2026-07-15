from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables and .env.

    Attributes:
        database_path: Path to the SQLite database file.
        google_client_secrets_path: Path to the downloaded Google OAuth client secrets file.
        google_redirect_uri: OAuth redirect URI registered in the Google Cloud Console.
        jwt_secret_key: Symmetric key used to sign our own Bearer tokens and OAuth state.
        token_encryption_key: Fernet key used to encrypt stored Google OAuth tokens at rest.
        dev_mode: When true, allows the access-token cookie over plain HTTP (no Secure flag).
        gemini_api_key: API key for the Gemini API, used to generate workout plans.
    """

    database_path: str = "data/conditioner.db"
    google_client_secrets_path: str = "client_secret.json"
    google_redirect_uri: str = "http://localhost:9876/auth/google/callback"
    jwt_secret_key: str
    token_encryption_key: str
    dev_mode: bool = False
    gemini_api_key: str

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CONDITIONER_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
