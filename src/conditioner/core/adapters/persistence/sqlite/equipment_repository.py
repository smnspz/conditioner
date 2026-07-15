from __future__ import annotations

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.workout.equipment import Equipment
from conditioner.core.interfaces.workout.equipment_repository import EquipmentRepository


class SqliteEquipmentRepository(EquipmentRepository):
    """SQLite-backed implementation of EquipmentRepository. Read-only: the catalog is seeded
    by migration, not written to at runtime."""

    def __init__(self, db_path: str) -> None:
        # Initializations
        self._db_path = db_path

    async def list_all(self) -> list[Equipment]:
        """Fetch every catalog entry, ordered by name."""

        async with connect(self._db_path) as conn:
            # Get all equipment rows
            cursor = await conn.execute("SELECT * FROM equipment ORDER BY name")
            rows = await cursor.fetchall()

            # Return mapped equipment domain objects
            return [self._to_domain(row) for row in rows]

    async def get_by_ids(self, ids: list[str]) -> list[Equipment]:
        """Fetch catalog entries matching the given ids."""

        if not ids:
            return []

        async with connect(self._db_path) as conn:
            # Get matching equipment rows
            placeholders = ",".join("?" for _ in ids)
            cursor = await conn.execute(
                f"SELECT * FROM equipment WHERE id IN ({placeholders})", ids
            )
            rows = await cursor.fetchall()

            # Return mapped equipment domain objects
            return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: aiosqlite.Row) -> Equipment:
        """Map a database row to an Equipment domain object."""

        # Return mapped equipment domain object
        return Equipment(id=row["id"], name=row["name"])
