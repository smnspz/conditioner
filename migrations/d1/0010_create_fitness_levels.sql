CREATE TABLE fitness_levels (
    user_id TEXT NOT NULL REFERENCES users(id),
    week_start TEXT NOT NULL,
    score INTEGER NOT NULL,
    PRIMARY KEY (user_id, week_start)
);
