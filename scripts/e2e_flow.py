"""Walk the full app flow for an already-authenticated user: constraints, wearable
metrics, questionnaire, readiness, fitness level, then weekly workout generation.

Wearable metrics are seeded directly via the configured persistence adapter
(SQLite or D1, driven by CONDITIONER_PERSISTENCE_ENGINE); everything else goes
through the real HTTP API.

Usage:
    poetry run python scripts/e2e_flow.py <access_token> [base_url]

<access_token> is the value issued by /auth/google/callback (the
access_token cookie). Get it by completing the OAuth login flow once in a
browser and copying the cookie value.
"""

import asyncio
import sys
from dataclasses import dataclass
from datetime import date, timedelta

import httpx

from conditioner.core.adapters.persistence.d1.client import D1Client
from conditioner.core.adapters.persistence.d1.metrics_repository import D1MetricsRepository
from conditioner.core.adapters.persistence.sqlite.metrics_repository import (
    SqliteMetricsRepository,
)
from conditioner.core.domain.wearables.wearable_metrics import WearableDailyMetrics
from conditioner.core.services.auth.access_tokens import AccessTokenService
from conditioner.core.services.auth.jwt_tokens import JwtSigner
from conditioner.shared.config import get_settings
from conditioner.shared.constants import Constants


@dataclass
class QuestionnaireAnswers:
    """Subjective readiness inputs for the daily questionnaire.

    Attributes:
        fatigue: Perceived fatigue on waking, 0 (fresh) to 10 (exhausted).
        soreness: Muscle soreness/DOMS, 0 (none) to 10 (strong pain).
        stress: Mental/emotional stress, 0 (calm) to 10 (very high).
        sleep_quality: Perceived sleep quality, 0 (terrible) to 10 (excellent).
        is_sick: True if the user is ill/injured, applying a fixed penalty.
    """

    fatigue: int
    soreness: int
    stress: int
    sleep_quality: int
    is_sick: bool = False


async def _seed_wearable_history(user_id: str, today: date) -> None:
    settings = get_settings()

    # Get metrics repository for the configured persistence engine
    if settings.persistence_engine == "d1":
        client = D1Client(
            account_id=settings.cloudflare_account_id,
            database_id=settings.cloudflare_d1_database_id,
            api_token=settings.cloudflare_api_token,
        )
        repo = D1MetricsRepository(client)
    else:
        repo = SqliteMetricsRepository(settings.database_path)

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


async def _clear_readiness_cache(user_id: str, day: date) -> None:
    """Delete the cached readiness score for the given day so it is recomputed fresh."""

    settings = get_settings()
    if settings.persistence_engine == "d1":
        client = D1Client(
            account_id=settings.cloudflare_account_id,
            database_id=settings.cloudflare_d1_database_id,
            api_token=settings.cloudflare_api_token,
        )
        await client.execute(
            "DELETE FROM readiness_scores WHERE user_id = ? AND date = ?",
            (user_id, day.isoformat()),
        )
    else:
        import aiosqlite

        # Get path to the SQLite database
        async with aiosqlite.connect(settings.database_path) as conn:
            await conn.execute(
                "DELETE FROM readiness_scores WHERE user_id = ? AND date = ?",
                (user_id, day.isoformat()),
            )
            await conn.commit()


def _check(response: httpx.Response, step: str) -> httpx.Response:
    if response.is_error:
        print(f"FAILED at {step}: {response.status_code} {response.text}")
        sys.exit(1)
    print(f"OK  {step}: {response.status_code}")
    return response


async def run(
    token: str,
    base_url: str,
    fitness_level: int,
    questionnaire: QuestionnaireAnswers,
) -> dict:
    """Run one full scenario and return the generated workout as a dict.

    Args:
        token: The user's access token.
        base_url: The API base URL.
        fitness_level: Weekly self-reported fitness level, 1–10.
        questionnaire: Subjective readiness answers for today.

    Returns:
        The generated workout JSON.
    """

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    # Get the user id out of the access token so we can seed metrics for the right user
    user_id = AccessTokenService(JwtSigner(get_settings().jwt_secret_key)).verify(token)

    await _seed_wearable_history(user_id, today)
    await _clear_readiness_cache(user_id, week_start)

    async with httpx.AsyncClient(
        base_url=base_url, cookies={Constants.access_token_cookie_name(): token}, timeout=180.0
    ) as client:
        _check(
            await client.put(
                "/constraints",
                json={
                    "equipment": ["resistance_bands"],
                    "goal": "mma_conditioning",
                    "available_minutes_by_weekday": {
                        "0": 60,
                        "1": 60,
                        "2": 60,
                        "3": 60,
                        "4": 60,
                        "5": 60,
                        "6": 60,
                    },
                    "initial_perceived_fitness": fitness_level,
                },
            ),
            "PUT /constraints",
        )
        _check(
            await client.put(
                f"/fitness-level/{week_start}",
                json={"score": fitness_level},
            ),
            "PUT /fitness-level",
        )
        _check(
            await client.post(
                "/questionnaire",
                json={
                    "date": str(week_start),
                    "fatigue": questionnaire.fatigue,
                    "soreness": questionnaire.soreness,
                    "stress": questionnaire.stress,
                    "sleep_quality": questionnaire.sleep_quality,
                    "is_sick": questionnaire.is_sick,
                },
            ),
            "POST /questionnaire",
        )

        # Get the readiness score (may be cached from a previous run; cleared above)
        readiness_resp = _check(
            await client.get(f"/readiness/{week_start}"), "GET /readiness"
        )
        readiness = readiness_resp.json()

        # Generate (or regenerate) the weekly plan
        gen_resp = await client.post(f"/workouts/{week_start}/generate")
        if gen_resp.status_code == 422:
            # Plan may already exist — regenerate instead
            gen_resp = _check(
                await client.post(f"/workouts/{week_start}/regenerate"),
                "POST /workouts/regenerate",
            )
        else:
            _check(gen_resp, "POST /workouts/generate")

        # Return the readiness and workout results
        return {"readiness": readiness, "workout": gen_resp.json()}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    access_token = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:9876"
    asyncio.run(
        run(
            access_token,
            url,
            fitness_level=5,
            questionnaire=QuestionnaireAnswers(
                fatigue=3, soreness=5, stress=1, sleep_quality=7
            ),
        )
    )
