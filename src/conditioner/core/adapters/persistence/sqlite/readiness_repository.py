from __future__ import annotations

from datetime import date

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.readiness import ReadinessScore, ReadinessZone
from conditioner.core.interfaces.readiness_repository import ReadinessRepository


class SqliteReadinessRepository(ReadinessRepository):
    """SQLite-backed implementation of ReadinessRepository."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def save(self, score: ReadinessScore) -> None:
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
        async with connect(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM readiness_scores WHERE user_id = ? AND date = ?",
                (user_id, day.isoformat()),
            )
            row = await cursor.fetchone()
            return self._to_domain(row) if row else None

    async def get_range(self, user_id: str, start: date, end: date) -> list[ReadinessScore]:
        async with connect(self._db_path) as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM readiness_scores
                WHERE user_id = ? AND date BETWEEN ? AND ?
                ORDER BY date
                """,
                (user_id, start.isoformat(), end.isoformat()),
            )
            rows = await cursor.fetchall()
            return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: aiosqlite.Row) -> ReadinessScore:
        return ReadinessScore(
            user_id=row["user_id"],
            date=date.fromisoformat(row["date"]),
            score=row["score"],
            zone=ReadinessZone(row["zone"]),
        )
