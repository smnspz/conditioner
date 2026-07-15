import json
from datetime import date
from unittest.mock import AsyncMock

from conditioner.core.adapters.ai.gemini.workout_generation_provider import (
    GeminiWorkoutGenerationProvider,
)
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.domain.workout.workout import ExerciseModality


def _fake_interaction(output_text: str) -> AsyncMock:
    interaction = AsyncMock()
    interaction.output_text = output_text
    return interaction


async def test_generate_weekly_plan_maps_structured_response_to_workout() -> None:
    provider = GeminiWorkoutGenerationProvider(api_key="test-key")
    plan_json = json.dumps(
        {
            "sessions": [
                {
                    "day_offset": 0,
                    "exercises": [
                        {
                            "name": "Back squat",
                            "modality": "strength",
                            "sets": 5,
                            "reps": 5,
                            "target_load": 80.0,
                        }
                    ],
                }
            ]
        }
    )
    provider._client.aio.interactions.create = AsyncMock(
        return_value=_fake_interaction(plan_json)
    )

    workout = await provider.generate_weekly_plan(
        user_id="user-1",
        week_start=date(2026, 7, 13),
        constraints=WorkoutConstraints(
            user_id="user-1",
            equipment=["barbell"],
            goal=TrainingGoal.MMA_CONDITIONING,
            available_minutes_by_weekday={0: 60},
        ),
        readiness=ReadinessScore(
            user_id="user-1", date=date(2026, 7, 13), score=75, zone=ReadinessZone.GOOD
        ),
    )

    assert workout.user_id == "user-1"
    assert workout.week_start == date(2026, 7, 13)
    assert len(workout.sessions) == 1
    session = workout.sessions[0]
    assert session.date == date(2026, 7, 13)
    assert len(session.exercises) == 1
    exercise = session.exercises[0]
    assert exercise.name == "Back squat"
    assert exercise.modality == ExerciseModality.STRENGTH
    assert exercise.sets == 5
    assert exercise.target_load == 80.0


async def test_generate_weekly_plan_calls_gemini_with_structured_output_schema() -> None:
    provider = GeminiWorkoutGenerationProvider(api_key="test-key")
    create_mock = AsyncMock(return_value=_fake_interaction(json.dumps({"sessions": []})))
    provider._client.aio.interactions.create = create_mock

    await provider.generate_weekly_plan(
        user_id="user-1",
        week_start=date(2026, 7, 13),
        constraints=WorkoutConstraints(
            user_id="user-1",
            equipment=[],
            goal=TrainingGoal.MMA_CONDITIONING,
            available_minutes_by_weekday={},
        ),
        readiness=ReadinessScore(
            user_id="user-1", date=date(2026, 7, 13), score=50, zone=ReadinessZone.MODERATE
        ),
    )

    _, kwargs = create_mock.call_args
    assert kwargs["response_format"]["mime_type"] == "application/json"
    assert "sessions" in kwargs["response_format"]["schema"]["properties"]
