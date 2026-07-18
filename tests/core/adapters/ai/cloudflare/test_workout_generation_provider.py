import json
from datetime import date
from unittest.mock import AsyncMock, patch

import httpx

from conditioner.core.adapters.ai.cloudflare.workout_generation_provider import (
    CloudflareAIWorkoutGenerationProvider,
)
from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry
from conditioner.core.domain.workout.workout import ExerciseModality

_CONSTRAINTS = WorkoutConstraints(
    user_id="user-1",
    equipment=["dumbbells"],
    goal=TrainingGoal.MMA_CONDITIONING,
    available_minutes_by_weekday={0: 60},
)
_FITNESS_LEVEL = FitnessLevel(user_id="user-1", week_start=date(2026, 7, 13), score=6)
_READINESS = ReadinessScore(
    user_id="user-1", date=date(2026, 7, 13), score=75, zone=ReadinessZone.GOOD
)
_CATALOG = [
    ExerciseCatalogEntry(
        id="db_goblet_squat",
        name="Goblet Squat",
        modality=ExerciseModality.STRENGTH,
        movement_pattern="squat",
    )
]

_PLAN = {
    "sessions": [
        {
            "day_offset": 0,
            "blocks": [
                {
                    "type": "main",
                    "estimated_minutes": 60,
                    "exercises": [
                        {
                            "exercise_id": "db_goblet_squat",
                            "sets": 3,
                            "reps": 10,
                            "rest_seconds": 60,
                            "intensity_cue": "RPE 7",
                            "notes": "",
                        }
                    ],
                }
            ],
        }
    ]
}


def _fake_response(result: dict, *, as_string: bool) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "result": {"response": json.dumps(result) if as_string else result},
            "success": True,
            "errors": [],
            "messages": [],
        },
        request=httpx.Request("POST", "https://example.test"),
    )


async def _assert_maps_plan_to_workout(response: httpx.Response) -> None:
    provider = CloudflareAIWorkoutGenerationProvider(account_id="acct-1", api_token="test-token")

    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=response)):
        workout = await provider.generate_weekly_plan(
            user_id="user-1",
            week_start=date(2026, 7, 13),
            constraints=_CONSTRAINTS,
            fitness_level=_FITNESS_LEVEL,
            readiness=_READINESS,
            catalog_entries=_CATALOG,
        )

    assert workout.user_id == "user-1"
    assert workout.week_start == date(2026, 7, 13)
    assert len(workout.sessions) == 1
    session = workout.sessions[0]
    assert session.date == date(2026, 7, 13)
    assert len(session.blocks) == 1
    block = session.blocks[0]
    assert block.type.value == "main"
    exercise = block.exercises[0]
    assert exercise.exercise_id == "db_goblet_squat"
    assert exercise.exercise_name == "Goblet Squat"
    assert exercise.sets == 3
    assert exercise.reps == 10


async def test_generate_weekly_plan_maps_string_encoded_response_to_workout() -> None:
    await _assert_maps_plan_to_workout(_fake_response(_PLAN, as_string=True))


async def test_generate_weekly_plan_maps_object_response_to_workout() -> None:
    await _assert_maps_plan_to_workout(_fake_response(_PLAN, as_string=False))


async def test_generate_weekly_plan_calls_correct_url_with_structured_output_schema() -> None:
    provider = CloudflareAIWorkoutGenerationProvider(account_id="acct-1", api_token="test-token")
    post_mock = AsyncMock(return_value=_fake_response({"sessions": []}, as_string=True))

    with patch.object(httpx.AsyncClient, "post", post_mock):
        await provider.generate_weekly_plan(
            user_id="user-1",
            week_start=date(2026, 7, 13),
            constraints=_CONSTRAINTS,
            fitness_level=_FITNESS_LEVEL,
            readiness=_READINESS,
            catalog_entries=_CATALOG,
        )

    args, kwargs = post_mock.call_args
    assert args[0] == (
        "https://api.cloudflare.com/client/v4/accounts/acct-1/ai/run/"
        "@cf/meta/llama-3.3-70b-instruct"
    )
    assert kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert kwargs["json"]["response_format"]["type"] == "json_schema"
    assert "sessions" in kwargs["json"]["response_format"]["json_schema"]["properties"]
    assert kwargs["json"]["max_tokens"] == 4096

    # exercise_id is constrained to the catalog IDs
    defs = kwargs["json"]["response_format"]["json_schema"]["$defs"]
    id_field = defs["BlockExerciseSchema"]["properties"]["exercise_id"]
    allowed = set(id_field["enum"]) if "enum" in id_field else {id_field["const"]}
    assert allowed == {"db_goblet_squat"}
