from datetime import date as Date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from conditioner.api.dependencies import get_current_user_id, get_questionnaire_repository
from conditioner.api.dto.questionnaire import QuestionnaireRequest, QuestionnaireResponseOut
from conditioner.core.interfaces.questionnaire.questionnaire_repository import (
    QuestionnaireRepository,
)

router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])


@router.post("", response_model=QuestionnaireResponseOut, status_code=status.HTTP_201_CREATED)
async def submit(
    body: QuestionnaireRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repo: Annotated[QuestionnaireRepository, Depends(get_questionnaire_repository)],
) -> QuestionnaireResponseOut:
    """Submit or update the daily questionnaire for the authenticated user."""

    # Save questionnaire response to persistence
    response = body.to_domain(user_id)
    await repo.save(response)

    # Return the saved response
    return QuestionnaireResponseOut.from_domain(response)


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

    # Return serialized questionnaire response
    return QuestionnaireResponseOut.from_domain(response)
