ACCESS_TOKEN_COOKIE_NAME = "access_token"

GOOGLE_IDENTITY_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]
GOOGLE_HEALTH_SCOPES = [
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
]
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_HEALTH_BASE_URL = "https://health.googleapis.com/v4"

GEMINI_WORKOUT_MODEL = "gemini-3.5-flash"

CLOUDFLARE_AI_BASE_URL = "https://api.cloudflare.com/client/v4"
CLOUDFLARE_WORKOUT_MODEL = "@cf/google/gemini-3.1-flash-lite"
