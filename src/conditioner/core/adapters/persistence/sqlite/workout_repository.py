from __future__ import annotations

from datetime import date

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.workout.workout import Exercise, ExerciseModality, Session, Workout
from conditioner.core.interfaces.workout.workout_repository import WorkoutRepository


class SqliteWorkoutRepository(WorkoutRepository):
    """SQLite-backed implementation of WorkoutRepository.

    Sessions and exercises are replaced wholesale on save, since a workout plan
    is authored and updated as a single aggregate rather than field-by-field.
    """

    def __init__(self, db_path: str) -> None:
        # Initializations
        self._db_path = db_path

    async def save(self, workout: Workout) -> None:
        """Upsert a workout plan, replacing all sessions and exercises wholesale."""

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
                for phase, exercises in (
                    ("warmup", session.warmup_exercises),
                    ("main", session.exercises),
                    ("cooldown", session.cooldown_exercises),
                ):
                    for exercise in exercises:
                        await conn.execute(
                            """
                            INSERT INTO exercises
                                (id, session_id, name, modality, sets, reps,
                                 duration_minutes, target_load, phase)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                                phase,
                            ),
                        )
            await conn.commit()

    async def get_by_id(self, workout_id: str) -> Workout | None:
        """Fetch a workout plan by its unique ID, including all sessions and exercises."""

        async with connect(self._db_path) as conn:
            # Get workout row by ID
            cursor = await conn.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,))

            # Get single result row
            row = await cursor.fetchone()
            if not row:
                return None

            # Return mapped workout domain object
            return await self._to_domain(conn, row)

    async def get_by_week(self, user_id: str, week_start: date) -> Workout | None:
        """Fetch a user's workout plan for a given week start date."""

        async with connect(self._db_path) as conn:
            # Get workout row for user and week
            cursor = await conn.execute(
                "SELECT * FROM workouts WHERE user_id = ? AND week_start = ?",
                (user_id, week_start.isoformat()),
            )

            # Get single result row
            row = await cursor.fetchone()
            if not row:
                return None

            # Return mapped workout domain object
            return await self._to_domain(conn, row)

    @staticmethod
    async def _to_domain(conn: aiosqlite.Connection, workout_row: aiosqlite.Row) -> Workout:
        """Reconstruct a full Workout aggregate from the workout, sessions, and exercises rows."""

        # Get session rows for this workout
        session_cursor = await conn.execute(
            "SELECT * FROM sessions WHERE workout_id = ? ORDER BY date", (workout_row["id"],)
        )

        # Get all session rows
        session_rows = await session_cursor.fetchall()

        # Accumulates built Session objects
        sessions: list[Session] = []
        for session_row in session_rows:
            # Get exercise rows for this session
            exercise_cursor = await conn.execute(
                "SELECT * FROM exercises WHERE session_id = ?", (session_row["id"],)
            )

            # Get all exercise rows
            exercise_rows = await exercise_cursor.fetchall()

            # Group exercises by phase, defaulting legacy rows to main
            warmup: list[Exercise] = []
            main: list[Exercise] = []
            cooldown: list[Exercise] = []
            for exercise_row in exercise_rows:
                exercise = Exercise(
                    id=exercise_row["id"],
                    name=exercise_row["name"],
                    modality=ExerciseModality(exercise_row["modality"]),
                    sets=exercise_row["sets"],
                    reps=exercise_row["reps"],
                    duration_minutes=exercise_row["duration_minutes"],
                    target_load=exercise_row["target_load"],
                )
                phase = exercise_row["phase"] if exercise_row["phase"] else "main"
                if phase == "warmup":
                    warmup.append(exercise)
                elif phase == "cooldown":
                    cooldown.append(exercise)
                else:
                    main.append(exercise)

            sessions.append(
                Session(
                    id=session_row["id"],
                    date=date.fromisoformat(session_row["date"]),
                    warmup_exercises=warmup,
                    exercises=main,
                    cooldown_exercises=cooldown,
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
