import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

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


PART_NAMES = ("duration", "restlessness", "heart_rate", "environment")


def part(name, points, mx, detail):
    return {"name": name, "points": round(points, 1), "max": mx, "detail": detail}


def score(s, readings, gaps):
    t = lambda x: datetime.strptime(x, FMT)
    length = (t(s["ended_at"]) - t(s["started_at"])).total_seconds()
    gapped = {}
    for gap in gaps:
        gapped[gap["sensor"]] = gapped.get(gap["sensor"], 0) + (t(gap["end"]) - t(gap["start"])).total_seconds()
    by = {}
    for r in readings:
        by.setdefault(r["sensor"], []).append(r)
    # a Sensor is unusable when its Data Gaps cover more than half the Sleep Session
    ok = lambda sensor: length > 0 and bool(by.get(sensor)) and gapped.get(sensor, 0) <= length / 2
    parts = {}

    h, m = length / 3600, round(length / 60)
    # NSF 7–9 h (Hirshkowitz 2015), 6 and 10 h "may be appropriate"; PSQI bands. Time in bed, not measured sleep
    pts = 30 if 7 <= h <= 9 else 20 if 6 <= h < 7 or 9 < h <= 10 else 10 if h >= 5 else 0
    parts["duration"] = part("duration", pts, 30, f"{m // 60} h {m % 60} min in bed; NSF recommends 7–9 h for adults")

    if ok("motion"):
        v = [r["value"] for r in by["motion"]]
        # simplified neighbour rule in the spirit of Cole-Kripke/Sadeh, not their coefficients
        wake = sum(1 for i, x in enumerate(v) if x > 0 and any(y > 0 for y in v[max(i - 1, 0):i] + v[i + 1:i + 2]))
        eff = 1 - wake / len(v)
        pts = 30 if eff >= 0.85 else 20 if eff >= 0.75 else 10 if eff >= 0.65 else 0  # Ohayon 2017 ≥85%; PSQI bands
        parts["restlessness"] = part(
            "restlessness", pts, 30,
            f"Wake-like movement in {wake} of {len(v)} epochs (sleep efficiency estimate {eff * 100:.1f}%; ≥85% is good)",
        )

    if ok("heart_rate"):
        hr = [(t(r["recorded_at"]), r["value"]) for r in by["heart_rate"]]
        t0, hours = hr[0][0], {}
        for a, x in hr:
            hours.setdefault(int((a - t0).total_seconds() // 3600), []).append((a, x))
        # pre-sleep proxy for daytime HR: stricter than Ben-Dov 2007
        awake = mean(x for a, x in hr if (a - t0).total_seconds() < 1800)
        # a bucket under 30 min (partial last hour) is too noisy to be the lowest hour
        full = [b for b in hours.values() if (b[-1][0] - b[0][0]).total_seconds() >= 1800] or list(hours.values())
        dip = (awake - min(mean(x for a, x in b) for b in full)) / awake
        pts = 20 * min(max(dip / 0.10, 0), 1)  # Ben-Dov 2007 nondipping < 10%; linear scale is a design choice
        parts["heart_rate"] = part(
            "heart_rate", pts, 20,
            f"Heart rate {'fell' if dip >= 0 else 'rose'} {abs(dip) * 100:.1f}% from the first 30 min to the lowest hour (≥10% is a normal dip)",
        )

    # Okamoto-Mizuno 2012: 13–23 °C with bedding; 40–60% RH bed microclimate used as a room proxy
    share = lambda sensor, lo, hi: sum(lo <= r["value"] <= hi for r in by[sensor]) / len(by[sensor]) if ok(sensor) else None
    tf, hf = share("temperature", 13, 23), share("humidity", 40, 60)
    if tf is not None or hf is not None:
        used = [f for f in (tf, hf) if f is not None]
        pts = 10 * sum(used) if len(used) == 2 else 20 * used[0]
        pct = lambda f: f"{round(f * 100)}%" if f is not None else None
        detail = (
            f"Temperature 13–23 °C in {pct(tf)} of Readings; humidity 40–60% in {pct(hf)}" if len(used) == 2
            else f"Temperature 13–23 °C in {pct(tf)} of Readings; humidity missing" if hf is None
            else f"Humidity 40–60% in {pct(hf)} of Readings; temperature missing"
        )
        parts["environment"] = part("environment", pts, 20, detail)

    if not {"restlessness", "heart_rate", "environment"} & parts.keys():
        return None  # no Sensor data means no score, never one from duration alone
    got = [parts[n] for n in PART_NAMES if n in parts]
    return {
        "total": round(sum(p["points"] for p in got) / sum(p["max"] for p in got) * 100),
        "parts": got,
        "excluded": [n for n in PART_NAMES if n not in parts],
    }


def session_score(db, s):
    if s["ended_at"] is None:
        return None
    # shortcut: scored on read, a few queries per Sleep Session (N+1); store the score on stop if the list gets slow
    rows = db.execute(
        "SELECT sensor, value, recorded_at FROM readings WHERE session_id = ? AND recorded_at <= ? ORDER BY recorded_at",
        (s["id"], s["ended_at"]),
    ).fetchall()
    return score(s, rows, find_gaps(db, s))


def baseline(db, s):
    past = db.execute(
        "SELECT * FROM sessions WHERE ended_at IS NOT NULL AND auto_closed = 0 AND started_at < ? ORDER BY started_at DESC, id DESC",
        (s["started_at"],),
    )
    scores = []
    for p in past:
        if len(scores) == 7:
            break
        sc = session_score(db, p)
        if sc is not None:
            scores.append(sc)
    if len(scores) < 3:
        return None, f"Baseline still building: {len(scores)} of 3 past Sleep Sessions"
    pts = {}
    for sc in scores:
        for p in sc["parts"]:
            pts.setdefault(p["name"], []).append(p["points"])
    return {
        "total": round(mean(sc["total"] for sc in scores), 1),
        "parts": [{"name": n, "points": round(mean(pts[n]), 1)} for n in PART_NAMES if n in pts],
        "sessions_used": len(scores),
    }, None


def session_json(db, row):
    return {
        "id": row["id"],
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "auto_closed": bool(row["auto_closed"]),
        "score": session_score(db, row),
        # pages label a Sleep Session's score as simulated without downloading its Readings
        "simulated": bool(db.execute(
            "SELECT EXISTS(SELECT 1 FROM readings WHERE session_id = ? AND simulated)", (row["id"],)
        ).fetchone()[0]),
    }


def auto_close(db):
    # shortcut: lazy close on request, upgrade to a scheduler if hardware runs unattended
    db.execute(
        """UPDATE sessions SET auto_closed = 1,
             ended_at = MAX(sessions.started_at, COALESCE((SELECT MAX(recorded_at) FROM readings WHERE session_id = sessions.id), started_at))
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
        # overlapping a stopped Sleep Session (e.g. a live Simulator run that stopped at a future ended_at) is accepted; only one may be running
        if running(db):
            abort(409, "a Sleep Session is already running")
        b = body()
        started_at = parse_ts(b["started_at"]) if "started_at" in b else now()
        if started_at is None:
            abort(400, "started_at must be an ISO 8601 timestamp with a timezone")
        if started_at > (datetime.now(timezone.utc) + timedelta(minutes=5)).strftime(FMT):
            abort(400, "started_at is more than 5 minutes in the future")
        cur = db.execute("INSERT INTO sessions (started_at) VALUES (?)", (started_at,))
        return session_json(db, find_session(db, cur.lastrowid)), 201

    @app.post("/api/sessions/<int:id>/stop")
    def stop_session(id):
        db = get_db()
        s = find_session(db, id)
        if s["ended_at"] is not None:
            abort(409, "this Sleep Session has already ended")
        b = body()
        ended_at = parse_ts(b["ended_at"]) if "ended_at" in b else max(now(), s["started_at"])
        if ended_at is None:
            abort(400, "ended_at must be an ISO 8601 timestamp with a timezone")
        if ended_at < s["started_at"]:
            abort(400, "ended_at is before started_at")
        db.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (ended_at, id))
        return session_json(db, find_session(db, id))

    @app.post("/api/readings")
    def add_readings():
        batch = request.get_json(silent=True)
        if not isinstance(batch, list):
            abort(400, "body must be a list of Readings")
        db = get_db()
        s = running(db)
        if s is None:
            abort(409, "no Sleep Session is running")
        # auto-close horizon
        horizon = (datetime.strptime(s["started_at"], FMT) + timedelta(hours=14)).strftime(FMT)
        rows, rejected = [], []
        for i, r in enumerate(batch):
            reason = check_reading(r)
            # no cap at "now": the Simulator replays on its own clock
            if not reason and not s["started_at"] <= parse_ts(r["recorded_at"]) <= horizon:
                reason = "outside session"
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
        db = get_db()
        rows = db.execute("SELECT * FROM sessions ORDER BY started_at DESC, id DESC").fetchall()
        return [session_json(db, r) for r in rows]

    @app.get("/api/sessions/current")
    def current_session():
        db = get_db()
        s = running(db)
        if s is None:
            abort(404, "no Sleep Session is running")
        return session_json(db, s)

    @app.get("/api/sessions/<int:id>")
    def get_session(id):
        db = get_db()
        s = find_session(db, id)
        b, why = baseline(db, s)
        return {**session_json(db, s), "gaps": find_gaps(db, s), "baseline": b, "baseline_reason": why}

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
            {"sensor": r["sensor"], "value": int(r["value"]) if r["sensor"] == "motion" else r["value"], "recorded_at": r["recorded_at"], "simulated": bool(r["simulated"])}
            for r in rows
        ]

    return app
