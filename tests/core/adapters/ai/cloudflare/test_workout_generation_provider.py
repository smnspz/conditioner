from datetime import date
from unittest.mock import AsyncMock, patch

import httpx

from conditioner.core.adapters.ai.cloudflare.workout_generation_provider import (
    CloudflareAIWorkoutGenerationProvider,
)
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.domain.workout.workout import ExerciseModality

_CONSTRAINTS = WorkoutConstraints(
    user_id="user-1",
    equipment=["barbell"],
    goal=TrainingGoal.MMA_CONDITIONING,
    available_minutes_by_weekday={0: 60},
)
_READINESS = ReadinessScore(
    user_id="user-1", date=date(2026, 7, 13), score=75, zone=ReadinessZone.GOOD
)


def _fake_response(result: dict) -> httpx.Response:
    return httpx.Response(
        200,
        json={"result": {"response": result}, "success": True, "errors": [], "messages": []},
        request=httpx.Request("POST", "https://example.test"),
    )


async def test_generate_weekly_plan_maps_structured_response_to_workout() -> None:
    provider = CloudflareAIWorkoutGenerationProvider(account_id="acct-1", api_token="test-token")
    plan = {
        "sessions": [
            {
                "day_offset": 0,
                "exercises": [
                    {
                        "name": "Back squat",
                        "modality": "strength",
                        "sets": 5,
                        "reps": 5,
                        "duration_minutes": None,
                        "target_load": 80.0,
                    }
                ],
            }
        ]
    }

    with patch.object(
        httpx.AsyncClient, "post", AsyncMock(return_value=_fake_response(plan))
    ):
        workout = await provider.generate_weekly_plan(
            user_id="user-1",
            week_start=date(2026, 7, 13),
            constraints=_CONSTRAINTS,
            readiness=_READINESS,
        )

    assert workout.user_id == "user-1"
    assert workout.week_start == date(2026, 7, 13)
    assert len(workout.sessions) == 1
    session = workout.sessions[0]
    assert session.date == date(2026, 7, 13)
    exercise = session.exercises[0]
    assert exercise.name == "Back squat"
    assert exercise.modality == ExerciseModality.STRENGTH
    assert exercise.sets == 5
    assert exercise.target_load == 80.0


async def test_generate_weekly_plan_calls_correct_url_with_structured_output_schema() -> None:
    provider = CloudflareAIWorkoutGenerationProvider(account_id="acct-1", api_token="test-token")
    post_mock = AsyncMock(return_value=_fake_response({"sessions": []}))

    with patch.object(httpx.AsyncClient, "post", post_mock):
        await provider.generate_weekly_plan(
            user_id="user-1",
            week_start=date(2026, 7, 13),
            constraints=_CONSTRAINTS,
            readiness=_READINESS,
        )

    args, kwargs = post_mock.call_args
    assert args[0] == (
        "https://api.cloudflare.com/client/v4/accounts/acct-1/ai/run/"
        "@cf/meta/llama-3.1-8b-instruct"
    )
    assert kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert kwargs["json"]["response_format"]["type"] == "json_schema"
    assert "sessions" in kwargs["json"]["response_format"]["json_schema"]["properties"]
