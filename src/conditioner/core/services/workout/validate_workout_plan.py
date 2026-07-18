from __future__ import annotations

from dataclasses import dataclass

from conditioner.core.domain.workout.exercise_catalog import ExerciseCatalogEntry
from conditioner.core.domain.workout.workout import BlockType, Workout


@dataclass(frozen=True)
class ValidationError:
    """A single constraint violation found during workout plan validation.

    Attributes:
        path: JSON-pointer-style location of the violation (e.g. '/sessions/0/blocks/1/exercises/2').
        code: Machine-readable error code.
        message: Human-readable description.
    """

    path: str
    code: str
    message: str


def validate_workout_plan(
    workout: Workout,
    catalog_index: dict[str, ExerciseCatalogEntry],
    session_duration_minutes: int,
    duration_tolerance_minutes: int = 10,
) -> list[ValidationError]:
    """Validate a generated workout plan against catalog and structural constraints.

    Returns an empty list if the plan is valid; returns one ValidationError per violation
    otherwise. Does not raise — callers check the list.

    Checks (in order per session/block/exercise):
    - EMPTY_SESSION: session has no blocks.
    - EMPTY_BLOCK: a block has no exercises.
    - INVALID_BLOCK_TYPE: block type is not a known BlockType value.
    - DURATION_OUT_OF_RANGE: sum of block estimated_minutes deviates > tolerance from budget.
    - UNKNOWN_EXERCISE: exercise_id not in catalog_index.
    - INVALID_SETS_REPS: sets < 1, or both reps and duration_seconds are None.
    """

    errors: list[ValidationError] = []

    for s_idx, session in enumerate(workout.sessions):
        s_path = f"/sessions/{s_idx}"

        if not session.blocks:
            errors.append(
                ValidationError(
                    path=s_path,
                    code="EMPTY_SESSION",
                    message=f"Session at {s_path} has no blocks.",
                )
            )
            continue

        # Check duration budget
        total_minutes = sum(b.estimated_minutes for b in session.blocks)
        if abs(total_minutes - session_duration_minutes) > duration_tolerance_minutes:
            errors.append(
                ValidationError(
                    path=s_path,
                    code="DURATION_OUT_OF_RANGE",
                    message=(
                        f"Session at {s_path} totals {total_minutes} min, expected "
                        f"{session_duration_minutes} ± {duration_tolerance_minutes} min."
                    ),
                )
            )

        for b_idx, block in enumerate(session.blocks):
            b_path = f"{s_path}/blocks/{b_idx}"

            # Validate block type is a known enum value
            try:
                BlockType(block.type.value)
            except ValueError:
                errors.append(
                    ValidationError(
                        path=b_path,
                        code="INVALID_BLOCK_TYPE",
                        message=f"Block at {b_path} has unknown type '{block.type}'.",
                    )
                )

            if not block.exercises:
                errors.append(
                    ValidationError(
                        path=b_path,
                        code="EMPTY_BLOCK",
                        message=f"Block at {b_path} has no exercises.",
                    )
                )
                continue

            for e_idx, exercise in enumerate(block.exercises):
                e_path = f"{b_path}/exercises/{e_idx}"

                if exercise.exercise_id not in catalog_index:
                    errors.append(
                        ValidationError(
                            path=e_path,
                            code="UNKNOWN_EXERCISE",
                            message=(
                                f"exercise_id '{exercise.exercise_id}' at {e_path} "
                                "is not in the catalog."
                            ),
                        )
                    )

                if exercise.sets < 1:
                    errors.append(
                        ValidationError(
                            path=e_path,
                            code="INVALID_SETS_REPS",
                            message=f"Exercise at {e_path} has sets < 1.",
                        )
                    )

                if exercise.reps is None and exercise.duration_seconds is None:
                    errors.append(
                        ValidationError(
                            path=e_path,
                            code="INVALID_SETS_REPS",
                            message=(
                                f"Exercise at {e_path} has neither reps nor duration_seconds set."
                            ),
                        )
                    )

    return errors
