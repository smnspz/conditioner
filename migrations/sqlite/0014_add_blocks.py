from yoyo import step

_CREATE_BLOCKS = """
CREATE TABLE blocks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    estimated_minutes INTEGER NOT NULL DEFAULT 0,
    order_index INTEGER NOT NULL DEFAULT 0
)
"""

_CREATE_BLOCK_EXERCISES = """
CREATE TABLE block_exercises (
    id TEXT PRIMARY KEY,
    block_id TEXT NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    exercise_id TEXT NOT NULL,
    exercise_name TEXT NOT NULL,
    sets INTEGER NOT NULL DEFAULT 1,
    reps INTEGER,
    duration_seconds INTEGER,
    rest_seconds INTEGER NOT NULL DEFAULT 60,
    intensity_cue TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    order_index INTEGER NOT NULL DEFAULT 0
)
"""

steps = [
    step("DROP TABLE IF EXISTS exercises"),
    step(_CREATE_BLOCKS, "DROP TABLE blocks"),
    step(_CREATE_BLOCK_EXERCISES, "DROP TABLE block_exercises"),
]
