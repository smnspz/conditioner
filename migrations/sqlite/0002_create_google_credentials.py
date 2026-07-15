from yoyo import step

steps = [
    step(
        """
        CREATE TABLE google_credentials (
            user_id TEXT PRIMARY KEY REFERENCES users(id),
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            scopes TEXT NOT NULL
        )
        """,
        "DROP TABLE google_credentials",
    )
]
