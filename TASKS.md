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
- [x] `core/adapters/ai/cloudflare`: second `WorkoutGenerationProvider` implementation, backed by Cloudflare Workers AI's REST API (structured JSON output via `response_format`). Prompt building and schema/domain mapping factored out to `core/adapters/ai/workout_prompt.py`, shared with the Gemini adapter. Not wired into `get_workout_generation_provider` — Gemini stays the active engine; swapping is a one-line change plus adding `cloudflare_account_id`/`cloudflare_api_token` settings if/when needed.
- [x] `shared/config.py` + `.env.example`: `gemini_api_key` setting; keep the key out of client responses and logs.
- [x] GDPR: readiness scores and constraints sent to Gemini are personal (health-adjacent) data leaving the EU-hosted system to a third party — confirm lawful basis/DPA coverage for this processor and document what's sent (constraints + readiness only, not raw wearable/questionnaire data) before wiring the adapter in. (Documented in README; actual DPA/lawful-basis sign-off is a legal/compliance task, not resolved in code.)

#### 7b. Generation logic

- [x] `core`: weekly plan generator, prompting the AI port with constraints + readiness; refuses to generate (`PrerequisitesMissingError`) if either is missing. (No progressive load yet — prior-week history isn't passed to the AI port.)
- [x] `core`: daily adjustment use case — scales sets/reps/duration/target_load of not-yet-completed sessions from a given day onward by that day's readiness zone (rule-based factor per zone; REST clears the sessions). Completed sessions and past sessions untouched.
- [x] `core`: regeneration use case — re-prompts the AI port with current constraints + readiness, keeping any session already marked completed in the prior plan instead of the freshly generated one for that date.

#### 7c. Equipment catalog

- [x] `core/domain`: `Equipment` (id, name) — a seeded gear catalog entry, not user-authored.
- [x] `core/interfaces`: `EquipmentRepository` port (`list_all`, `get_by_ids`) + `core/adapters/persistence/sqlite`: SQLite implementation.
- [x] Migration: `equipment` table + seed data (14 items: none/bodyweight, dumbbells, barbell, kettlebell, resistance_bands, pull_up_bar, bench, medicine_ball, jump_rope, foam_roller, yoga_mat, plyo_box, battle_ropes, suspension_trainer).
- [x] API endpoint: `GET /equipment` — read-only list of the catalog, no auth-scoped filtering (same for every user). (No separate service layer — the route calls `EquipmentRepository` directly, it added nothing.)
- [x] `core/domain`: `WorkoutConstraints.equipment` stays `list[str]`, now documented as catalog ids rather than free text (no storage/migration change needed — ids are still just strings).
- [x] `api/routes/constraints.py`: validates submitted equipment ids exist in the catalog (422 with the unknown ids if not).
- [x] Gemini prompt building unchanged — catalog ids (e.g. `dumbbells`, `resistance_bands`) are already human-readable, so no id→name lookup was needed in the prompt.

### 8. API layer
- [x] FastAPI routers: `/auth/google/*`, `/questionnaire`, `/readiness`.
- [x] `/workouts` router — `POST /workouts/{week_start}/generate`, `POST /workouts/{week_start}/regenerate`, `POST /workouts/{day}/adjust` (all 422 if prerequisites missing), `GET /workouts/{week_start}`.
- [x] Constraints endpoint(s) (set/get `WorkoutConstraints`) — see task 7a.
- [x] `GET /equipment` — gear catalog, see task 7c.

### 9. GDPR compliance
- [ ] Consent capture at signup/OAuth.
- [ ] Data export endpoint.
- [ ] Data deletion endpoint (cascades across all tables holding user health data).
- [ ] Retention/expiry policy for raw wearable data.

### 10. Testing
- [ ] Unit tests per service/use case as built.
- [ ] Integration tests for adapters (SQLite, Google Health client mocked).
- [ ] E2E tests for full auth → ingest → readiness → workout flow.
