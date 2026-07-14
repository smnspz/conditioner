from __future__ import annotations

from datetime import date

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.questionnaire import QuestionnaireResponse
from conditioner.core.interfaces.questionnaire_repository import QuestionnaireRepository


class SqliteQuestionnaireRepository(QuestionnaireRepository):
    """SQLite-backed implementation of QuestionnaireRepository."""

    def __init__(self, db_path: str) -> None:
        # Initializations
        self._db_path = db_path

    async def save(self, response: QuestionnaireResponse) -> None:
        """Upsert a user's daily questionnaire response."""

        async with connect(self._db_path) as conn:
            await conn.execute(
                """
                INSERT INTO questionnaire_responses
                    (user_id, date, fatigue, soreness, stress, sleep_quality, is_sick)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (user_id, date) DO UPDATE SET
                    fatigue = excluded.fatigue,
                    soreness = excluded.soreness,
                    stress = excluded.stress,
                    sleep_quality = excluded.sleep_quality,
                    is_sick = excluded.is_sick
                """,
                (
                    response.user_id,
                    response.date.isoformat(),
                    response.fatigue,
                    response.soreness,
                    response.stress,
                    response.sleep_quality,
                    int(response.is_sick),
                ),
            )
            await conn.commit()

    async def get_by_date(self, user_id: str, day: date) -> QuestionnaireResponse | None:
        """Fetch a user's questionnaire response for a specific date."""

        async with connect(self._db_path) as conn:
            # Get questionnaire row for user and date
            cursor = await conn.execute(
                "SELECT * FROM questionnaire_responses WHERE user_id = ? AND date = ?",
                (user_id, day.isoformat()),
            )

            # Get single result row
            row = await cursor.fetchone()

            # Return domain object or None
            return self._to_domain(row) if row else None

    @staticmethod
    def _to_domain(row: aiosqlite.Row) -> QuestionnaireResponse:
        """Map a database row to a QuestionnaireResponse domain object."""

        # Return mapped questionnaire domain object
        return QuestionnaireResponse(
            user_id=row["user_id"],
            date=date.fromisoformat(row["date"]),
            fatigue=row["fatigue"],
            soreness=row["soreness"],
            stress=row["stress"],
            sleep_quality=row["sleep_quality"],
            is_sick=bool(row["is_sick"]),
        )
