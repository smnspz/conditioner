from __future__ import annotations

from pydantic import BaseModel

from conditioner.core.domain.workout.equipment import Equipment


class EquipmentOut(BaseModel):
    """Serialized equipment catalog entry returned to the client."""

    id: str
    name: str

    @classmethod
    def from_domain(cls, equipment: Equipment) -> EquipmentOut:
        """Build from a domain Equipment."""

        return cls(id=equipment.id, name=equipment.name)
