CREATE TABLE workout_constraints (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    equipment TEXT NOT NULL,
    goal TEXT NOT NULL,
    available_minutes_by_weekday TEXT NOT NULL
);
