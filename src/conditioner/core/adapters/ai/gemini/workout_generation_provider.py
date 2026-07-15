from __future__ import annotations

from datetime import date, timedelta
from typing import cast
from uuid import uuid4

from google import genai
from google.genai.interactions import Interaction
from pydantic import BaseModel

from conditioner.core.domain.readiness.readiness import ReadinessScore
from conditioner.core.domain.workout.constraints import WorkoutConstraints
from conditioner.core.domain.workout.workout import Exercise, ExerciseModality, Session, Workout
from conditioner.core.interfaces.workout.workout_generation_provider import (
    WorkoutGenerationProvider,
)
from conditioner.shared.constants import GEMINI_WORKOUT_MODEL


class _ExerciseSchema(BaseModel):
    """Structured-output schema for a single generated exercise."""

    name: str
    modality: ExerciseModality
    sets: int | None = None
    reps: int | None = None
    duration_minutes: float | None = None
    target_load: float | None = None


class _SessionSchema(BaseModel):
    """Structured-output schema for a single generated session."""

    day_offset: int
    exercises: list[_ExerciseSchema]


class _WeeklyPlanSchema(BaseModel):
    """Structured-output schema for a generated weekly plan."""

    sessions: list[_SessionSchema]


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
            input=self._build_prompt(week_start, constraints, readiness),
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": _WeeklyPlanSchema.model_json_schema(),
            },
        )

        # Set the parsed plan from the model's JSON output; requests are always
        # non-streaming here, so the response is always a single Interaction
        output_text = cast(Interaction, interaction).output_text
        plan = _WeeklyPlanSchema.model_validate_json(output_text or "")

        # Return the generated weekly workout, mapped to domain objects
        return Workout(
            id=str(uuid4()),
            user_id=user_id,
            week_start=week_start,
            sessions=[self._to_session(week_start, session) for session in plan.sessions],
        )

    def _build_prompt(
        self, week_start: date, constraints: WorkoutConstraints, readiness: ReadinessScore
    ) -> str:
        """Build the text prompt describing this week's constraints and readiness."""

        return (
            f"Generate a weekly conditioning plan starting {week_start.isoformat()}.\n"
            f"Goal: {constraints.goal.value}.\n"
            f"Available equipment: {', '.join(constraints.equipment) or 'none'}.\n"
            f"Available minutes per weekday (0=Monday..6=Sunday): "
            f"{constraints.available_minutes_by_weekday}.\n"
            f"Current readiness: {readiness.score}/100 ({readiness.zone.value}).\n"
            "Only schedule sessions on weekdays with available minutes, and keep each "
            "session within its day's time budget."
        )

    def _to_session(self, week_start: date, session: _SessionSchema) -> Session:
        """Map a generated session schema to a domain Session."""

        return Session(
            id=str(uuid4()),
            date=week_start + timedelta(days=session.day_offset),
            exercises=[
                Exercise(
                    id=str(uuid4()),
                    name=exercise.name,
                    modality=exercise.modality,
                    sets=exercise.sets,
                    reps=exercise.reps,
                    duration_minutes=exercise.duration_minutes,
                    target_load=exercise.target_load,
                )
                for exercise in session.exercises
            ],
        )
