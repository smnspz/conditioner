from __future__ import annotations

from pydantic import BaseModel

from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry


class ExerciseCatalogEntryOut(BaseModel):
    """Serialized exercise catalog entry returned to the client."""

    id: str
    name: str
    modality: str
    required_gear: list[str]
    optional_gear: list[str]
    difficulty: int
    primary_muscles: list[str]
    movement_pattern: str
    tags: list[str]

    @classmethod
    def from_domain(cls, entry: ExerciseCatalogEntry) -> ExerciseCatalogEntryOut:
        """Build from a domain ExerciseCatalogEntry."""

        return cls(
            id=entry.id,
            name=entry.name,
            modality=entry.modality.value,
            required_gear=entry.required_gear,
            optional_gear=entry.optional_gear,
            difficulty=entry.difficulty,
            primary_muscles=entry.primary_muscles,
            movement_pattern=entry.movement_pattern,
            tags=entry.tags,
        )
