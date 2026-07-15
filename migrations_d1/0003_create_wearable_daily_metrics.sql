CREATE TABLE wearable_daily_metrics (
    user_id TEXT NOT NULL REFERENCES users(id),
    date TEXT NOT NULL,
    hrv_rmssd REAL,
    resting_heart_rate REAL,
    sleep_duration_hours REAL,
    sleep_efficiency_pct REAL,
    sleep_onset TEXT,
    wake_time TEXT,
    waso_minutes REAL,
    training_load REAL,
    steps INTEGER,
    alcohol_flag INTEGER NOT NULL DEFAULT 0,
    late_eating_flag INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, date)
);
