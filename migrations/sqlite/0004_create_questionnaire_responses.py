from yoyo import step

steps = [
    step(
        """
        CREATE TABLE questionnaire_responses (
            user_id TEXT NOT NULL REFERENCES users(id),
            date TEXT NOT NULL,
            fatigue INTEGER NOT NULL,
            soreness INTEGER NOT NULL,
            stress INTEGER NOT NULL,
            sleep_quality INTEGER NOT NULL,
            is_sick INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, date)
        )
        """,
        "DROP TABLE questionnaire_responses",
    )
]
