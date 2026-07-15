from __future__ import annotations

from conditioner.core.adapters.persistence.d1.client import D1Client, JsonRow
from conditioner.core.domain.workout.equipment import Equipment
from conditioner.core.interfaces.workout.equipment_repository import EquipmentRepository


class D1EquipmentRepository(EquipmentRepository):
    """Cloudflare D1-backed implementation of EquipmentRepository. Read-only: the catalog is
    seeded by migration, not written to at runtime."""

    def __init__(self, client: D1Client) -> None:
        # Initializations
        self._client = client

    async def list_all(self) -> list[Equipment]:
        """Fetch every catalog entry, ordered by name."""

        # Get all equipment rows
        rows = await self._client.query("SELECT * FROM equipment ORDER BY name")
        return [self._to_domain(row) for row in rows]

    async def get_by_ids(self, ids: list[str]) -> list[Equipment]:
        """Fetch catalog entries matching the given ids."""

        if not ids:
            return []

        # Get matching equipment rows
        placeholders = ",".join("?" for _ in ids)
        rows = await self._client.query(
            f"SELECT * FROM equipment WHERE id IN ({placeholders})", ids
        )
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: JsonRow) -> Equipment:
        """Map a result row to an Equipment domain object."""

        # Return mapped equipment domain object
        return Equipment(id=row["id"], name=row["name"])
