from __future__ import annotations

from datetime import date
from uuid import uuid4

import httpx

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
from conditioner.shared.constants import CLOUDFLARE_AI_BASE_URL, CLOUDFLARE_WORKOUT_MODEL


class CloudflareAIWorkoutGenerationProvider(WorkoutGenerationProvider):
    """Cloudflare Workers AI-backed implementation of WorkoutGenerationProvider.

    Sends only constraints and the readiness zone/score to the model — never raw
    wearable or questionnaire data.
    """

    def __init__(self, account_id: str, api_token: str) -> None:
        # Initializations
        self._url = (
            f"{CLOUDFLARE_AI_BASE_URL}/accounts/{account_id}/ai/run/{CLOUDFLARE_WORKOUT_MODEL}"
        )
        self._headers = {"Authorization": f"Bearer {api_token}"}

    async def generate_weekly_plan(
        self,
        user_id: str,
        week_start: date,
        constraints: WorkoutConstraints,
        readiness: ReadinessScore,
    ) -> Workout:
        """Prompt the model for a weekly plan and map the structured response to a Workout."""

        # Get the model's structured response for this week's constraints and readiness
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._url,
                headers=self._headers,
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": build_prompt(week_start, constraints, readiness),
                        }
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": WeeklyPlanSchema.model_json_schema(),
                    },
                },
            )
            response.raise_for_status()

        # Set the parsed plan from the model's JSON output
        plan = WeeklyPlanSchema.model_validate(response.json()["result"]["response"])

        # Return the generated weekly workout, mapped to domain objects
        return Workout(
            id=str(uuid4()),
            user_id=user_id,
            week_start=week_start,
            sessions=sessions_from_plan(week_start, plan),
        )
