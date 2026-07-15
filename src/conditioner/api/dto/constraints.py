from typing import Annotated

from pydantic import BaseModel, Field

from conditioner.core.domain.workout.constraints import TrainingGoal


class WorkoutConstraintsRequest(BaseModel):
    """Workout constraints submission.

    Attributes:
        equipment: The equipment the user has available to train with.
        goal: The user's training objective.
        available_minutes_by_weekday: Minutes available to train on each weekday,
            keyed 0 (Monday) through 6 (Sunday). Missing keys mean no session that day.
    """

    equipment: list[str]
    goal: TrainingGoal
    available_minutes_by_weekday: dict[Annotated[int, Field(ge=0, le=6)], int] = {}


class WorkoutConstraintsOut(BaseModel):
    """Serialized workout constraints returned to the client."""

    equipment: list[str]
    goal: TrainingGoal
    available_minutes_by_weekday: dict[int, int]
