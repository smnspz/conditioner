from __future__ import annotations

from datetime import date as Date

from pydantic import BaseModel

from conditioner.core.domain.workout.workout import Exercise, Session, Workout


class ExerciseOut(BaseModel):
    """Serialized exercise returned to the client."""

    id: str
    name: str
    modality: str
    sets: int | None
    reps: int | None
    duration_minutes: float | None
    target_load: float | None

    @classmethod
    def from_domain(cls, exercise: Exercise) -> ExerciseOut:
        """Build from a domain Exercise."""

        return cls(
            id=exercise.id,
            name=exercise.name,
            modality=exercise.modality.value,
            sets=exercise.sets,
            reps=exercise.reps,
            duration_minutes=exercise.duration_minutes,
            target_load=exercise.target_load,
        )


class SessionOut(BaseModel):
    """Serialized session returned to the client."""

    id: str
    date: Date
    exercises: list[ExerciseOut]
    completed: bool

    @classmethod
    def from_domain(cls, session: Session) -> SessionOut:
        """Build from a domain Session."""

        return cls(
            id=session.id,
            date=session.date,
            completed=session.completed,
            exercises=[ExerciseOut.from_domain(exercise) for exercise in session.exercises],
        )


class WorkoutOut(BaseModel):
    """Serialized weekly workout plan returned to the client."""

    id: str
    week_start: Date
    sessions: list[SessionOut]

    @classmethod
    def from_domain(cls, workout: Workout) -> WorkoutOut:
        """Build from a domain Workout."""

        return cls(
            id=workout.id,
            week_start=workout.week_start,
            sessions=[SessionOut.from_domain(session) for session in workout.sessions],
        )
