from typing import Annotated

from fastapi import APIRouter, Depends

from conditioner.api.dependencies import get_exercise_catalog_repository
from conditioner.api.dto.exercise_catalog import ExerciseCatalogEntryOut
from conditioner.core.interfaces.workout.exercise_catalog_repository import (
    ExerciseCatalogRepository,
)

router = APIRouter(prefix="/exercise-catalog", tags=["exercise-catalog"])


@router.get("", response_model=list[ExerciseCatalogEntryOut])
async def list_all(
    repo: Annotated[ExerciseCatalogRepository, Depends(get_exercise_catalog_repository)],
    gear: list[str] | None = None,
) -> list[ExerciseCatalogEntryOut]:
    """List the exercise catalog, optionally filtered to gear the user has available."""

    if gear:
        # Get gear-filtered entries
        entries = await repo.filter_by_gear(gear)
    else:
        # Get full catalog
        entries = await repo.list_all()

    # Return serialized catalog entries
    return [ExerciseCatalogEntryOut.from_domain(e) for e in entries]
