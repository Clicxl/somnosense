from datetime import datetime, timedelta, timezone

from backend import FMT
from conftest import reading, sql


def past_session(client, day, hours=8, sensors=("motion",), temp=20):
    """A finished Sleep Session with a still Reading every 5 min (no Data Gaps) from each Sensor."""
    start = datetime(2025, 10, day, 23, tzinfo=timezone.utc)
    sid = client.post("/api/sessions", json={"started_at": start.strftime(FMT)}).json["id"]
    values = {"motion": 0, "temperature": temp}
    client.post("/api/readings", json=[
        reading(sensor=x, value=values[x], recorded_at=(start + timedelta(minutes=5 * i)).strftime(FMT))
        for i in range(hours * 12 + 1) for x in sensors
    ])
    client.post(f"/api/sessions/{sid}/stop", json={"ended_at": (start + timedelta(hours=hours)).strftime(FMT)})
    return sid


def test_baseline_null_with_reason_under_three(client):
    past_session(client, 1)
    past_session(client, 2)
    r = client.get(f"/api/sessions/{past_session(client, 3)}").json
    assert r["baseline"] is None
    assert r["baseline_reason"].startswith("Baseline still building")


def test_baseline_uses_last_seven_earlier_sessions(client):
    for day in (1, 2):
        past_session(client, day, hours=4)  # duration 0 points: total 50
    for day in range(3, 10):
        past_session(client, day)  # total 100
    target = past_session(client, 10)
    past_session(client, 11, hours=4)  # after the target, never used
    r = client.get(f"/api/sessions/{target}").json
    assert r["baseline"] == {"total": 100.0, "parts": [{"name": "duration", "points": 30.0}, {"name": "restlessness", "points": 30.0}], "sessions_used": 7}
    assert r["baseline_reason"] is None


def test_baseline_skips_auto_closed(client, db_path):
    for day in (1, 2, 3):
        past_session(client, day)
    sql(db_path, "UPDATE sessions SET auto_closed = 1 WHERE id = ?", past_session(client, 4, hours=4))
    b = client.get(f"/api/sessions/{past_session(client, 5)}").json["baseline"]
    assert b["total"] == 100.0
    assert b["sessions_used"] == 3


def test_baseline_skips_unscored_sessions(client):
    past_session(client, 1)
    past_session(client, 2)
    past_session(client, 3, sensors=())  # no Readings: score null
    r = client.get(f"/api/sessions/{past_session(client, 4)}").json
    assert r["baseline"] is None
    assert r["baseline_reason"].startswith("Baseline still building")


def test_baseline_part_mean_skips_excluded_parts(client):
    for day in (1, 2, 3):
        past_session(client, day)
    past_session(client, 4, sensors=("motion", "temperature"))  # the only session that scores environment
    b = client.get(f"/api/sessions/{past_session(client, 5)}").json["baseline"]
    assert b["parts"] == [
        {"name": "duration", "points": 30.0}, {"name": "restlessness", "points": 30.0}, {"name": "environment", "points": 20.0},
    ]
    assert b["sessions_used"] == 4
