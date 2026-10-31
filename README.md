# Somnosense

Somnosense is a web app that shows Readings from bedside and wearable Sensors for one Sleeper per Sleep Session, and turns them into an explainable, rule-based Sleep Score. See [GLOSSARY.md](GLOSSARY.md) for the terms and [ADR 0001](docs/adr/0001-rescope-to-rule-based-software-mvp.md) for the scope.

**All demo data is Simulated: every Reading comes from the Simulator, not real hardware.**

## Prerequisites

- Python 3
- Node.js and npm

## Backend

```
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r backend/requirements.txt
flask --app backend run
```

The API serves on port 5000 and stores data in `backend/somnosense.db`; set `SOMNOSENSE_DB` to use another file. Run the tests with `pytest`.

## Frontend

```
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173 (it proxies `/api` to the backend). Build with `npm run build`.

## Simulator

Arrives with SOM-12 (#12).
