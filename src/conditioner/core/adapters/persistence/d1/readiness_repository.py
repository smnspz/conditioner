from __future__ import annotations

from datetime import date

from conditioner.core.adapters.persistence.d1.client import D1Client, JsonRow
from conditioner.core.domain.readiness.readiness import ReadinessScore, ReadinessZone
from conditioner.core.interfaces.readiness.readiness_repository import ReadinessRepository


class D1ReadinessRepository(ReadinessRepository):
    """Cloudflare D1-backed implementation of ReadinessRepository."""

    def __init__(self, client: D1Client) -> None:
        # Initializations
        self._client = client

    async def save(self, score: ReadinessScore) -> None:
        """Upsert a daily readiness score for a user."""

        await self._client.execute(
            """
            INSERT INTO readiness_scores (user_id, date, score, zone)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (user_id, date) DO UPDATE SET
                score = excluded.score,
                zone = excluded.zone
            """,
            (score.user_id, score.date.isoformat(), score.score, score.zone.value),
        )

    async def get_by_date(self, user_id: str, day: date) -> ReadinessScore | None:
        """Fetch a user's readiness score for a specific date."""

        # Get readiness row for user and date
        rows = await self._client.query(
            "SELECT * FROM readiness_scores WHERE user_id = ? AND date = ?",
            (user_id, day.isoformat()),
        )
        return self._to_domain(rows[0]) if rows else None

    async def get_range(self, user_id: str, start: date, end: date) -> list[ReadinessScore]:
        """Fetch readiness scores for an inclusive date range, ordered by date."""

        # Get readiness rows for the date range
        rows = await self._client.query(
            """
            SELECT * FROM readiness_scores
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date
            """,
            (user_id, start.isoformat(), end.isoformat()),
        )
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: JsonRow) -> ReadinessScore:
        """Map a result row to a ReadinessScore domain object."""

        # Return mapped readiness score domain object
        return ReadinessScore(
            user_id=row["user_id"],
            date=date.fromisoformat(row["date"]),
            score=row["score"],
            zone=ReadinessZone(row["zone"]),
        )
