import re

from conftest import sql

TS = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ"


def start(client, **body):
    return client.post("/api/sessions", json=body)


def test_start_returns_201_with_started_at_now(client):
    r = start(client)
    assert r.status_code == 201
    assert r.json["id"] == 1
    assert re.fullmatch(TS, r.json["started_at"])


def test_start_converts_started_at_to_utc(client):
    r = start(client, started_at="2026-10-31T23:00:00.123+05:30")
    assert r.json["started_at"] == "2026-10-31T17:30:00Z"


def test_start_with_naive_started_at_returns_400(client):
    assert start(client, started_at="2026-10-31T23:00:00").status_code == 400


def test_double_start_returns_409(client, db_path):
    start(client)
    assert start(client).status_code == 409
    assert sql(db_path, "SELECT COUNT(*) FROM sessions") == [(1,)]


def test_stop_sets_ended_at(client):
    start(client, started_at="2026-10-31T23:00:00Z")
    r = client.post("/api/sessions/1/stop", json={"ended_at": "2026-11-01T07:00:00Z"})
    assert r.status_code == 200
    assert r.json["id"] == 1
    assert r.json["started_at"] == "2026-10-31T23:00:00Z"
    assert r.json["ended_at"] == "2026-11-01T07:00:00Z"


def test_stop_defaults_ended_at_to_now(client):
    start(client)
    r = client.post("/api/sessions/1/stop")
    assert r.status_code == 200
    assert re.fullmatch(TS, r.json["ended_at"])


def test_stop_before_started_at_returns_400(client):
    start(client, started_at="2026-10-31T23:00:00Z")
    r = client.post("/api/sessions/1/stop", json={"ended_at": "2026-10-31T22:59:59Z"})
    assert r.status_code == 400


def test_double_stop_returns_409(client):
    start(client)
    client.post("/api/sessions/1/stop")
    assert client.post("/api/sessions/1/stop").status_code == 409


def test_stop_unknown_session_returns_404(client):
    r = client.post("/api/sessions/99/stop")
    assert r.status_code == 404
    assert "error" in r.json


def test_current_returns_running_session(client):
    start(client, started_at="2026-10-31T23:00:00Z")
    r = client.get("/api/sessions/current")
    assert r.status_code == 200
    assert r.json["id"] == 1
    assert r.json["ended_at"] is None


def test_current_404_when_none_running(client):
    r = client.get("/api/sessions/current")
    assert r.status_code == 404
    assert "error" in r.json
    start(client)
    client.post("/api/sessions/1/stop")
    assert client.get("/api/sessions/current").status_code == 404


def test_can_start_after_stop(client):
    start(client)
    client.post("/api/sessions/1/stop")
    assert start(client).status_code == 201
