from conftest import reading


def night(client, started_at, ended_at=None):
    sid = client.post("/api/sessions", json={"started_at": started_at}).json["id"]
    if ended_at:
        client.post(f"/api/sessions/{sid}/stop", json={"ended_at": ended_at})
    return sid


def test_get_unknown_session_returns_404(client):
    r = client.get("/api/sessions/99")
    assert r.status_code == 404
    assert "error" in r.json


def test_readings_of_unknown_session_return_404(client):
    r = client.get("/api/sessions/99/readings")
    assert r.status_code == 404
    assert "error" in r.json


def test_list_sessions_newest_first_by_started_at(client):
    night(client, "2025-10-30T23:00:00Z", "2025-10-31T07:00:00Z")
    night(client, "2025-10-28T23:00:00Z", "2025-10-29T07:00:00Z")
    night(client, "2025-10-29T23:00:00Z", "2025-10-30T07:00:00Z")
    assert [s["started_at"][:10] for s in client.get("/api/sessions").json] == ["2025-10-30", "2025-10-29", "2025-10-28"]


def test_list_session_fields(client):
    night(client, "2025-10-30T23:00:00Z", "2025-10-31T07:00:00Z")
    assert client.get("/api/sessions").json == [{
        "id": 1, "started_at": "2025-10-30T23:00:00Z", "ended_at": "2025-10-31T07:00:00Z",
        "auto_closed": False, "score": None, "simulated": False,
    }]


def test_session_is_simulated_when_any_reading_is(client):
    night(client, "2025-10-31T23:00:00Z")
    client.post("/api/readings", json=[reading(simulated=False), reading(simulated=True)])
    assert client.get("/api/sessions").json[0]["simulated"] is True
    assert client.get("/api/sessions/1").json["simulated"] is True


def test_get_session_has_gaps_and_score(client):
    night(client, "2025-10-31T23:00:00Z")
    r = client.get("/api/sessions/1")
    assert r.status_code == 200
    assert r.json["id"] == 1
    assert r.json["started_at"] == "2025-10-31T23:00:00Z"
    assert r.json["gaps"] is None
    assert r.json["score"] is None


def test_readings_ordered_by_recorded_at(client):
    night(client, "2025-10-31T23:00:00Z")
    client.post("/api/readings", json=[
        reading(recorded_at="2025-10-31T23:01:00Z", value=61),
        reading(recorded_at="2025-10-31T23:00:30Z", value=60),
    ])
    assert client.get("/api/sessions/1/readings").json == [
        {"sensor": "heart_rate", "value": 60, "recorded_at": "2025-10-31T23:00:30Z", "simulated": True},
        {"sensor": "heart_rate", "value": 61, "recorded_at": "2025-10-31T23:01:00Z", "simulated": True},
    ]


def test_readings_filter_by_sensor(client):
    night(client, "2025-10-31T23:00:00Z")
    client.post("/api/readings", json=[reading(), reading(sensor="motion", value=2)])
    r = client.get("/api/sessions/1/readings?sensor=motion").json
    assert [x["sensor"] for x in r] == ["motion"]


def test_motion_readings_returned_as_int(client):
    night(client, "2025-10-31T23:00:00Z")
    client.post("/api/readings", json=[reading(sensor="motion", value=3)])
    r = client.get("/api/sessions/1/readings?sensor=motion").json
    assert r == [{"sensor": "motion", "value": 3, "recorded_at": "2025-10-31T23:00:30Z", "simulated": True}]
    assert type(r[0]["value"]) is int  # 3.0 == 3
