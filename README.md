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

## Database

Migrations are managed with [yoyo](https://ollycope.com/software/yoyo/latest/) against a local SQLite database at `data/conditioner.db`.

```bash
poetry run yoyo apply     # apply pending migrations
poetry run yoyo list      # show migration status
```

## Running the API

```bash
poetry run uvicorn conditioner.api.main:app --host 0.0.0.0 --port 9876 --reload
```

## Testing

```bash
poetry run pytest
```

## Linting & type checking

```bash
poetry run ruff check .
poetry run mypy src
```
