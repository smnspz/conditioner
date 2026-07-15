from datetime import date as Date

from pydantic import BaseModel


class ExerciseOut(BaseModel):
    """Serialized exercise returned to the client."""

    id: str
    name: str
    modality: str
    sets: int | None
    reps: int | None
    duration_minutes: float | None
    target_load: float | None


class SessionOut(BaseModel):
    """Serialized session returned to the client."""

    id: str
    date: Date
    exercises: list[ExerciseOut]
    completed: bool


class WorkoutOut(BaseModel):
    """Serialized weekly workout plan returned to the client."""

    id: str
    week_start: Date
    sessions: list[SessionOut]
