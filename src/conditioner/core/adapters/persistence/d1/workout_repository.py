from __future__ import annotations

from datetime import date
from typing import Any

from conditioner.core.adapters.persistence.d1.client import D1Client, JsonRow
from conditioner.core.domain.workout.workout import Block, BlockExercise, BlockType, Session, Workout
from conditioner.core.interfaces.workout.workout_repository import WorkoutRepository


class D1WorkoutRepository(WorkoutRepository):
    """Cloudflare D1-backed implementation of WorkoutRepository.

    Sessions and blocks are replaced wholesale on save, since a workout plan
    is authored and updated as a single aggregate rather than field-by-field.
    """

    def __init__(self, client: D1Client) -> None:
        # Initializations
        self._client = client

    async def save(self, workout: Workout) -> None:
        """Upsert a workout plan, replacing all sessions and blocks wholesale."""

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
                DELETE FROM block_exercises
                WHERE block_id IN (
                    SELECT b.id FROM blocks b
                    JOIN sessions s ON b.session_id = s.id
                    WHERE s.workout_id = ?
                )
                """,
                (workout.id,),
            ),
            (
                """
                DELETE FROM blocks
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
            for block_index, block in enumerate(session.blocks):
                statements.append(
                    (
                        """
                        INSERT INTO blocks (id, session_id, type, estimated_minutes, order_index)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (block.id, session.id, block.type.value, block.estimated_minutes, block_index),
                    )
                )
                for ex_index, exercise in enumerate(block.exercises):
                    statements.append(
                        (
                            """
                            INSERT INTO block_exercises
                                (id, block_id, exercise_id, exercise_name, sets, reps,
                                 duration_seconds, rest_seconds, intensity_cue, notes, order_index)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                exercise.id,
                                block.id,
                                exercise.exercise_id,
                                exercise.exercise_name,
                                exercise.sets,
                                exercise.reps,
                                exercise.duration_seconds,
                                exercise.rest_seconds,
                                exercise.intensity_cue,
                                exercise.notes,
                                ex_index,
                            ),
                        )
                    )

        await self._client.batch(statements)

    async def get_by_id(self, workout_id: str) -> Workout | None:
        """Fetch a workout plan by its unique ID, including all sessions and blocks."""

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
        """Reconstruct a full Workout aggregate from workout, sessions, blocks, and exercises rows."""

        # Get session rows for this workout
        session_rows = await self._client.query(
            "SELECT * FROM sessions WHERE workout_id = ? ORDER BY date", (workout_row["id"],)
        )

        # Accumulates built Session objects
        sessions: list[Session] = []
        for session_row in session_rows:
            # Get block rows for this session
            block_rows = await self._client.query(
                "SELECT * FROM blocks WHERE session_id = ? ORDER BY order_index",
                (session_row["id"],),
            )

            # Accumulates built Block objects
            blocks: list[Block] = []
            for block_row in block_rows:
                # Get exercise rows for this block
                ex_rows = await self._client.query(
                    "SELECT * FROM block_exercises WHERE block_id = ? ORDER BY order_index",
                    (block_row["id"],),
                )

                # Build block exercise domain objects
                exercises = [
                    BlockExercise(
                        id=ex["id"],
                        exercise_id=ex["exercise_id"],
                        exercise_name=ex["exercise_name"],
                        sets=ex["sets"],
                        reps=ex["reps"],
                        duration_seconds=ex["duration_seconds"],
                        rest_seconds=ex["rest_seconds"],
                        intensity_cue=ex["intensity_cue"],
                        notes=ex["notes"],
                    )
                    for ex in ex_rows
                ]

                blocks.append(
                    Block(
                        id=block_row["id"],
                        type=BlockType(block_row["type"]),
                        estimated_minutes=block_row["estimated_minutes"],
                        exercises=exercises,
                    )
                )

            sessions.append(
                Session(
                    id=session_row["id"],
                    date=date.fromisoformat(session_row["date"]),
                    blocks=blocks,
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
