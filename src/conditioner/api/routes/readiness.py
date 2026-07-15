from datetime import date as Date
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from conditioner.api.dependencies import (
    get_current_user_id,
    get_metrics_repository,
    get_questionnaire_repository,
    get_readiness_repository,
)
from conditioner.api.dto.readiness import ReadinessScoreOut
from conditioner.core.interfaces.questionnaire.questionnaire_repository import (
    QuestionnaireRepository,
)
from conditioner.core.interfaces.readiness.readiness_repository import ReadinessRepository
from conditioner.core.interfaces.wearables.metrics_repository import MetricsRepository
from conditioner.core.services.readiness.baseline import (
    CHRONIC_LOAD_WINDOW_DAYS,
    acute_chronic_load_ratio,
    compute_baseline,
    consecutive_training_days,
)
from conditioner.core.services.readiness.readiness import compute_readiness

router = APIRouter(prefix="/readiness", tags=["readiness"])


@router.get("/{day}", response_model=ReadinessScoreOut)
async def get_by_date(
    day: Date,
    user_id: Annotated[str, Depends(get_current_user_id)],
    readiness_repository: Annotated[ReadinessRepository, Depends(get_readiness_repository)],
    metrics_repository: Annotated[MetricsRepository, Depends(get_metrics_repository)],
    questionnaire_repository: Annotated[
        QuestionnaireRepository, Depends(get_questionnaire_repository)
    ],
) -> ReadinessScoreOut:
    """Fetch the authenticated user's readiness score for a day, computing it if needed."""

    # Get cached readiness score for this day, if already computed
    cached = await readiness_repository.get_by_date(user_id, day)
    if cached is not None:
        return ReadinessScoreOut.from_domain(cached)

    # Get today's wearable metrics and questionnaire response
    metrics = await metrics_repository.get_by_date(user_id, day)
    questionnaire = await questionnaire_repository.get_by_date(user_id, day)
    if metrics is None or questionnaire is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not enough data to compute readiness for this date",
        )

    # Get metrics history for baseline and training load calculations
    history = await metrics_repository.get_range(
        user_id, day - timedelta(days=CHRONIC_LOAD_WINDOW_DAYS), day - timedelta(days=1)
    )

    # Set computed readiness score
    score = compute_readiness(
        user_id,
        metrics,
        questionnaire,
        compute_baseline(history),
        consecutive_training_days(history),
        acute_chronic_load_ratio(history),
    )

    # Save computed score for future lookups
    await readiness_repository.save(score)

    # Return computed readiness score
    return ReadinessScoreOut.from_domain(score)
