import sys
from datetime import date, timedelta

import simulator


def run(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["simulator.py", *args])
    simulator.main()


def test_backfilled_nights_then_live_night_has_score_gaps_and_baseline(client, monkeypatch):
    # the Simulator's HTTP goes through the Flask test client: no server, no port
    def call(api, method, path, body=None):
        r = client.open(path, method=method, json=body)
        return r.status_code, r.get_json()

    monkeypatch.setattr(simulator, "call", call)
    # today-5..today-2: the last backfilled night starts before now at any time of day
    start = (date.today() - timedelta(days=5)).isoformat()
    run(monkeypatch, "--start", start, "--nights", "4", "--scenario", "good,good,restless,good", "--seed", "1")
    run(monkeypatch, "--scenario", "restless", "--speed", "0", "--seed", "2", "--gap", "motion")

    sessions = client.get("/api/sessions").get_json()
    assert len(sessions) == 5 and all(s["ended_at"] and s["simulated"] for s in sessions)
    live = client.get(f"/api/sessions/{sessions[0]['id']}").get_json()
    assert live["score"] is not None
    assert [g["sensor"] for g in live["gaps"]] == ["motion"]
    assert "restlessness" not in live["score"]["excluded"]  # a 30 min gap leaves the part scored
    assert live["baseline"] is not None and live["baseline"]["sessions_used"] == 4
