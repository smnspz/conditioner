from yoyo import step

steps = [
    step(
        "ALTER TABLE exercises ADD COLUMN phase TEXT NOT NULL DEFAULT 'main'",
        "SELECT 1",
    ),
]
