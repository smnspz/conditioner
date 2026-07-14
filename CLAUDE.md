# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Conditioner is an API for a fitness conditioning application. Its ultimate goal is to generate weekly workouts of increasing load/difficulty tailored to the user, then adjust those workouts throughout the week based on the user's daily readiness to perform.

Readiness is computed from two sources: objective data pulled from the user's wearable device, and subjective daily questionnaire answers.

## Architecture

The project follows hexagonal (ports and adapters) architecture, keeping business logic, interfaces, and adapters cleanly separated. Everything is separated as much as possible — don't collapse layers together for convenience.

- Wearable data ingestion is abstracted behind a port so any provider can be plugged in. Google Health API is the first adapter; Garmin, Apple Watch, etc. may follow later — do not hardcode assumptions about the data source into core logic.
- Persistence is likewise abstracted behind a port. The first adapter is SQLite3, but the architecture must not assume a specific database.

### Folder structure

Under the `conditioner` package (`src/conditioner`):

- `core` — business logic (use cases / application services orchestrating the domain), and everything it depends on:
  - `core/adapters` — concrete implementations of the ports (e.g. Google Health API client, SQLite persistence).
  - `core/services` — supporting services used by the core.
  - `core/interfaces` — the ports: abstract interfaces that adapters implement and core depends on.
  - `core/domain` — data models (entities/value objects).
- `shared` — cross-cutting code, including `shared/constants.py` for non-secret string constants.
- `api` — FastAPI routers/endpoints, the inbound HTTP interface.

At the repo root:

- `migrations` — database migrations, managed with **yoyo**.

## Tools and libraries

- **Poetry** manages the virtual environment and dependencies.
- **FastAPI** exposes the API endpoints.
- **httpx** calls the Google OAuth and Google Health APIs (and future wearable provider APIs).
- **yoyo** manages database migrations (`migrations/` at repo root).
- Git commit hooks run the test suite on every commit.

## Code quality conventions

- No magic strings. Any non-secret string constant belongs in `shared/constants.py`.
- After finishing a feature, review the code for dead code or logic that should be refactored into shared functions.

## Testing

Tests are treated as essential, not optional. When a feature is finished, write tests for it spanning unit through end-to-end coverage.

## Security and compliance

Features are designed with security in mind from the planning stage. Since the project operates in Europe, GDPR must be understood and accounted for when handling user health/wearable data — this is a hard constraint on feature design, not an afterthought.

## Authentication / authorization

- Users authenticate via Google OAuth.
- Google OAuth credentials are stored in the SQLite database; they are never exposed to the client.
- The API returns a Bearer token to the user, which is used to authenticate subsequent calls to our own endpoints.
- Our endpoints, in turn, use the stored Google credentials to call the Google Health API (or whichever wearable API is configured) on the user's behalf.
- A Google Cloud Console project is already set up, with `client_secret.json` present in the repo root for OAuth.

## Google Health API integration

When implementing wearable data ingestion, find and use the appropriate Google Health API endpoints needed to supply the inputs listed in the Readiness Score model below.

## Readiness Score model (0–100)

A daily training-readiness score aggregates objective tracker data and subjective questionnaire data into a single 0–100 value.

### Inputs

**Objective (tracker) data** — computed as daily values or trends relative to a personal baseline (e.g. rolling 7–14 day average):

- Physiology: nightly HRV (RMSSD or equivalent) and its deviation from baseline; morning resting heart rate (RHR) and its deviation from baseline.
- Sleep: total sleep duration; sleep efficiency (% of time in bed asleep); sleep/wake schedule regularity; number/duration of night-time awakenings (WASO).
- Training load: daily training load (e.g. TRIMP); acute load (last 7 days) vs. chronic load (last 3–4 weeks) for accumulated fatigue; consecutive training days without rest.
- Lifestyle (if available): total steps/NEAT; indirect markers like alcohol intake or late-evening eating, used only as penalties.

**Subjective (daily questionnaire)** — 0–10 scales:

- Perceived fatigue on waking (0 = fresh, 10 = exhausted).
- Muscle soreness/DOMS (0 = none, 10 = strong pain).
- Mental/emotional stress (0 = calm, 10 = very high stress).
- Perceived sleep quality (0 = terrible, 10 = excellent).
- A "sick" flag (illness, cold, joint pain) that applies a fixed penalty when active.

### Normalization

Each metric is normalized to a sub-score $s \in [0, 1]$, where 1 = ideal for hard training and 0 = rest day.

- **HRV**: $\Delta_{HRV} = (HRV_{today} - HRV_{baseline}) / HRV_{baseline}$, mapped to $s_{HRV}$ via thresholds (e.g. $\ge +0.05 \to 1.0$, $[-0.05, +0.05) \to 0.8$, $[-0.10, -0.05) \to 0.6$, $< -0.10 \to 0.3$).
- **RHR** (lower is better): $\Delta_{RHR} = (RHR_{today} - RHR_{baseline}) / RHR_{baseline}$, mapped similarly in the opposite direction (e.g. $\le -0.05 \to 1.0$ down to $> +0.10 \to 0.3$).
- **Sleep**: combine duration ($\min(1, hours\_slept / target)$, floored around 0.3 if < 5h), efficiency (>90% → 1.0, 85–90% → 0.8, 80–85% → 0.6, <80% → 0.3), and schedule regularity (penalty beyond 1–2h deviation from average bed/wake time) into $s_{sleep}$ via a weighted average (e.g. 0.5 duration, 0.3 efficiency, 0.2 regularity).
- **Subjective scores** (0–10 scales, 0 = best): $s_{fatigue} = 1 - fatigue/10$, $s_{soreness} = 1 - soreness/10$, $s_{stress} = 1 - stress/10$, $s_{sleep\_subjective} = sleep\_quality/10$.

### Aggregation formula

1. Aggregated subjective wellbeing:
   $$s_{wellbeing} = 0.4 \cdot s_{fatigue} + 0.3 \cdot s_{soreness} + 0.2 \cdot s_{stress} + 0.1 \cdot s_{sleep\_subjective}$$

2. Base readiness (weighted average of HRV, sleep, wellbeing, soreness, RHR):
   $$s_{readiness\_base} = 0.30 \cdot s_{HRV} + 0.25 \cdot s_{sleep} + 0.20 \cdot s_{wellbeing} + 0.15 \cdot s_{soreness} + 0.10 \cdot s_{RHR}$$

3. Load penalties:
   - Consecutive-days penalty (from day 4 onward, capped at 0.15):
     $$penalty_{days} = \min(0.15,\ \max(0, consecutive\_training\_days - 3) \times 0.02)$$
   - High acute:chronic load ratio (ACWR > 1.5) adds a further 0.05–0.1 penalty.

4. Final readiness fraction:
   $$s_{readiness} = \max(0,\ s_{readiness\_base} - penalty_{days} - penalty_{load})$$

5. Scaled to 0–100:
   $$Readiness = \text{round}(100 \cdot s_{readiness})$$

### Operational zones

| Range | Zone | Recommendation |
|---|---|---|
| 80–100 | Peak | OK for hard sessions / competition |
| 65–79 | Good | Normal training |
| 50–64 | Moderate | Reduce volume/intensity |
| 35–49 | Light | Light work / recovery only |
| 0–34 | Rest | Complete rest or mobility strongly advised |
