from __future__ import annotations

from datetime import date
from uuid import uuid4

import httpx

from conditioner.core.adapters.ai.workout_prompt import (
    build_prompt,
    build_weekly_plan_schema,
    sessions_from_plan,
)
from conditioner.core.domain.readiness.readiness import ReadinessScore
from conditioner.core.domain.workout.constraints import WorkoutConstraints
from conditioner.core.domain.workout.workout import Workout
from conditioner.core.interfaces.workout.workout_generation_provider import (
    WorkoutGenerationProvider,
)
from conditioner.shared.constants import Constants


class CloudflareAIWorkoutGenerationProvider(WorkoutGenerationProvider):
    """Cloudflare Workers AI-backed implementation of WorkoutGenerationProvider.

    Sends only constraints and the readiness zone/score to the model — never raw
    wearable or questionnaire data.
    """

    def __init__(self, account_id: str, api_token: str) -> None:
        # Initializations
        self._url = (
            f"{Constants.cloudflare_api_base_url()}/accounts/{account_id}"
            f"/ai/run/{Constants.cloudflare_workout_model()}"
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

        # Get the per-request schema, constraining exercise equipment to what's available
        schema_cls = build_weekly_plan_schema(constraints)

        # Get the model's structured response for this week's constraints and readiness
        async with httpx.AsyncClient(timeout=150.0) as client:
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
                        "json_schema": schema_cls.model_json_schema(),
                    },
                    "max_tokens": Constants.cloudflare_workout_max_tokens(),
                },
            )
            response.raise_for_status()

        # Parse the model's JSON output; handle both string and already-parsed responses
        result = response.json()["result"]["response"]
        plan = (
            schema_cls.model_validate_json(result)
            if isinstance(result, str)
            else schema_cls.model_validate(result)
        )

        # Return the generated weekly workout, mapped to domain objects
        return Workout(
            id=str(uuid4()),
            user_id=user_id,
            week_start=week_start,
            sessions=sessions_from_plan(week_start, plan),
        )
