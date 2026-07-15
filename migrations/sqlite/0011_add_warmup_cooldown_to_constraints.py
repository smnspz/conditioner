from yoyo import step

steps = [
    step(
        "ALTER TABLE workout_constraints ADD COLUMN include_warmup_cooldown INTEGER NOT NULL DEFAULT 0",
        "SELECT 1",
    ),
]
