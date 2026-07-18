from __future__ import annotations

import json

import aiosqlite

from conditioner.core.adapters.persistence.sqlite.connection import connect
from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry
from conditioner.core.domain.workout.workout import ExerciseModality
from conditioner.core.interfaces.workout.exercise_catalog_repository import (
    ExerciseCatalogRepository,
)


class SqliteExerciseCatalogRepository(ExerciseCatalogRepository):
    """SQLite-backed implementation of ExerciseCatalogRepository.

    Read-only at runtime — the catalog is seeded by migration, never written to by the app.
    """

    def __init__(self, db_path: str) -> None:
        # Initializations
        self._db_path = db_path

    async def list_all(self) -> list[ExerciseCatalogEntry]:
        """Fetch every catalog entry, ordered by id."""

        async with connect(self._db_path) as conn:
            # Get all exercise catalog rows
            cursor = await conn.execute("SELECT * FROM exercise_catalog ORDER BY id")
            rows = await cursor.fetchall()

            # Return mapped domain objects
            return [self._to_domain(row) for row in rows]

    async def filter_by_gear(self, available_gear: list[str]) -> list[ExerciseCatalogEntry]:
        """Return entries whose required_gear is a subset of available_gear plus bodyweight."""

        # Get all entries and filter in Python — catalog is small enough for this
        all_entries = await self.list_all()
        allowed = set(available_gear) | {"bodyweight"}

        # Return entries whose every required gear item is in the allowed set
        return [e for e in all_entries if set(e.required_gear) <= allowed]

    async def get_by_ids(self, ids: list[str]) -> list[ExerciseCatalogEntry]:
        """Fetch catalog entries matching the given ids."""

        if not ids:
            return []

        async with connect(self._db_path) as conn:
            # Get matching rows by id
            placeholders = ",".join("?" for _ in ids)
            cursor = await conn.execute(
                f"SELECT * FROM exercise_catalog WHERE id IN ({placeholders})", ids
            )
            rows = await cursor.fetchall()

            # Return mapped domain objects
            return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: aiosqlite.Row) -> ExerciseCatalogEntry:
        """Map a database row to an ExerciseCatalogEntry domain object."""

        # Return mapped exercise catalog domain object
        return ExerciseCatalogEntry(
            id=row["id"],
            name=row["name"],
            modality=ExerciseModality(row["modality"]),
            required_gear=json.loads(row["required_gear_json"]),
            optional_gear=json.loads(row["optional_gear_json"]),
            difficulty=row["difficulty"],
            primary_muscles=json.loads(row["primary_muscles_json"]),
            movement_pattern=row["movement_pattern"],
            tags=json.loads(row["tags_json"]),
        )
