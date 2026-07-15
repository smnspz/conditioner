from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints


class WorkoutConstraintsRequest(BaseModel):
    """Workout constraints submission.

    Attributes:
        equipment: The equipment the user has available to train with.
        goal: The user's training objective.
        available_minutes_by_weekday: Minutes available to train on each weekday,
            keyed 0 (Monday) through 6 (Sunday). Missing keys mean no session that day.
        initial_perceived_fitness: Self-reported fitness level on a 1–10 scale.
            Used as the readiness proxy for the first workout generation, before any
            computed readiness scores exist. Optional; can be updated later.
    """

    equipment: list[str]
    goal: TrainingGoal
    available_minutes_by_weekday: dict[Annotated[int, Field(ge=0, le=6)], int] = {}
    initial_perceived_fitness: Annotated[int, Field(ge=1, le=10)] | None = None

    def to_domain(self, user_id: str) -> WorkoutConstraints:
        """Build a domain WorkoutConstraints for the given user."""

        return WorkoutConstraints(
            user_id=user_id,
            equipment=self.equipment,
            goal=self.goal,
            available_minutes_by_weekday=self.available_minutes_by_weekday,
            initial_perceived_fitness=self.initial_perceived_fitness,
        )


class WorkoutConstraintsOut(BaseModel):
    """Serialized workout constraints returned to the client."""

    equipment: list[str]
    goal: TrainingGoal
    available_minutes_by_weekday: dict[int, int]
    initial_perceived_fitness: int | None

    @classmethod
    def from_domain(cls, constraints: WorkoutConstraints) -> WorkoutConstraintsOut:
        """Build from a domain WorkoutConstraints."""

        return cls(
            equipment=constraints.equipment,
            goal=constraints.goal,
            available_minutes_by_weekday=constraints.available_minutes_by_weekday,
            initial_perceived_fitness=constraints.initial_perceived_fitness,
        )
