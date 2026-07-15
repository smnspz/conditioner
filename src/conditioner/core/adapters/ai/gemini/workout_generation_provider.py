from __future__ import annotations

from datetime import date
from typing import cast
from uuid import uuid4

from google import genai
from google.genai.interactions import Interaction

from conditioner.core.adapters.ai.workout_prompt import (
    WeeklyPlanSchema,
    build_prompt,
    sessions_from_plan,
)
from conditioner.core.domain.readiness.readiness import ReadinessScore
from conditioner.core.domain.workout.constraints import WorkoutConstraints
from conditioner.core.domain.workout.workout import Workout
from conditioner.core.interfaces.workout.workout_generation_provider import (
    WorkoutGenerationProvider,
)
from conditioner.shared.constants import GEMINI_WORKOUT_MODEL


class GeminiWorkoutGenerationProvider(WorkoutGenerationProvider):
    """Gemini-backed implementation of WorkoutGenerationProvider.

    Sends only constraints and the readiness zone/score to Gemini — never raw
    wearable or questionnaire data.
    """

    def __init__(self, api_key: str) -> None:
        # Initializations
        self._client = genai.Client(api_key=api_key)

    async def generate_weekly_plan(
        self,
        user_id: str,
        week_start: date,
        constraints: WorkoutConstraints,
        readiness: ReadinessScore,
    ) -> Workout:
        """Prompt Gemini for a weekly plan and map the structured response to a Workout."""

        # Get the model's structured response for this week's constraints and readiness
        interaction = await self._client.aio.interactions.create(
            model=GEMINI_WORKOUT_MODEL,
            input=build_prompt(week_start, constraints, readiness),
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": WeeklyPlanSchema.model_json_schema(),
            },
        )

        # Set the parsed plan from the model's JSON output; requests are always
        # non-streaming here, so the response is always a single Interaction
        output_text = cast(Interaction, interaction).output_text
        plan = WeeklyPlanSchema.model_validate_json(output_text or "")

        # Return the generated weekly workout, mapped to domain objects
        return Workout(
            id=str(uuid4()),
            user_id=user_id,
            week_start=week_start,
            sessions=sessions_from_plan(week_start, plan),
        )
