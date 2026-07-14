from __future__ import annotations

from datetime import date

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.workout import Exercise, ExerciseModality, Session, Workout
from conditioner.core.interfaces.workout_repository import WorkoutRepository


class SqliteWorkoutRepository(WorkoutRepository):
    """SQLite-backed implementation of WorkoutRepository.

    Sessions and exercises are replaced wholesale on save, since a workout plan
    is authored and updated as a single aggregate rather than field-by-field.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def save(self, workout: Workout) -> None:
        async with connect(self._db_path) as conn:
            await conn.execute(
                """
                INSERT INTO workouts (id, user_id, week_start)
                VALUES (?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = excluded.user_id,
                    week_start = excluded.week_start
                """,
                (workout.id, workout.user_id, workout.week_start.isoformat()),
            )
            await conn.execute(
                """
                DELETE FROM exercises
                WHERE session_id IN (SELECT id FROM sessions WHERE workout_id = ?)
                """,
                (workout.id,),
            )
            await conn.execute("DELETE FROM sessions WHERE workout_id = ?", (workout.id,))
            for session in workout.sessions:
                await conn.execute(
                    "INSERT INTO sessions (id, workout_id, date, completed) VALUES (?, ?, ?, ?)",
                    (session.id, workout.id, session.date.isoformat(), int(session.completed)),
                )
                for exercise in session.exercises:
                    await conn.execute(
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
            await conn.commit()

    async def get_by_id(self, workout_id: str) -> Workout | None:
        async with connect(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return await self._to_domain(conn, row)

    async def get_by_week(self, user_id: str, week_start: date) -> Workout | None:
        async with connect(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM workouts WHERE user_id = ? AND week_start = ?",
                (user_id, week_start.isoformat()),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return await self._to_domain(conn, row)

    @staticmethod
    async def _to_domain(conn: aiosqlite.Connection, workout_row: aiosqlite.Row) -> Workout:
        session_cursor = await conn.execute(
            "SELECT * FROM sessions WHERE workout_id = ? ORDER BY date", (workout_row["id"],)
        )
        session_rows = await session_cursor.fetchall()

        sessions: list[Session] = []
        for session_row in session_rows:
            exercise_cursor = await conn.execute(
                "SELECT * FROM exercises WHERE session_id = ?", (session_row["id"],)
            )
            exercise_rows = await exercise_cursor.fetchall()
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

        return Workout(
            id=workout_row["id"],
            user_id=workout_row["user_id"],
            week_start=date.fromisoformat(workout_row["week_start"]),
            sessions=sessions,
        )
