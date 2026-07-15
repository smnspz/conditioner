from yoyo import step

steps = [
    step(
        """
        CREATE TABLE workouts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            week_start TEXT NOT NULL
        )
        """,
        "DROP TABLE workouts",
    ),
    step(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            workout_id TEXT NOT NULL REFERENCES workouts(id),
            date TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0
        )
        """,
        "DROP TABLE sessions",
    ),
    step(
        """
        CREATE TABLE exercises (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES sessions(id),
            name TEXT NOT NULL,
            modality TEXT NOT NULL,
            sets INTEGER,
            reps INTEGER,
            duration_minutes REAL,
            target_load REAL
        )
        """,
        "DROP TABLE exercises",
    ),
]
