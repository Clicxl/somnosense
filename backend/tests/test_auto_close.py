from conftest import reading, sql

AGE = "UPDATE sessions SET opened_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now', ?)"


def test_session_over_14h_is_auto_closed_at_last_reading(client, db_path):
    client.post("/api/sessions", json={"started_at": "2025-10-31T23:00:00Z"})
    client.post("/api/readings", json=[reading(recorded_at="2025-11-01T02:00:00Z"), reading(recorded_at="2025-11-01T03:15:00Z")])
    sql(db_path, AGE, "-15 hours")
    s = client.get("/api/sessions/1").json
    assert s["ended_at"] == "2025-11-01T03:15:00Z"
    assert s["auto_closed"] is True


def test_auto_closed_without_readings_ends_at_started_at(client, db_path):
    client.post("/api/sessions", json={"started_at": "2025-10-31T23:00:00Z"})
    sql(db_path, AGE, "-15 hours")
    s = client.get("/api/sessions").json[0]
    assert s["ended_at"] == "2025-10-31T23:00:00Z"
    assert s["auto_closed"] is True


def test_session_opened_13h_ago_stays_running(client, db_path):
    client.post("/api/sessions")
    sql(db_path, AGE, "-13 hours")
    assert client.get("/api/sessions/current").status_code == 200


def test_backfilled_session_is_not_auto_closed(client):
    client.post("/api/sessions", json={"started_at": "2025-10-26T23:00:00Z"})
    client.post("/api/readings", json=[reading(recorded_at="2025-10-27T03:00:00Z")])
    r = client.get("/api/sessions/current")
    assert r.status_code == 200
    assert r.json["ended_at"] is None


def test_can_start_after_auto_close(client, db_path):
    client.post("/api/sessions")
    sql(db_path, AGE, "-15 hours")
    assert client.post("/api/sessions").status_code == 201


def test_readings_to_stale_session_return_409(client, db_path):
    client.post("/api/sessions", json={"started_at": "2025-10-31T23:00:00Z"})
    sql(db_path, AGE, "-15 hours")
    assert client.post("/api/readings", json=[reading()]).status_code == 409
