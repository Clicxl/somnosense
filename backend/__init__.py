import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, abort, g, request
from werkzeug.exceptions import HTTPException

FMT = "%Y-%m-%dT%H:%M:%SZ"


def now():
    return datetime.now(timezone.utc).strftime(FMT)


def parse_ts(s):
    try:
        t = datetime.fromisoformat(s)
        if t.tzinfo is None:
            return None
        return t.astimezone(timezone.utc).strftime(FMT)
    except (TypeError, ValueError, OverflowError):
        return None


GAP_SENSORS = ("heart_rate", "temperature", "humidity", "motion")  # sound waits for #11
MAX_GAP = timedelta(minutes=5)

SENSORS = {
    "heart_rate": (30, 220),
    "temperature": (-10, 50),
    "humidity": (0, 100),
    "motion": (0, 2**63 - 1),  # SQLite INTEGER max; larger ints overflow on insert
    "sound": (0, 140),
}


def check_reading(r):
    """Reason the Reading is rejected, or None."""
    if not isinstance(r, dict) or not isinstance(r.get("sensor"), str) or r["sensor"] not in SENSORS:
        return "unknown sensor"
    v = r.get("value")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return "non-numeric value"
    if parse_ts(r.get("recorded_at")) is None:
        return "bad timestamp"
    lo, hi = SENSORS[r["sensor"]]
    if not lo <= v <= hi or (r["sensor"] == "motion" and not float(v).is_integer()):
        return "out of range"
    if not isinstance(r.get("simulated"), bool):
        return "missing simulated flag"


def session_json(row):
    return {
        "id": row["id"],
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "auto_closed": bool(row["auto_closed"]),
        "score": None,
    }


def auto_close(db):
    # shortcut: lazy close on request, upgrade to a scheduler if hardware runs unattended
    db.execute(
        """UPDATE sessions SET auto_closed = 1,
             ended_at = COALESCE((SELECT MAX(recorded_at) FROM readings WHERE session_id = sessions.id), started_at)
           WHERE ended_at IS NULL AND opened_at < strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-14 hours')"""
    )


def find_gaps(db, s):
    if s["ended_at"] is None:
        return None
    gaps = []
    for sensor in GAP_SENSORS:
        seen = db.execute(
            "SELECT recorded_at FROM readings WHERE session_id = ? AND sensor = ? ORDER BY recorded_at",
            (s["id"], sensor),
        )
        times = [r[0] for r in seen]
        if not times:  # #10: no Readings at all is one gap, even in a short session
            gaps.append({"sensor": sensor, "start": s["started_at"], "end": s["ended_at"]})
            continue
        times = [s["started_at"], *times, s["ended_at"]]
        for a, b in zip(times, times[1:]):
            if datetime.strptime(b, FMT) - datetime.strptime(a, FMT) > MAX_GAP:
                gaps.append({"sensor": sensor, "start": a, "end": b})
    return gaps


def running(db):
    return db.execute("SELECT * FROM sessions WHERE ended_at IS NULL").fetchone()


def find_session(db, id):
    row = db.execute("SELECT * FROM sessions WHERE id = ?", (id,)).fetchone()
    if row is None:
        abort(404, "no such Sleep Session")
    return row


def body():
    b = request.get_json(silent=True)
    return b if isinstance(b, dict) else {}


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = str(
        db_path or os.environ.get("SOMNOSENSE_DB") or Path(__file__).parent / "somnosense.db"
    )

    db = sqlite3.connect(app.config["DATABASE"])
    try:
        db.executescript((Path(__file__).parent / "schema.sql").read_text())
    finally:
        db.close()  # sqlite3's `with` doesn't close; Windows keeps the file locked

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            auto_close(g.db)
        return g.db

    @app.teardown_appcontext
    def close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            if exc is None:
                db.commit()
            db.close()

    @app.errorhandler(HTTPException)
    def http_error(e):
        return {"error": e.description}, e.code

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/sessions")
    def start_session():
        db = get_db()
        if running(db):
            abort(409, "a Sleep Session is already running")
        b = body()
        started_at = parse_ts(b["started_at"]) if "started_at" in b else now()
        if started_at is None:
            abort(400, "started_at must be an ISO 8601 timestamp with a timezone")
        cur = db.execute("INSERT INTO sessions (started_at) VALUES (?)", (started_at,))
        return session_json(find_session(db, cur.lastrowid)), 201

    @app.post("/api/sessions/<int:id>/stop")
    def stop_session(id):
        db = get_db()
        s = find_session(db, id)
        if s["ended_at"] is not None:
            abort(409, "this Sleep Session has already ended")
        b = body()
        ended_at = parse_ts(b["ended_at"]) if "ended_at" in b else now()
        if ended_at is None:
            abort(400, "ended_at must be an ISO 8601 timestamp with a timezone")
        if ended_at < s["started_at"]:
            abort(400, "ended_at is before started_at")
        db.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (ended_at, id))
        return session_json(find_session(db, id))

    @app.post("/api/readings")
    def add_readings():
        batch = request.get_json(silent=True)
        if not isinstance(batch, list):
            abort(400, "body must be a list of Readings")
        db = get_db()
        s = running(db)
        if s is None:
            abort(409, "no Sleep Session is running")
        rows, rejected = [], []
        for i, r in enumerate(batch):
            reason = check_reading(r)
            if reason:
                rejected.append({"index": i, "reason": reason})
            else:
                rows.append((s["id"], r["sensor"], r["value"], parse_ts(r["recorded_at"]), r["simulated"]))
        db.executemany(
            "INSERT INTO readings (session_id, sensor, value, recorded_at, simulated) VALUES (?, ?, ?, ?, ?)", rows
        )
        return {"accepted": len(rows), "rejected": rejected}, 201

    @app.get("/api/sessions")
    def list_sessions():
        rows = get_db().execute("SELECT * FROM sessions ORDER BY started_at DESC, id DESC")
        return [session_json(r) for r in rows]

    @app.get("/api/sessions/current")
    def current_session():
        s = running(get_db())
        if s is None:
            abort(404, "no Sleep Session is running")
        return session_json(s)

    @app.get("/api/sessions/<int:id>")
    def get_session(id):
        db = get_db()
        s = find_session(db, id)
        return {**session_json(s), "gaps": find_gaps(db, s)}

    @app.get("/api/sessions/<int:id>/readings")
    def session_readings(id):
        db = get_db()
        find_session(db, id)
        query, args = "SELECT * FROM readings WHERE session_id = ?", [id]
        if "sensor" in request.args:
            query += " AND sensor = ?"
            args.append(request.args["sensor"])
        rows = db.execute(query + " ORDER BY recorded_at", args)
        return [
            {"sensor": r["sensor"], "value": r["value"], "recorded_at": r["recorded_at"], "simulated": bool(r["simulated"])}
            for r in rows
        ]

    return app
