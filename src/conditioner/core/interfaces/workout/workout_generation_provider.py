from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from conditioner.core.domain.readiness.readiness import ReadinessScore
from conditioner.core.domain.workout.constraints import WorkoutConstraints
from conditioner.core.domain.workout.workout import Workout


class WorkoutGenerationProvider(ABC):
    """Port for generating a weekly workout plan from a generative AI engine."""

    @abstractmethod
    async def generate_weekly_plan(
        self,
        user_id: str,
        week_start: date,
        constraints: WorkoutConstraints,
        readiness: ReadinessScore,
    ) -> Workout:
        """Generate a weekly workout plan tailored to the user's constraints and readiness."""
