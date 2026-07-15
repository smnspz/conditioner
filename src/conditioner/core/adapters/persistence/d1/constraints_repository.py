from __future__ import annotations

import json

from conditioner.core.adapters.persistence.d1.client import D1Client, JsonRow
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.interfaces.workout.constraints_repository import ConstraintsRepository


class D1ConstraintsRepository(ConstraintsRepository):
    """Cloudflare D1-backed implementation of ConstraintsRepository."""

    def __init__(self, client: D1Client) -> None:
        # Initializations
        self._client = client

    async def save(self, constraints: WorkoutConstraints) -> None:
        """Upsert workout constraints for a user."""

        await self._client.execute(
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

    async def get_by_user_id(self, user_id: str) -> WorkoutConstraints | None:
        """Fetch stored workout constraints for a user."""

        # Get constraints row for this user
        rows = await self._client.query(
            "SELECT * FROM workout_constraints WHERE user_id = ?", (user_id,)
        )
        return self._to_domain(rows[0]) if rows else None

    def _to_domain(self, row: JsonRow) -> WorkoutConstraints:
        """Map a result row to a WorkoutConstraints domain object."""

        # Return constraints domain object
        return WorkoutConstraints(
            user_id=row["user_id"],
            equipment=row["equipment"].split(",") if row["equipment"] else [],
            goal=TrainingGoal(row["goal"]),
            available_minutes_by_weekday={
                int(k): v for k, v in json.loads(row["available_minutes_by_weekday"]).items()
            },
            initial_perceived_fitness=row.get("initial_perceived_fitness"),
            include_warmup_cooldown=bool(row.get("include_warmup_cooldown", 0)),
        )
