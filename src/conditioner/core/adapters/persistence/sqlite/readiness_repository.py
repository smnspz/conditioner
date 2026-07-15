from __future__ import annotations

from datetime import date

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.interfaces.readiness.readiness_repository import ReadinessRepository


class SqliteReadinessRepository(ReadinessRepository):
    """SQLite-backed implementation of ReadinessRepository."""

    def __init__(self, db_path: str) -> None:
        # Initializations
        self._db_path = db_path

    async def save(self, score: ReadinessScore) -> None:
        """Upsert a daily readiness score for a user."""

        async with connect(self._db_path) as conn:
            await conn.execute(
                """
                INSERT INTO readiness_scores (user_id, date, score, zone)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (user_id, date) DO UPDATE SET
                    score = excluded.score,
                    zone = excluded.zone
                """,
                (score.user_id, score.date.isoformat(), score.score, score.zone.value),
            )
            await conn.commit()

    async def get_by_date(self, user_id: str, day: date) -> ReadinessScore | None:
        """Fetch a user's readiness score for a specific date."""

        async with connect(self._db_path) as conn:
            # Get readiness row for user and date
            cursor = await conn.execute(
                "SELECT * FROM readiness_scores WHERE user_id = ? AND date = ?",
                (user_id, day.isoformat()),
            )

            # Get single result row
            row = await cursor.fetchone()

            # Return domain object or None
            return self._to_domain(row) if row else None

    async def get_range(self, user_id: str, start: date, end: date) -> list[ReadinessScore]:
        """Fetch readiness scores for an inclusive date range, ordered by date."""

        async with connect(self._db_path) as conn:
            # Get readiness rows for the date range
            cursor = await conn.execute(
                """
                SELECT * FROM readiness_scores
                WHERE user_id = ? AND date BETWEEN ? AND ?
                ORDER BY date
                """,
                (user_id, start.isoformat(), end.isoformat()),
            )

            # Get all result rows
            rows = await cursor.fetchall()

            # Return list of domain objects
            return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: aiosqlite.Row) -> ReadinessScore:
        """Map a database row to a ReadinessScore domain object."""

        # Return mapped readiness score domain object
        return ReadinessScore(
            user_id=row["user_id"],
            date=date.fromisoformat(row["date"]),
            score=row["score"],
            zone=ReadinessZone(row["zone"]),
        )
