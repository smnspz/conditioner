"""Walk the full app flow for an already-authenticated user: constraints, wearable
metrics, questionnaire, readiness, then weekly workout generation.

There is no HTTP endpoint yet to ingest wearable metrics (that happens via a
background Google Health sync, not built as an on-demand route), so this
script seeds them directly through SqliteMetricsRepository. Everything else
goes through the real HTTP API.

Usage:
    poetry run python scripts/e2e_flow.py <access_token> [base_url]

<access_token> is the value issued by /auth/google/callback (the
access_token cookie). Get it by completing the OAuth login flow once in a
browser and copying the cookie value.
"""

import asyncio
import sys
from datetime import date, timedelta

import httpx

from conditioner.core.adapters.persistence.sqlite.metrics_repository import (
    SqliteMetricsRepository,
)
from conditioner.core.domain.wearables.wearable_metrics import WearableDailyMetrics
from conditioner.core.services.auth.access_tokens import AccessTokenService
from conditioner.core.services.auth.jwt_tokens import JwtSigner
from conditioner.shared.config import get_settings
from conditioner.shared.constants import ACCESS_TOKEN_COOKIE_NAME


async def _seed_wearable_history(user_id: str, today: date) -> None:
    repo = SqliteMetricsRepository(get_settings().database_path)
    for offset in range(14, -1, -1):
        await repo.save(
            WearableDailyMetrics(
                user_id=user_id,
                date=today - timedelta(days=offset),
                hrv_rmssd=65.0,
                resting_heart_rate=48.0,
                sleep_duration_hours=7.5,
                sleep_efficiency_pct=92.0,
                training_load=40.0,
                steps=8000,
            )
        )


def _check(response: httpx.Response, step: str) -> httpx.Response:
    if response.is_error:
        print(f"FAILED at {step}: {response.status_code} {response.text}")
        sys.exit(1)
    print(f"OK  {step}: {response.status_code} {response.json()}")
    return response


async def run(token: str, base_url: str) -> None:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    # Weekly generation requires a readiness score dated exactly at week_start
    # (not just "today's"), so that's the date we submit the questionnaire for.
    readiness_day = week_start

    # Get the user id out of the access token so we can seed metrics for the right user
    user_id = AccessTokenService(JwtSigner(get_settings().jwt_secret_key)).verify(token)

    await _seed_wearable_history(user_id, today)
    print(f"Seeded 15 days of wearable metrics for user {user_id}")

    async with httpx.AsyncClient(
        base_url=base_url, cookies={ACCESS_TOKEN_COOKIE_NAME: token}, timeout=30.0
    ) as client:
        _check(
            await client.put(
                "/constraints",
                json={
                    "equipment": ["dumbbells", "kettlebell"],
                    "goal": "mma_conditioning",
                    "available_minutes_by_weekday": {"0": 45, "1": 45, "2": 45, "3": 45, "4": 45},
                },
            ),
            "PUT /constraints",
        )
        _check(
            await client.post(
                "/questionnaire",
                json={
                    "date": str(readiness_day),
                    "fatigue": 2,
                    "soreness": 2,
                    "stress": 2,
                    "sleep_quality": 8,
                    "is_sick": False,
                },
            ),
            "POST /questionnaire",
        )
        _check(await client.get(f"/readiness/{readiness_day}"), "GET /readiness/{readiness_day}")
        _check(
            await client.post(f"/workouts/{week_start}/generate"),
            "POST /workouts/{week_start}/generate",
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    access_token = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:9876"
    asyncio.run(run(access_token, url))
