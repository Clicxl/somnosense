# Somnosense

Somnosense is a web app that shows Readings from bedside and wearable Sensors for one Sleeper per Sleep Session, and turns them into an explainable, rule-based Sleep Score. See [GLOSSARY.md](GLOSSARY.md) for the terms and [ADR 0001](docs/adr/0001-rescope-to-rule-based-software-mvp.md) for the scope.

**All demo data is Simulated: every Reading comes from the Simulator, not real hardware.**

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (installs Python 3.12+ for you if needed)
- Node.js 22+ and npm

## Backend

```
uv sync
uv run flask --app backend run
```

The API serves on port 5000 and stores data in `backend/somnosense.db`; set `SOMNOSENSE_DB` to use another file. Run the tests with `uv run pytest`.

## Frontend

```
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173 (it proxies `/api` to the backend). Build with `npm run build`.

**Contract tests.** Install the backend dependencies first. `npm test` in `frontend/` starts Flask on port 5055 with a temporary database, runs the tests, then stops it; port 5055 must be free. It uses the `PYTHON` environment variable if set, else the repo's `.venv`, else `python`.

## Simulator

Arrives with SOM-12 (#12).
