CREATE TABLE readiness_scores (
    user_id TEXT NOT NULL REFERENCES users(id),
    date TEXT NOT NULL,
    score INTEGER NOT NULL,
    zone TEXT NOT NULL,
    PRIMARY KEY (user_id, date)
);
