from datetime import UTC, date, datetime

from conditioner.core.adapters.persistence.sqlite.questionnaire_repository import (
    SqliteQuestionnaireRepository,
)
from conditioner.core.adapters.persistence.sqlite.user_repository import SqliteUserRepository
from conditioner.core.domain.auth.user import User
from conditioner.core.domain.questionnaire.questionnaire import QuestionnaireResponse


async def _seed_user(db_path: str, user_id: str) -> None:
    await SqliteUserRepository(db_path).save(
        User(id=user_id, email=f"{user_id}@example.com", created_at=datetime.now(UTC))
    )


async def test_save_and_get_by_date_round_trips(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteQuestionnaireRepository(db_path)
    response = QuestionnaireResponse(
        user_id="user-1",
        date=date(2026, 1, 1),
        fatigue=3,
        soreness=2,
        stress=4,
        sleep_quality=8,
        is_sick=False,
    )

    await repo.save(response)

    assert await repo.get_by_date("user-1", date(2026, 1, 1)) == response


async def test_save_upserts_existing_response(db_path: str) -> None:
    await _seed_user(db_path, "user-1")
    repo = SqliteQuestionnaireRepository(db_path)
    await repo.save(
        QuestionnaireResponse(
            user_id="user-1",
            date=date(2026, 1, 1),
            fatigue=3,
            soreness=2,
            stress=4,
            sleep_quality=8,
        )
    )

    updated = QuestionnaireResponse(
        user_id="user-1",
        date=date(2026, 1, 1),
        fatigue=7,
        soreness=6,
        stress=8,
        sleep_quality=3,
        is_sick=True,
    )
    await repo.save(updated)

    assert await repo.get_by_date("user-1", date(2026, 1, 1)) == updated


async def test_get_by_date_returns_none_when_missing(db_path: str) -> None:
    repo = SqliteQuestionnaireRepository(db_path)
    assert await repo.get_by_date("missing", date(2026, 1, 1)) is None
