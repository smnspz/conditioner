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
# llama-3.1-8b-instruct is fast (~2s) but flaky at following the sets/reps-vs-duration
# instruction (run-to-run on identical input). The fp8-fast 70B variant followed it but
# took ~80s. This full-precision 70B model was 100% compliant across 3 real test runs
# at ~15-21s — best combination of reliability and latency found so far.
CLOUDFLARE_WORKOUT_MODEL = "@cf/meta/llama-3.1-70b-instruct"
CLOUDFLARE_WORKOUT_MAX_TOKENS = 4096
