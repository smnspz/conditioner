from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from conditioner.core.domain.fitness.fitness_level import FitnessLevel
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
        fitness_level: FitnessLevel,
        readiness: ReadinessScore | None,
    ) -> Workout:
        """Generate a weekly workout plan tailored to the user's constraints, fitness level,
        and readiness.

        fitness_level is the weekly self-reported assessment (1–10) that drives exercise
        difficulty and complexity. readiness is the daily computed score (0–100) that
        adjusts volume and intensity within that difficulty tier. readiness may be None
        for a user's very first generation before any wearable/questionnaire data exists.
        """
