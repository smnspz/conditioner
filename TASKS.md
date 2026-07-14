# Conditioner — Requirements & Tasks

## Requirements

### Functional
1. Google OAuth login → issue our own Bearer token; store Google credentials server-side (SQLite), never exposed to client.
2. Ingest wearable data (Google Health API first) behind a port/interface — HRV, RHR, sleep (duration/efficiency/regularity/WASO), training load, steps, and lifestyle markers where available.
3. Daily questionnaire endpoint capturing fatigue, soreness, stress, sleep quality (0–10) and a sick flag.
4. Compute daily Readiness Score (0–100) per the CLAUDE.md formula, map to one of 5 operational zones.
5. Generate a weekly workout plan with progressive load, then adjust remaining sessions during the week based on daily readiness.
6. Persist users, credentials, daily metrics/questionnaire answers, readiness scores, and generated workouts via a persistence port (SQLite adapter first).

### Non-functional
- Hexagonal architecture: `core`/`domain` must not import from `adapters`; both wearable ingestion and persistence stay behind `interfaces`.
- No magic strings — constants in `shared/constants.py`.
- GDPR: health data is special-category personal data — need lawful basis/consent capture, data export, data deletion ("right to erasure"), encryption at rest for tokens, retention policy.
- Tests (unit → e2e) required per finished feature; commit hooks run test suite.
- DB migrations via yoyo in `migrations/`.

## Task list

### 0. Project bootstrap
- [ ] Fill in `pyproject.toml` deps: fastapi, uvicorn, httpx, yoyo-migrations, pydantic, sqlite/aiosqlite, python-jose or similar for Bearer tokens, pytest.
- [ ] Scaffold `core/`, `adapters/`, `services/`, `interfaces/`, `domain/`, `shared/`, `api/` under `src/conditioner`.
- [ ] Set up `migrations/` with yoyo config.
- [ ] Reconcile `client_secret.json` vs CLAUDE.md's `client_secrets.json` naming.
- [ ] Write initial README (setup, run, test commands).

### 1. Domain models
- [ ] `domain`: User, GoogleCredentials, WearableDailyMetrics, QuestionnaireResponse, ReadinessScore, Workout/Session/Exercise.

### 2. Persistence port + SQLite adapter
- [ ] `interfaces`: `UserRepository`, `CredentialsRepository`, `MetricsRepository`, `WorkoutRepository`, etc.
- [ ] `adapters/persistence/sqlite`: implementations + migrations for each table.

### 3. Auth
- [ ] Google OAuth flow (authorization URL, callback, token exchange) using `client_secret.json`.
- [ ] Encrypt/store Google credentials in SQLite.
- [ ] Issue/verify our own Bearer tokens; auth dependency for FastAPI routes.

### 4. Wearable ingestion port + Google Health adapter
- [ ] `interfaces`: `WearableDataProvider` port (fetch HRV, RHR, sleep, steps, etc. for a date range).
- [ ] `adapters/wearables/google_health`: httpx client hitting Google Health API endpoints, mapped to domain models.

### 5. Questionnaire
- [ ] API endpoint + core use case to submit/store daily questionnaire responses.

### 6. Readiness score service
- [ ] `services`: normalization functions per metric (HRV, RHR, sleep composite, subjective wellbeing).
- [ ] `core`: aggregation use case implementing the weighted formula + load penalties (consecutive days, ACWR) + zone mapping.
- [ ] Baseline computation (rolling 7–14 day averages) as a supporting service.

### 7. Workout generation
- [ ] `core`: weekly plan generator with progressive load.
- [ ] `core`: daily adjustment use case that modifies remaining sessions based on readiness zone.

### 8. API layer
- [ ] FastAPI routers: `/auth/google/*`, `/questionnaire`, `/readiness`, `/workouts`.

### 9. GDPR compliance
- [ ] Consent capture at signup/OAuth.
- [ ] Data export endpoint.
- [ ] Data deletion endpoint (cascades across all tables holding user health data).
- [ ] Retention/expiry policy for raw wearable data.

### 10. Testing
- [ ] Unit tests per service/use case as built.
- [ ] Integration tests for adapters (SQLite, Google Health client mocked).
- [ ] E2E tests for full auth → ingest → readiness → workout flow.
