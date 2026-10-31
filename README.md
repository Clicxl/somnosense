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

**Contract tests.** Run `uv sync` first. `npm test` in `frontend/` starts Flask on port 5055 with a temporary database, runs the tests, then stops it; port 5055 must be free. It uses the `PYTHON` environment variable if set, else the repo's `.venv`, else `python`.

## Simulator

The Simulator stands in for the sensor hardware: it plays a Scenario (`good`, `restless` or `hot-humid`) against the API as Simulated Readings. Every Reading it sends is labelled simulated.

**Live mode.** Start the backend, then:

```
uv run python simulator/simulator.py --scenario good --speed 60
```

It fills the running Sleep Session if you pressed "Going to bed", otherwise it starts one. `--speed` is how much faster than real time to play (default 1; 0 is as fast as possible). It stops the session when the night ends, and exits 0 if you stop it early. Live mode takes a single Scenario and no `--nights` (those need `--start`). Starting a session that overlaps a stopped Sleep Session is accepted, since a live run stops at a simulated end that may be in the future.

**Backfill mode.** To fill the history with past nights, give a start date and a number of nights:

```
uv run python simulator/simulator.py --start 2026-10-24 --nights 7 --scenario good,good,restless --seed 1
```

The Scenarios in the list repeat night by night. It refuses to run while a Sleep Session is running.

`--seed` makes a run repeatable and `--api` points at a backend other than `http://127.0.0.1:5000`.
