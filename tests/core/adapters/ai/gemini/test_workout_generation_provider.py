import json
from datetime import date
from unittest.mock import AsyncMock

from conditioner.core.adapters.ai.gemini.workout_generation_provider import (
    GeminiWorkoutGenerationProvider,
)
from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry
from conditioner.core.domain.workout.workout import ExerciseModality

_FITNESS_LEVEL = FitnessLevel(user_id="user-1", week_start=date(2026, 7, 13), score=6)
_CATALOG = [
    ExerciseCatalogEntry(
        id="bw_push_up",
        name="Push-Up",
        modality=ExerciseModality.STRENGTH,
        movement_pattern="push",
    )
]


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
                    "blocks": [
                        {
                            "type": "main",
                            "estimated_minutes": 30,
                            "exercises": [
                                {
                                    "exercise_id": "bw_push_up",
                                    "sets": 3,
                                    "reps": 12,
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
    )
    provider._client.aio.interactions.create = AsyncMock(
        return_value=_fake_interaction(plan_json)
    )

    workout = await provider.generate_weekly_plan(
        user_id="user-1",
        week_start=date(2026, 7, 13),
        constraints=WorkoutConstraints(
            user_id="user-1",
            equipment=[],
            goal=TrainingGoal.MMA_CONDITIONING,
            available_minutes_by_weekday={0: 60},
        ),
        fitness_level=_FITNESS_LEVEL,
        readiness=ReadinessScore(
            user_id="user-1", date=date(2026, 7, 13), score=75, zone=ReadinessZone.GOOD
        ),
        catalog_entries=_CATALOG,
    )

    assert workout.user_id == "user-1"
    assert workout.week_start == date(2026, 7, 13)
    assert len(workout.sessions) == 1
    session = workout.sessions[0]
    assert session.date == date(2026, 7, 13)
    assert len(session.blocks) == 1
    exercise = session.blocks[0].exercises[0]
    assert exercise.exercise_id == "bw_push_up"
    assert exercise.exercise_name == "Push-Up"
    assert exercise.sets == 3
    assert exercise.reps == 12


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
        fitness_level=_FITNESS_LEVEL,
        readiness=ReadinessScore(
            user_id="user-1", date=date(2026, 7, 13), score=50, zone=ReadinessZone.MODERATE
        ),
        catalog_entries=_CATALOG,
    )

    _, kwargs = create_mock.call_args
    assert kwargs["response_format"]["mime_type"] == "application/json"
    assert "sessions" in kwargs["response_format"]["schema"]["properties"]
