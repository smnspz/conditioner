from yoyo import step

steps = [
    step(
        "ALTER TABLE workout_constraints ADD COLUMN initial_perceived_fitness INTEGER",
        "ALTER TABLE workout_constraints DROP COLUMN initial_perceived_fitness",
    )
]
