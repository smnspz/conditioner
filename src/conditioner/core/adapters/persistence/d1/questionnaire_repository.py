from __future__ import annotations

from datetime import date

from conditioner.core.adapters.persistence.d1.client import D1Client, JsonRow
from conditioner.core.domain.questionnaire.questionnaire import QuestionnaireResponse
from conditioner.core.interfaces.questionnaire.questionnaire_repository import (
    QuestionnaireRepository,
)


class D1QuestionnaireRepository(QuestionnaireRepository):
    """Cloudflare D1-backed implementation of QuestionnaireRepository."""

    def __init__(self, client: D1Client) -> None:
        # Initializations
        self._client = client

    async def save(self, response: QuestionnaireResponse) -> None:
        """Upsert a user's daily questionnaire response."""

        await self._client.execute(
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

    async def get_by_date(self, user_id: str, day: date) -> QuestionnaireResponse | None:
        """Fetch a user's questionnaire response for a specific date."""

        # Get questionnaire row for user and date
        rows = await self._client.query(
            "SELECT * FROM questionnaire_responses WHERE user_id = ? AND date = ?",
            (user_id, day.isoformat()),
        )
        return self._to_domain(rows[0]) if rows else None

    @staticmethod
    def _to_domain(row: JsonRow) -> QuestionnaireResponse:
        """Map a result row to a QuestionnaireResponse domain object."""

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
