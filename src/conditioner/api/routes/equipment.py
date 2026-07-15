from typing import Annotated

from fastapi import APIRouter, Depends

from conditioner.api.dependencies import get_equipment_repository
from conditioner.api.dto.equipment import EquipmentOut
from conditioner.core.interfaces.workout.equipment_repository import EquipmentRepository

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("", response_model=list[EquipmentOut])
async def list_all(
    repo: Annotated[EquipmentRepository, Depends(get_equipment_repository)],
) -> list[EquipmentOut]:
    """List the seeded equipment catalog."""

    # Get the full equipment catalog
    catalog = await repo.list_all()

    # Return serialized catalog entries
    return [EquipmentOut(id=item.id, name=item.name) for item in catalog]
