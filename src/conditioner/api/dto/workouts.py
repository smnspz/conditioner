from __future__ import annotations

from datetime import date as Date

from pydantic import BaseModel

from conditioner.core.domain.workout.workout import Block, BlockExercise, Session, Workout


class BlockExerciseOut(BaseModel):
    """Serialized block exercise returned to the client."""

    id: str
    exercise_id: str
    exercise_name: str
    sets: int
    reps: int | None
    duration_seconds: int | None
    rest_seconds: int
    intensity_cue: str
    notes: str

    @classmethod
    def from_domain(cls, exercise: BlockExercise) -> BlockExerciseOut:
        """Build from a domain BlockExercise."""

        return cls(
            id=exercise.id,
            exercise_id=exercise.exercise_id,
            exercise_name=exercise.exercise_name,
            sets=exercise.sets,
            reps=exercise.reps,
            duration_seconds=exercise.duration_seconds,
            rest_seconds=exercise.rest_seconds,
            intensity_cue=exercise.intensity_cue,
            notes=exercise.notes,
        )


class BlockOut(BaseModel):
    """Serialized session block returned to the client."""

    id: str
    type: str
    estimated_minutes: int
    exercises: list[BlockExerciseOut]

    @classmethod
    def from_domain(cls, block: Block) -> BlockOut:
        """Build from a domain Block."""

        return cls(
            id=block.id,
            type=block.type.value,
            estimated_minutes=block.estimated_minutes,
            exercises=[BlockExerciseOut.from_domain(ex) for ex in block.exercises],
        )


class SessionOut(BaseModel):
    """Serialized session returned to the client."""

    id: str
    date: Date
    blocks: list[BlockOut]
    completed: bool

    @classmethod
    def from_domain(cls, session: Session) -> SessionOut:
        """Build from a domain Session."""

        return cls(
            id=session.id,
            date=session.date,
            blocks=[BlockOut.from_domain(b) for b in session.blocks],
            completed=session.completed,
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
