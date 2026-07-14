from datetime import date as Date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from conditioner.api.dependencies import get_current_user_id, get_questionnaire_repository
from conditioner.core.domain.questionnaire import QuestionnaireResponse
from conditioner.core.interfaces.questionnaire_repository import QuestionnaireRepository

router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])


class QuestionnaireRequest(BaseModel):
    """Daily subjective questionnaire submission.

    Attributes:
        date: The day this response describes; defaults to today.
        fatigue: Perceived fatigue on waking, 0 (fresh) to 10 (exhausted).
        soreness: Muscle soreness/DOMS, 0 (none) to 10 (strong pain).
        stress: Mental/emotional stress, 0 (calm) to 10 (very high).
        sleep_quality: Perceived sleep quality, 0 (terrible) to 10 (excellent).
        is_sick: Whether the user flagged illness, cold, or joint pain.
    """

    date: Date = Field(default_factory=Date.today)
    fatigue: Annotated[int, Field(ge=0, le=10)]
    soreness: Annotated[int, Field(ge=0, le=10)]
    stress: Annotated[int, Field(ge=0, le=10)]
    sleep_quality: Annotated[int, Field(ge=0, le=10)]
    is_sick: bool = False


class QuestionnaireResponseOut(BaseModel):
    """Serialized questionnaire response returned to the client."""

    date: Date
    fatigue: int
    soreness: int
    stress: int
    sleep_quality: int
    is_sick: bool


@router.post("", response_model=QuestionnaireResponseOut, status_code=status.HTTP_201_CREATED)
async def submit(
    body: QuestionnaireRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repo: Annotated[QuestionnaireRepository, Depends(get_questionnaire_repository)],
) -> QuestionnaireResponseOut:
    """Submit or update the daily questionnaire for the authenticated user."""
    # Save questionnaire response to persistence
    await repo.save(
        QuestionnaireResponse(
            user_id=user_id,
            date=body.date,
            fatigue=body.fatigue,
            soreness=body.soreness,
            stress=body.stress,
            sleep_quality=body.sleep_quality,
            is_sick=body.is_sick,
        )
    )
    # Return the saved response
    return QuestionnaireResponseOut(
        date=body.date,
        fatigue=body.fatigue,
        soreness=body.soreness,
        stress=body.stress,
        sleep_quality=body.sleep_quality,
        is_sick=body.is_sick,
    )


@router.get("/{day}", response_model=QuestionnaireResponseOut)
async def get_by_date(
    day: Date,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repo: Annotated[QuestionnaireRepository, Depends(get_questionnaire_repository)],
) -> QuestionnaireResponseOut:
    """Fetch the authenticated user's questionnaire response for a given date."""
    # Get questionnaire response for the requested day
    response = await repo.get_by_date(user_id, day)
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No response for this date"
        )
    # Return the response
    return QuestionnaireResponseOut(
        date=response.date,
        fatigue=response.fatigue,
        soreness=response.soreness,
        stress=response.stress,
        sleep_quality=response.sleep_quality,
        is_sick=response.is_sick,
    )
