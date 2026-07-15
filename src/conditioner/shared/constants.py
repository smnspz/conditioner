class Constants:
    """Non-secret string/config constants."""

    _ACCESS_TOKEN_COOKIE_NAME = "access_token"

    _GOOGLE_IDENTITY_SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ]
    _GOOGLE_HEALTH_SCOPES = [
        "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
        "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
        "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    ]
    _GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    _GOOGLE_HEALTH_BASE_URL = "https://health.googleapis.com/v4"

    _GEMINI_WORKOUT_MODEL = "gemini-3.5-flash"

    _CLOUDFLARE_API_BASE_URL = "https://api.cloudflare.com/client/v4"
    _CLOUDFLARE_WORKOUT_MODEL = "@cf/meta/llama-3.1-70b-instruct"
    _CLOUDFLARE_WORKOUT_MAX_TOKENS = 4096

    @classmethod
    def access_token_cookie_name(cls) -> str:
        return cls._ACCESS_TOKEN_COOKIE_NAME

    @classmethod
    def google_identity_scopes(cls) -> list[str]:
        return cls._GOOGLE_IDENTITY_SCOPES

    @classmethod
    def google_health_scopes(cls) -> list[str]:
        return cls._GOOGLE_HEALTH_SCOPES

    @classmethod
    def google_userinfo_url(cls) -> str:
        return cls._GOOGLE_USERINFO_URL

    @classmethod
    def google_health_base_url(cls) -> str:
        return cls._GOOGLE_HEALTH_BASE_URL

    @classmethod
    def gemini_workout_model(cls) -> str:
        return cls._GEMINI_WORKOUT_MODEL

    @classmethod
    def cloudflare_api_base_url(cls) -> str:
        return cls._CLOUDFLARE_API_BASE_URL

    @classmethod
    def cloudflare_workout_model(cls) -> str:
        return cls._CLOUDFLARE_WORKOUT_MODEL

    @classmethod
    def cloudflare_workout_max_tokens(cls) -> int:
        return cls._CLOUDFLARE_WORKOUT_MAX_TOKENS
