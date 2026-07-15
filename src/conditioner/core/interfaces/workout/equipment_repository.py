from __future__ import annotations

from abc import ABC, abstractmethod

from conditioner.core.domain.workout.equipment import Equipment


class EquipmentRepository(ABC):
    """Port for reading the seeded equipment catalog."""

    @abstractmethod
    async def list_all(self) -> list[Equipment]:
        """Fetch every catalog entry, ordered by name."""

    @abstractmethod
    async def get_by_ids(self, ids: list[str]) -> list[Equipment]:
        """Fetch catalog entries matching the given ids, used to validate constraints."""
