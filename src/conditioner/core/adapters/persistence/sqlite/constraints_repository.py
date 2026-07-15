from __future__ import annotations

import json

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.interfaces.workout.constraints_repository import ConstraintsRepository


class SqliteConstraintsRepository(ConstraintsRepository):
    """SQLite-backed implementation of ConstraintsRepository."""

    def __init__(self, db_path: str) -> None:
        # Initializations
        self._db_path = db_path

    async def save(self, constraints: WorkoutConstraints) -> None:
        """Upsert workout constraints for a user."""

        async with connect(self._db_path) as conn:
            await conn.execute(
                """
                INSERT INTO workout_constraints
                    (user_id, equipment, goal, available_minutes_by_weekday,
                     initial_perceived_fitness, include_warmup_cooldown)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (user_id) DO UPDATE SET
                    equipment = excluded.equipment,
                    goal = excluded.goal,
                    available_minutes_by_weekday = excluded.available_minutes_by_weekday,
                    initial_perceived_fitness = excluded.initial_perceived_fitness,
                    include_warmup_cooldown = excluded.include_warmup_cooldown
                """,
                (
                    constraints.user_id,
                    ",".join(constraints.equipment),
                    constraints.goal.value,
                    json.dumps(constraints.available_minutes_by_weekday),
                    constraints.initial_perceived_fitness,
                    int(constraints.include_warmup_cooldown),
                ),
            )
            await conn.commit()

    async def get_by_user_id(self, user_id: str) -> WorkoutConstraints | None:
        """Fetch stored workout constraints for a user."""

        async with connect(self._db_path) as conn:
            # Get constraints row for this user
            cursor = await conn.execute(
                "SELECT * FROM workout_constraints WHERE user_id = ?", (user_id,)
            )

            # Get single result row
            row = await cursor.fetchone()

            # Return domain object or None
            return self._to_domain(row) if row else None

    def _to_domain(self, row: aiosqlite.Row) -> WorkoutConstraints:
        """Map a database row to a WorkoutConstraints domain object."""

        # Return constraints domain object
        return WorkoutConstraints(
            user_id=row["user_id"],
            equipment=row["equipment"].split(",") if row["equipment"] else [],
            goal=TrainingGoal(row["goal"]),
            available_minutes_by_weekday={
                int(k): v for k, v in json.loads(row["available_minutes_by_weekday"]).items()
            },
            initial_perceived_fitness=row["initial_perceived_fitness"],
            include_warmup_cooldown=bool(row["include_warmup_cooldown"]),
        )
