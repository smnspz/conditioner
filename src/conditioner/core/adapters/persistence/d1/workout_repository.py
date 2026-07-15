from __future__ import annotations

from datetime import date
from typing import Any

from conditioner.core.adapters.persistence.d1.client import D1Client, JsonRow
from conditioner.core.domain.workout.workout import Exercise, ExerciseModality, Session, Workout
from conditioner.core.interfaces.workout.workout_repository import WorkoutRepository


class D1WorkoutRepository(WorkoutRepository):
    """Cloudflare D1-backed implementation of WorkoutRepository.

    Sessions and exercises are replaced wholesale on save, since a workout plan
    is authored and updated as a single aggregate rather than field-by-field.
    """

    def __init__(self, client: D1Client) -> None:
        # Initializations
        self._client = client

    async def save(self, workout: Workout) -> None:
        """Upsert a workout plan, replacing all sessions and exercises wholesale."""

        # Accumulates one atomic batch of upsert/delete/insert statements
        statements: list[tuple[str, tuple[Any, ...]]] = [
            (
                """
                INSERT INTO workouts (id, user_id, week_start)
                VALUES (?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = excluded.user_id,
                    week_start = excluded.week_start
                """,
                (workout.id, workout.user_id, workout.week_start.isoformat()),
            ),
            (
                """
                DELETE FROM exercises
                WHERE session_id IN (SELECT id FROM sessions WHERE workout_id = ?)
                """,
                (workout.id,),
            ),
            ("DELETE FROM sessions WHERE workout_id = ?", (workout.id,)),
        ]
        for session in workout.sessions:
            statements.append(
                (
                    "INSERT INTO sessions (id, workout_id, date, completed) VALUES (?, ?, ?, ?)",
                    (session.id, workout.id, session.date.isoformat(), int(session.completed)),
                )
            )
            for exercise in session.exercises:
                statements.append(
                    (
                        """
                        INSERT INTO exercises
                            (id, session_id, name, modality, sets, reps,
                             duration_minutes, target_load)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            exercise.id,
                            session.id,
                            exercise.name,
                            exercise.modality.value,
                            exercise.sets,
                            exercise.reps,
                            exercise.duration_minutes,
                            exercise.target_load,
                        ),
                    )
                )

        await self._client.batch(statements)

    async def get_by_id(self, workout_id: str) -> Workout | None:
        """Fetch a workout plan by its unique ID, including all sessions and exercises."""

        # Get workout row by ID
        rows = await self._client.query("SELECT * FROM workouts WHERE id = ?", (workout_id,))
        return await self._to_domain(rows[0]) if rows else None

    async def get_by_week(self, user_id: str, week_start: date) -> Workout | None:
        """Fetch a user's workout plan for a given week start date."""

        # Get workout row for user and week
        rows = await self._client.query(
            "SELECT * FROM workouts WHERE user_id = ? AND week_start = ?",
            (user_id, week_start.isoformat()),
        )
        return await self._to_domain(rows[0]) if rows else None

    async def _to_domain(self, workout_row: JsonRow) -> Workout:
        """Reconstruct a full Workout aggregate from the workout, sessions, and exercises rows."""

        # Get session rows for this workout
        session_rows = await self._client.query(
            "SELECT * FROM sessions WHERE workout_id = ? ORDER BY date", (workout_row["id"],)
        )

        # Accumulates built Session objects
        sessions: list[Session] = []
        for session_row in session_rows:
            # Get exercise rows for this session
            exercise_rows = await self._client.query(
                "SELECT * FROM exercises WHERE session_id = ?", (session_row["id"],)
            )

            # Build Exercise objects from rows
            exercises = [
                Exercise(
                    id=exercise_row["id"],
                    name=exercise_row["name"],
                    modality=ExerciseModality(exercise_row["modality"]),
                    sets=exercise_row["sets"],
                    reps=exercise_row["reps"],
                    duration_minutes=exercise_row["duration_minutes"],
                    target_load=exercise_row["target_load"],
                )
                for exercise_row in exercise_rows
            ]
            sessions.append(
                Session(
                    id=session_row["id"],
                    date=date.fromisoformat(session_row["date"]),
                    exercises=exercises,
                    completed=bool(session_row["completed"]),
                )
            )

        # Return fully reconstructed workout aggregate
        return Workout(
            id=workout_row["id"],
            user_id=workout_row["user_id"],
            week_start=date.fromisoformat(workout_row["week_start"]),
            sessions=sessions,
        )
