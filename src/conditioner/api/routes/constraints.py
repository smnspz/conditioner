from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from conditioner.api.dependencies import (
    get_constraints_repository,
    get_current_user_id,
    get_equipment_repository,
)
from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints
from conditioner.core.interfaces.workout.constraints_repository import ConstraintsRepository
from conditioner.core.interfaces.workout.equipment_repository import EquipmentRepository

router = APIRouter(prefix="/constraints", tags=["constraints"])


class WorkoutConstraintsRequest(BaseModel):
    """Workout constraints submission.

    Attributes:
        equipment: The equipment the user has available to train with.
        goal: The user's training objective.
        available_minutes_by_weekday: Minutes available to train on each weekday,
            keyed 0 (Monday) through 6 (Sunday). Missing keys mean no session that day.
    """

    equipment: list[str]
    goal: TrainingGoal
    available_minutes_by_weekday: dict[Annotated[int, Field(ge=0, le=6)], int] = {}


class WorkoutConstraintsOut(BaseModel):
    """Serialized workout constraints returned to the client."""

    equipment: list[str]
    goal: TrainingGoal
    available_minutes_by_weekday: dict[int, int]


@router.put("", response_model=WorkoutConstraintsOut)
async def upsert(
    body: WorkoutConstraintsRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    repo: Annotated[ConstraintsRepository, Depends(get_constraints_repository)],
    equipment_repo: Annotated[EquipmentRepository, Depends(get_equipment_repository)],
) -> WorkoutConstraintsOut:
    """Create or update the authenticated user's workout constraints."""

    # Get catalog entries matching the submitted equipment ids, to validate them
    matched = await equipment_repo.get_by_ids(body.equipment)
    unknown = set(body.equipment) - {item.id for item in matched}
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown equipment id(s): {', '.join(sorted(unknown))}",
        )

    # Save constraints to persistence
    await repo.save(
        WorkoutConstraints(
            user_id=user_id,
            equipment=body.equipment,
            goal=body.goal,
            available_minutes_by_weekday=body.available_minutes_by_weekday,
        )
    )

    # Return the saved constraints
    return WorkoutConstraintsOut(
        equipment=body.equipment,
        goal=body.goal,
        available_minutes_by_weekday=body.available_minutes_by_weekday,
    )


@router.get("", response_model=WorkoutConstraintsOut)
async def get(
    user_id: Annotated[str, Depends(get_current_user_id)],
    repo: Annotated[ConstraintsRepository, Depends(get_constraints_repository)],
) -> WorkoutConstraintsOut:
    """Fetch the authenticated user's workout constraints."""

    # Get stored constraints for this user
    constraints = await repo.get_by_user_id(user_id)
    if constraints is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No constraints set for this user"
        )

    # Return serialized constraints
    return WorkoutConstraintsOut(
        equipment=constraints.equipment,
        goal=constraints.goal,
        available_minutes_by_weekday=constraints.available_minutes_by_weekday,
    )
