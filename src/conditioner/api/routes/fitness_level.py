from datetime import date as Date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from conditioner.api.dependencies import get_current_user_id, get_fitness_level_repository
from conditioner.api.dto.fitness_level import FitnessLevelOut, FitnessLevelRequest
from conditioner.core.interfaces.fitness.fitness_level_repository import FitnessLevelRepository

router = APIRouter(prefix="/fitness-level", tags=["fitness-level"])


@router.put("/{week_start}", response_model=FitnessLevelOut)
async def upsert_fitness_level(
    week_start: Date,
    body: FitnessLevelRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    fitness_level_repository: Annotated[
        FitnessLevelRepository, Depends(get_fitness_level_repository)
    ],
) -> FitnessLevelOut:
    """Set or update the authenticated user's fitness level for the given week."""

    # Save the fitness level assessment
    fitness_level = body.to_domain(user_id, week_start)
    await fitness_level_repository.save(fitness_level)

    # Return the saved fitness level
    return FitnessLevelOut.from_domain(fitness_level)


@router.get("/{week_start}", response_model=FitnessLevelOut)
async def get_fitness_level(
    week_start: Date,
    user_id: Annotated[str, Depends(get_current_user_id)],
    fitness_level_repository: Annotated[
        FitnessLevelRepository, Depends(get_fitness_level_repository)
    ],
) -> FitnessLevelOut:
    """Fetch the authenticated user's fitness level for the given week."""

    # Get the fitness level for this week
    fitness_level = await fitness_level_repository.get_by_week(user_id, week_start)
    if fitness_level is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fitness level set for this week",
        )

    # Return the fitness level
    return FitnessLevelOut.from_domain(fitness_level)
