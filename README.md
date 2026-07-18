# Conditioner

API for a fitness conditioning application. Generates weekly workouts tailored to the user and adjusts them throughout the week based on daily readiness, computed from wearable data (Google Health API, with more providers planned) and a daily questionnaire.

See [CLAUDE.md](CLAUDE.md) for architecture details and the readiness score model, and [TASKS.md](TASKS.md) for the requirements/task breakdown.

## Setup

Requires Python 3.12+ and [Poetry](https://python-poetry.org/).

```bash
poetry install
```

Place your Google OAuth `client_secret.json` in the repo root (not committed — see `.gitignore`).

Copy `.env.example` to `.env` and fill in:
- `CONDITIONER_JWT_SECRET_KEY` — any random string, used to sign our own Bearer tokens and OAuth CSRF state.
- `CONDITIONER_TOKEN_ENCRYPTION_KEY` — a Fernet key used to encrypt stored Google tokens at rest, generate one with:
  ```bash
  poetry run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- `CONDITIONER_GEMINI_API_KEY` — API key for the Gemini API, used when the workout generation engine is `gemini`.
- `CONDITIONER_WORKOUT_GENERATION_ENGINE` — which `WorkoutGenerationProvider` adapter is active: `gemini` (default) or `cloudflare`. The `cloudflare` adapter uses `@cf/meta/llama-3.3-70b-instruct` on Cloudflare Workers AI.
- `CONDITIONER_PERSISTENCE_ENGINE` — which persistence adapter backs every repository port: `sqlite` (default) or `d1`.
- `CONDITIONER_CLOUDFLARE_ACCOUNT_ID` / `CONDITIONER_CLOUDFLARE_API_TOKEN` — required when the workout generation engine is `cloudflare` or the persistence engine is `d1`. The token needs Workers AI permission for the former, D1 edit permission for the latter; the account id is in the Cloudflare dashboard sidebar or via `wrangler whoami`.
- `CONDITIONER_CLOUDFLARE_D1_DATABASE_ID` — only required when the persistence engine is `d1`.

## Database

By default, migrations are managed with [yoyo](https://ollycope.com/software/yoyo/latest/) against a local SQLite database at `data/conditioner.db`.

```bash
poetry run yoyo apply     # apply pending migrations
poetry run yoyo list      # show migration status
```

### Cloudflare D1

When `CONDITIONER_PERSISTENCE_ENGINE=d1`, every repository talks to a D1 database over Cloudflare's REST API instead (`D1Client` in `core/adapters/persistence/d1`) — the app keeps running as a normal FastAPI/uvicorn process, it just points at D1 instead of a local SQLite file.

Schema is managed separately from yoyo, with [wrangler](https://developers.cloudflare.com/workers/wrangler/)'s own migration tooling against the same DDL, mirrored under `migrations/d1/`:

```bash
wrangler d1 create conditioner                          # once, then paste the id into wrangler.jsonc
wrangler d1 migrations apply conditioner --remote       # apply migrations/d1/*.sql
```

## Running the API

```bash
poetry run uvicorn conditioner.api.main:app --host 0.0.0.0 --port 9876 --reload
```

## API

Full interactive API docs (Swagger UI) are available at [localhost:9876/docs](http://localhost:9876/docs) while the server is running.

All endpoints except `/health`, `/`, `/auth/google/*`, `GET /equipment`, and `GET /exercise-catalog` require authentication: the access token issued at `/auth/google/callback` is delivered as an **HttpOnly cookie** (`access_token`), not an `Authorization` header — the browser sends it automatically on every subsequent request to the API.

### Auth

| Method | Path | Description |
|---|---|---|
| GET | `/auth/google/login` | Redirects to Google's OAuth consent screen. |
| GET | `/auth/google/callback` | OAuth callback (`code`, `state` query params). Creates/looks up the user, stores encrypted Google credentials, sets the `access_token` cookie. |

### Equipment

| Method | Path | Description |
|---|---|---|
| GET | `/equipment` | Lists the seeded equipment catalog (`id`, `name`). No auth — same for every user. |

### Exercise catalog

| Method | Path | Description |
|---|---|---|
| GET | `/exercise-catalog` | Lists all exercises the AI may include in generated plans (`id`, `name`, `modality`, `movement_pattern`, `difficulty`, `required_gear`, `optional_gear`, `primary_muscles`, `tags`). No auth. Pass `?gear=<id>&gear=<id>` to filter to exercises compatible with specific equipment. |

### Constraints

| Method | Path | Description |
|---|---|---|
| PUT | `/constraints` | Create/update the caller's `WorkoutConstraints` (`equipment` ids, `goal`, `available_minutes_by_weekday`). 422 if any equipment id isn't in the catalog. |
| GET | `/constraints` | Fetch the caller's constraints. 404 if none set. |

### Questionnaire

| Method | Path | Description |
|---|---|---|
| POST | `/questionnaire` | Submit/update the daily subjective questionnaire (`fatigue`, `soreness`, `stress`, `sleep_quality` 0–10, `is_sick`; `date` defaults to today). Returns 201. |
| GET | `/questionnaire/{day}` | Fetch the caller's questionnaire response for a date. 404 if none. |

### Readiness

| Method | Path | Description |
|---|---|---|
| GET | `/readiness/{day}` | Fetch the caller's readiness score/zone for a date, computing and caching it from wearable metrics + questionnaire if not already cached. 404 if there isn't enough data (missing metrics or questionnaire) for that date. |

### Workouts

| Method | Path | Description |
|---|---|---|
| POST | `/workouts/{week_start}/generate` | Generate and persist a weekly plan via the AI provider, using constraints + the readiness score dated exactly `week_start`. 422 if either is missing. Responds with `X-Workout-Source: fallback` header when the AI fails and a deterministic fallback plan is served instead. |
| POST | `/workouts/{week_start}/regenerate` | Regenerate the week (e.g. after constraints changed), keeping sessions already marked completed. Same 422 conditions as `generate`. |
| POST | `/workouts/{day}/adjust` | Scale not-yet-completed sessions from `day` onward by that day's readiness zone (local rule-based, no AI call). 422 if there's no readiness score or no workout for that week. |
| GET | `/workouts/{week_start}` | Fetch the caller's plan for the week starting `week_start`. 404 if none. |

### Misc

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check. |
| GET | `/` | Redirects to `/health`. |

## Testing

```bash
poetry run pytest
```

## Linting & type checking

```bash
poetry run ruff check .
poetry run mypy src
```

## Workout generation details

The AI generates a weekly plan structured as **sessions → blocks → exercises**. Each block has a type (`warmup`, `main`, `finisher`, `cooldown`) and a list of exercises drawn exclusively from the backend-controlled exercise catalog. Before calling the AI, the catalog is pre-filtered to the user's available equipment, so only compatible exercises are offered. The AI's JSON schema constrains `exercise_id` to a `Literal` over those catalog IDs, making hallucinated exercise names structurally impossible. After generation, a validation layer checks for unknown exercise IDs, empty blocks/sessions, invalid sets/reps, and duration out of budget; if validation fails, a single repair pass is attempted before falling back to a deterministic plan.

## Third-party AI processing (GDPR)

Weekly workout plans are generated by prompting an external AI provider (Gemini API or Cloudflare Workers AI, depending on `CONDITIONER_WORKOUT_GENERATION_ENGINE`), triggered via `POST /workouts/{week_start}/generate` and `POST /workouts/{week_start}/regenerate`. Only a user's workout constraints (equipment, goal, available time), their readiness score/zone, and a list of exercise IDs + metadata from the backend catalog are sent — raw wearable metrics and questionnaire answers never leave the system. `POST /workouts/{day}/adjust` (which scales session load by readiness zone) never calls an AI provider — it's a local rule-based adjustment. Generation/regeneration is refused (422) unless both constraints and a readiness score exist for the user. This still constitutes personal data leaving the EU-hosted system to a third-party processor; lawful basis and Data Processing Agreement coverage for each processor must be confirmed.
