from __future__ import annotations

from datetime import date

from conditioner.core.adapters.persistence.d1.client import D1Client, JsonRow
from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.interfaces.fitness.fitness_level_repository import FitnessLevelRepository


class D1FitnessLevelRepository(FitnessLevelRepository):
    """Cloudflare D1-backed implementation of FitnessLevelRepository."""

    def __init__(self, client: D1Client) -> None:
        # Initializations
        self._client = client

    async def save(self, fitness_level: FitnessLevel) -> None:
        """Upsert a weekly fitness level assessment for a user."""

        await self._client.execute(
            """
            INSERT INTO fitness_levels (user_id, week_start, score)
            VALUES (?, ?, ?)
            ON CONFLICT (user_id, week_start) DO UPDATE SET
                score = excluded.score
            """,
            (fitness_level.user_id, fitness_level.week_start.isoformat(), fitness_level.score),
        )

    async def get_by_week(self, user_id: str, week_start: date) -> FitnessLevel | None:
        """Fetch a user's fitness level for a specific week."""

        # Get fitness level row for user and week
        rows = await self._client.query(
            "SELECT * FROM fitness_levels WHERE user_id = ? AND week_start = ?",
            (user_id, week_start.isoformat()),
        )
        return self._to_domain(rows[0]) if rows else None

    @staticmethod
    def _to_domain(row: JsonRow) -> FitnessLevel:
        """Map a result row to a FitnessLevel domain object."""

        # Return mapped fitness level domain object
        return FitnessLevel(
            user_id=row["user_id"],
            week_start=date.fromisoformat(row["week_start"]),
            score=row["score"],
        )
