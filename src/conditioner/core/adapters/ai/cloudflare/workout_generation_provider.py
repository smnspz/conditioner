from __future__ import annotations

import json
import logging
from datetime import date
from uuid import uuid4

import httpx

from conditioner.core.adapters.ai.workout_prompt import (
    build_prompt,
    build_repair_prompt,
    build_weekly_plan_schema,
    sessions_from_plan,
)
from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.domain.readiness.readiness import ReadinessScore
from conditioner.core.domain.workout.constraints import WorkoutConstraints
from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry
from conditioner.core.domain.workout.workout import Workout
from conditioner.core.interfaces.workout.workout_generation_provider import (
    WorkoutGenerationProvider,
)
from conditioner.core.services.workout.validate_workout_plan import validate_workout_plan
from conditioner.shared.constants import Constants

logger = logging.getLogger(__name__)


class CloudflareAIWorkoutGenerationProvider(WorkoutGenerationProvider):
    """Cloudflare Workers AI-backed implementation of WorkoutGenerationProvider.

    Sends only constraints and the readiness zone/score to the model — never raw
    wearable or questionnaire data. Includes one repair pass before falling back.
    """

    def __init__(self, account_id: str, api_token: str) -> None:
        # Initializations
        self._url = (
            f"{Constants.cloudflare_api_base_url()}/accounts/{account_id}"
            f"/ai/run/{Constants.cloudflare_workout_model()}"
        )
        self._headers = {"Authorization": f"Bearer {api_token}"}

    async def _call(self, client: httpx.AsyncClient, messages: list[dict]) -> str:
        """Send a single chat completion request and return the raw response string."""

        response = await client.post(
            self._url,
            headers=self._headers,
            json={
                "messages": messages,
                "max_tokens": Constants.cloudflare_workout_max_tokens(),
            },
        )
        if not response.is_success:
            error = response.json().get("errors", [{}])[0].get("message", response.text)
            raise RuntimeError(f"Cloudflare AI error {response.status_code}: {error}")

        result = response.json()["result"]["response"]
        return result if isinstance(result, str) else json.dumps(result)

    async def _call_structured(
        self, client: httpx.AsyncClient, messages: list[dict], schema_cls: type
    ) -> str:
        """Send a structured-output chat completion and return the raw response string."""

        response = await client.post(
            self._url,
            headers=self._headers,
            json={
                "messages": messages,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": schema_cls.model_json_schema(),
                },
                "max_tokens": Constants.cloudflare_workout_max_tokens(),
            },
        )
        if not response.is_success:
            error = response.json().get("errors", [{}])[0].get("message", response.text)
            raise RuntimeError(f"Cloudflare AI error {response.status_code}: {error}")

        result = response.json()["result"]["response"]
        return result if isinstance(result, str) else json.dumps(result)

    async def generate_weekly_plan(
        self,
        user_id: str,
        week_start: date,
        constraints: WorkoutConstraints,
        fitness_level: FitnessLevel,
        readiness: ReadinessScore | None,
        catalog_entries: list[ExerciseCatalogEntry],
    ) -> Workout:
        """Prompt the model for a weekly plan; repair once if validation fails; raise on second failure."""

        # Get the per-request schema with exercise_id constrained to catalog IDs
        schema_cls = build_weekly_plan_schema(catalog_entries)

        # Build the catalog index for name denormalization and validation
        catalog_index = {e.id: e for e in catalog_entries}

        # Get session_duration as the most common non-zero budget (for duration validation)
        budgets = [m for m in constraints.available_minutes_by_weekday.values() if m > 0]
        session_duration = min(budgets) if budgets else 30

        user_message = build_prompt(
            week_start, constraints, fitness_level, readiness, catalog_entries
        )

        async with httpx.AsyncClient(timeout=150.0) as client:
            # First attempt with structured output
            raw = await self._call_structured(
                client,
                [{"role": "user", "content": user_message}],
                schema_cls,
            )
            plan = schema_cls.model_validate_json(raw)

            # Validate the plan
            candidate = Workout(
                id=str(uuid4()),
                user_id=user_id,
                week_start=week_start,
                sessions=sessions_from_plan(week_start, plan, catalog_index),
            )
            errors = validate_workout_plan(candidate, catalog_index, session_duration)

            if errors:
                logger.warning(
                    "generation.repair_triggered user=%s codes=%s",
                    user_id,
                    [e.code for e in errors],
                )
                repair_msg = build_repair_prompt(raw, errors)
                raw2 = await self._call_structured(
                    client,
                    [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": raw},
                        {"role": "user", "content": repair_msg},
                    ],
                    schema_cls,
                )
                plan = schema_cls.model_validate_json(raw2)
                candidate = Workout(
                    id=str(uuid4()),
                    user_id=user_id,
                    week_start=week_start,
                    sessions=sessions_from_plan(week_start, plan, catalog_index),
                )
                errors2 = validate_workout_plan(candidate, catalog_index, session_duration)
                if errors2:
                    logger.error(
                        "generation.repair_failed user=%s codes=%s",
                        user_id,
                        [e.code for e in errors2],
                    )
                    raise RuntimeError(
                        f"Workout plan failed validation after repair: "
                        f"{[e.code for e in errors2]}"
                    )

            logger.info("generation.success user=%s", user_id)

        # Return the validated weekly workout mapped to domain objects
        return candidate
