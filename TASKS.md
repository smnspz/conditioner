# Conditioner — Requirements & Tasks

## Requirements

### Functional
1. Google OAuth login → issue our own Bearer token; store Google credentials server-side (SQLite), never exposed to client.
2. Ingest wearable data (Google Health API first) behind a port/interface — HRV, RHR, sleep (duration/efficiency/regularity/WASO), training load, steps, and lifestyle markers where available.
3. Daily questionnaire endpoint capturing fatigue, soreness, stress, sleep quality (0–10) and a sick flag.
4. Compute daily Readiness Score (0–100) per the CLAUDE.md formula, map to one of 5 operational zones.
5. Generate a weekly workout plan by prompting a generative AI (Gemini first, behind a port) with the user's constraints (equipment, goal, available time per day) and daily readiness; adjust/regenerate remaining sessions during the week when readiness or constraints change.
6. Persist users, credentials, daily metrics/questionnaire answers, readiness scores, workout constraints, and generated workouts via a persistence port (SQLite adapter first).

### Non-functional
- Hexagonal architecture: `core` (including `core/domain`) must not import from `core/adapters`; wearable ingestion, persistence, and generative AI all stay behind `core/interfaces`.
- No magic strings — constants in `shared/constants.py`.
- GDPR: health data is special-category personal data — need lawful basis/consent capture, data export, data deletion ("right to erasure"), encryption at rest for tokens, retention policy.
- Tests (unit → e2e) required per finished feature; commit hooks run test suite.
- DB migrations via yoyo in `migrations/`.

## Task list

### 0. Project bootstrap
- [x] Fill in `pyproject.toml` deps: fastapi, uvicorn, httpx, yoyo-migrations, pydantic, sqlite/aiosqlite, python-jose or similar for Bearer tokens, pytest.
- [x] Scaffold `core/` (with `adapters/`, `services/`, `interfaces/`, `domain/` nested inside), `shared/`, `api/` under `src/conditioner`.
- [x] Set up `migrations/` with yoyo config.
- [x] Reconcile `client_secret.json` vs CLAUDE.md's `client_secrets.json` naming.
- [x] Write initial README (setup, run, test commands).

### 1. Domain models
- [x] `core/domain`: User, GoogleCredentials, WearableDailyMetrics, QuestionnaireResponse, ReadinessScore, Workout/Session/Exercise.

### 2. Persistence port + SQLite adapter
- [x] `core/interfaces`: `UserRepository`, `CredentialsRepository`, `MetricsRepository`, `WorkoutRepository`, etc.
- [x] `core/adapters/persistence/sqlite`: implementations + migrations for each table.

### 3. Auth
- [x] Google OAuth flow (authorization URL, callback, token exchange) using `client_secret.json`.
- [x] Encrypt/store Google credentials in SQLite.
- [x] Issue/verify our own Bearer tokens; auth dependency for FastAPI routes.

### 4. Wearable ingestion port + Google Health adapter
- [x] `core/interfaces`: `WearableDataProvider` port (fetch HRV, RHR, sleep, steps, etc. for a date range).
- [x] `core/adapters/wearables/google_health`: httpx client hitting Google Health API endpoints, mapped to domain models.

### 5. Questionnaire
- [x] API endpoint + core use case to submit/store daily questionnaire responses.

### 6. Readiness score service
- [x] `core/services`: normalization functions per metric (HRV, RHR, sleep composite, subjective wellbeing).
- [x] `core`: aggregation use case implementing the weighted formula + load penalties (consecutive days, ACWR) + zone mapping.
- [x] Baseline computation (rolling 7–14 day averages) as a supporting service.

### 7. Workout generation

#### 7a. Prerequisites

- [x] `core/domain`: `WorkoutConstraints` (equipment, goal, available time per day) — model `goal` so more values can be added later, not just "MMA conditioning".
- [x] `core/interfaces`: `ConstraintsRepository` port + `core/adapters/persistence/sqlite`: SQLite implementation + migration (one row per user, updated in place).
- [x] API endpoint(s) to set/get a user's constraints; changing available time for a day must be able to trigger regeneration of that day's (or remaining) session(s) later. (Endpoints persist constraints; the regeneration trigger itself is wired in 7b once the regeneration use case exists.)
- [x] `core/interfaces`: generative AI port (e.g. `WorkoutGenerationProvider`) — takes constraints + readiness (+ prior plan context) and returns a proposed `Workout`; must not leak Gemini-specific types into `core`.
- [x] `core/adapters/ai/gemini` (or similar): Gemini adapter implementing the port, using the Interactions API (see the `gemini-interactions-api` skill) with structured output mapped to `Workout`/`Session`/`Exercise`.
- [x] `shared/config.py` + `.env.example`: `gemini_api_key` setting; keep the key out of client responses and logs.
- [x] GDPR: readiness scores and constraints sent to Gemini are personal (health-adjacent) data leaving the EU-hosted system to a third party — confirm lawful basis/DPA coverage for this processor and document what's sent (constraints + readiness only, not raw wearable/questionnaire data) before wiring the adapter in. (Documented in README; actual DPA/lawful-basis sign-off is a legal/compliance task, not resolved in code.)

#### 7b. Generation logic

- [x] `core`: weekly plan generator, prompting the AI port with constraints + readiness; refuses to generate (`PrerequisitesMissingError`) if either is missing. (No progressive load yet — prior-week history isn't passed to the AI port.)
- [ ] `core`: daily adjustment use case that modifies remaining sessions based on readiness zone.
- [ ] `core`: regeneration use case triggered when constraints (e.g. available time) change mid-week, leaving already-completed sessions untouched.

### 8. API layer
- [x] FastAPI routers: `/auth/google/*`, `/questionnaire`, `/readiness`.
- [x] `/workouts` router — `POST /workouts/{week_start}/generate` (422 if prerequisites missing), `GET /workouts/{week_start}`. Daily adjustment/regeneration endpoints still blocked on the rest of 7b.
- [x] Constraints endpoint(s) (set/get `WorkoutConstraints`) — see task 7a.

### 9. GDPR compliance
- [ ] Consent capture at signup/OAuth.
- [ ] Data export endpoint.
- [ ] Data deletion endpoint (cascades across all tables holding user health data).
- [ ] Retention/expiry policy for raw wearable data.

### 10. Testing
- [ ] Unit tests per service/use case as built.
- [ ] Integration tests for adapters (SQLite, Google Health client mocked).
- [ ] E2E tests for full auth → ingest → readiness → workout flow.
