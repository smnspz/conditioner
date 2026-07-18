from __future__ import annotations

import json

from conditioner.core.adapters.persistence.d1.client import D1Client, JsonRow
from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry
from conditioner.core.domain.workout.workout import ExerciseModality
from conditioner.core.interfaces.workout.exercise_catalog_repository import (
    ExerciseCatalogRepository,
)


class D1ExerciseCatalogRepository(ExerciseCatalogRepository):
    """Cloudflare D1-backed implementation of ExerciseCatalogRepository.

    Read-only at runtime — the catalog is seeded by migration, never written to by the app.
    """

    def __init__(self, client: D1Client) -> None:
        # Initializations
        self._client = client

    async def list_all(self) -> list[ExerciseCatalogEntry]:
        """Fetch every catalog entry, ordered by id."""

        # Get all exercise catalog rows
        rows = await self._client.query("SELECT * FROM exercise_catalog ORDER BY id")
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

        # Get matching rows by id
        placeholders = ",".join("?" for _ in ids)
        rows = await self._client.query(
            f"SELECT * FROM exercise_catalog WHERE id IN ({placeholders})", ids
        )
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: JsonRow) -> ExerciseCatalogEntry:
        """Map a result row to an ExerciseCatalogEntry domain object."""

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
