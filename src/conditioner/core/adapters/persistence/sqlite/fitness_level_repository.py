from __future__ import annotations

from datetime import date

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.fitness.fitness_level import FitnessLevel
from conditioner.core.interfaces.fitness.fitness_level_repository import FitnessLevelRepository


class SqliteFitnessLevelRepository(FitnessLevelRepository):
    """SQLite-backed implementation of FitnessLevelRepository."""

    def __init__(self, db_path: str) -> None:
        # Initializations
        self._db_path = db_path

    async def save(self, fitness_level: FitnessLevel) -> None:
        """Upsert a weekly fitness level assessment for a user."""

        async with connect(self._db_path) as conn:
            await conn.execute(
                """
                INSERT INTO fitness_levels (user_id, week_start, score)
                VALUES (?, ?, ?)
                ON CONFLICT (user_id, week_start) DO UPDATE SET
                    score = excluded.score
                """,
                (fitness_level.user_id, fitness_level.week_start.isoformat(), fitness_level.score),
            )
            await conn.commit()

    async def get_by_week(self, user_id: str, week_start: date) -> FitnessLevel | None:
        """Fetch a user's fitness level for a specific week."""

        async with connect(self._db_path) as conn:
            # Get fitness level row for user and week
            cursor = await conn.execute(
                "SELECT * FROM fitness_levels WHERE user_id = ? AND week_start = ?",
                (user_id, week_start.isoformat()),
            )

            # Get single result row
            row = await cursor.fetchone()

            # Return domain object or None
            return self._to_domain(row) if row else None

    @staticmethod
    def _to_domain(row: aiosqlite.Row) -> FitnessLevel:
        """Map a database row to a FitnessLevel domain object."""

        # Return mapped fitness level domain object
        return FitnessLevel(
            user_id=row["user_id"],
            week_start=date.fromisoformat(row["week_start"]),
            score=row["score"],
        )
