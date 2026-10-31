import pytest

from conftest import reading, sql


@pytest.fixture
def running(client):
    client.post("/api/sessions", json={"started_at": "2026-10-31T23:00:00Z"})


def post(client, readings):
    return client.post("/api/readings", json=readings)


def test_mixed_batch_stores_valid_and_reports_rejected(client, running, db_path):
    r = post(client, [
        reading(),
        reading(sensor="pulse"),
        reading(value="60"),
        reading(value=True),
        reading(recorded_at="2026-10-31T23:00:30"),
        reading(value=300),
    ])
    assert r.status_code == 201
    assert r.json == {"accepted": 1, "rejected": [
        {"index": 1, "reason": "unknown sensor"},
        {"index": 2, "reason": "non-numeric value"},
        {"index": 3, "reason": "non-numeric value"},
        {"index": 4, "reason": "bad timestamp"},
        {"index": 5, "reason": "out of range"},
    ]}
    assert sql(db_path, "SELECT COUNT(*) FROM readings") == [(1,)]


def test_no_running_session_returns_409_and_stores_nothing(client, db_path):
    assert post(client, [reading()]).status_code == 409
    assert sql(db_path, "SELECT COUNT(*) FROM readings") == [(0,)]


@pytest.mark.parametrize("sensor, value, accepted", [
    ("heart_rate", 30, True), ("heart_rate", 29.9, False), ("heart_rate", 220, True), ("heart_rate", 220.1, False),
    ("temperature", -10, True), ("temperature", -10.1, False), ("temperature", 50, True), ("temperature", 50.1, False),
    ("humidity", 0, True), ("humidity", -0.1, False), ("humidity", 100, True), ("humidity", 100.1, False),
    ("motion", 0, True), ("motion", -1, False), ("motion", 1.5, False),
    ("sound", 0, True), ("sound", -0.1, False), ("sound", 140, True), ("sound", 140.1, False),
])
def test_range_boundaries(client, running, sensor, value, accepted):
    r = post(client, [reading(sensor=sensor, value=value)])
    assert r.json["accepted"] == int(accepted)
    assert r.json["rejected"] == ([] if accepted else [{"index": 0, "reason": "out of range"}])


def test_recorded_at_stored_as_utc(client, running, db_path):
    post(client, [reading(recorded_at="2026-11-01T05:00:30.5+05:30")])
    assert sql(db_path, "SELECT recorded_at FROM readings") == [("2026-10-31T23:30:30Z",)]


def test_simulated_required_and_stored_as_given(client, running, db_path):
    missing = reading()
    del missing["simulated"]
    r = post(client, [reading(simulated=False), reading(simulated=True), missing])
    assert r.json["accepted"] == 2
    assert [x["index"] for x in r.json["rejected"]] == [2]
    assert sql(db_path, "SELECT simulated FROM readings ORDER BY id") == [(0,), (1,)]


def test_non_list_body_returns_400(client, running):
    assert post(client, reading()).status_code == 400


def test_malformed_readings_rejected_without_failing_batch(client, running, db_path):
    r = post(client, [
        reading(),
        reading(sensor=["heart_rate"]),
        reading(sensor={"a": 1}),
        reading(sensor="motion", value=2**63),
        reading(value=10**400),
        reading(recorded_at="0001-01-01T00:00:00+01:00"),
        reading(sensor="motion", value=3),
    ])
    assert r.status_code == 201
    assert r.json == {"accepted": 2, "rejected": [
        {"index": 1, "reason": "unknown sensor"},
        {"index": 2, "reason": "unknown sensor"},
        {"index": 3, "reason": "out of range"},
        {"index": 4, "reason": "out of range"},
        {"index": 5, "reason": "bad timestamp"},
    ]}
    assert sql(db_path, "SELECT COUNT(*) FROM readings") == [(2,)]
