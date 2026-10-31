from conftest import reading


def session(client, *times, sensor="heart_rate", ended_at="2025-10-31T23:10:00Z"):
    client.post("/api/sessions", json={"started_at": "2025-10-31T23:00:00Z"})
    client.post("/api/readings", json=[reading(sensor=sensor, recorded_at=t) for t in times])
    client.post("/api/sessions/1/stop", json={"ended_at": ended_at})
    return client.get("/api/sessions/1").json["gaps"]


def gaps_for(gaps, sensor):
    return [g for g in gaps if g["sensor"] == sensor]


def test_sensor_without_readings_is_one_gap_covering_session(client):
    gaps = session(client, "2025-10-31T23:00:00Z", "2025-10-31T23:05:00Z", "2025-10-31T23:10:00Z")
    assert gaps_for(gaps, "motion") == [{"sensor": "motion", "start": "2025-10-31T23:00:00Z", "end": "2025-10-31T23:10:00Z"}]


def test_four_minute_pause_is_not_a_gap(client):
    gaps = session(client, "2025-10-31T23:00:00Z", "2025-10-31T23:04:00Z", "2025-10-31T23:08:00Z", "2025-10-31T23:10:00Z")
    assert gaps_for(gaps, "heart_rate") == []


def test_six_minute_pause_is_a_gap(client):
    gaps = session(client, "2025-10-31T23:00:00Z", "2025-10-31T23:06:00Z", "2025-10-31T23:10:00Z")
    assert gaps_for(gaps, "heart_rate") == [{"sensor": "heart_rate", "start": "2025-10-31T23:00:00Z", "end": "2025-10-31T23:06:00Z"}]


def test_gaps_at_start_and_end(client):
    gaps = session(client, "2025-10-31T23:05:30Z", ended_at="2025-10-31T23:12:00Z")
    assert gaps_for(gaps, "heart_rate") == [
        {"sensor": "heart_rate", "start": "2025-10-31T23:00:00Z", "end": "2025-10-31T23:05:30Z"},
        {"sensor": "heart_rate", "start": "2025-10-31T23:05:30Z", "end": "2025-10-31T23:12:00Z"},
    ]


def test_gaps_null_while_running(client):
    client.post("/api/sessions", json={"started_at": "2025-10-31T23:00:00Z"})
    assert client.get("/api/sessions/1").json["gaps"] is None


def test_sensor_without_readings_is_gap_in_short_session(client):
    gaps = session(client, "2025-10-31T23:00:00Z", "2025-10-31T23:02:00Z", ended_at="2025-10-31T23:04:00Z")
    assert gaps_for(gaps, "motion") == [{"sensor": "motion", "start": "2025-10-31T23:00:00Z", "end": "2025-10-31T23:04:00Z"}]
    assert gaps_for(gaps, "heart_rate") == []
