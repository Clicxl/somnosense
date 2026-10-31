import random
from datetime import datetime, timezone

from backend import score
from simulator import night

START = datetime(2025, 10, 31, 23, tzinfo=timezone.utc)
SESSION = {"started_at": "2025-10-31T23:00:00Z", "ended_at": "2025-11-01T07:00:00Z"}


def readings(scenario, drop=()):
    return [r for step in night(scenario, START, 8, random.Random(1)) for r in step if r["sensor"] not in drop]


def whole(*sensors):
    return [{"sensor": x, "start": SESSION["started_at"], "end": SESSION["ended_at"]} for x in sensors]


def parts(result):
    return {p["name"]: p for p in result["parts"]}


def test_scenario_scores_land_in_expected_ranges():
    good, restless, hot = (score(SESSION, readings(sc), [])["total"] for sc in ("good", "restless", "hot-humid"))
    assert good >= 90
    assert 60 <= restless <= 85
    assert 60 <= hot <= 85
    assert good - restless >= 15
    assert good - hot >= 15


def test_drop_is_explained_by_the_right_part():
    restless = parts(score(SESSION, readings("restless"), []))
    assert restless["restlessness"]["points"] < 30
    assert restless["heart_rate"]["points"] < 10
    assert parts(score(SESSION, readings("hot-humid"), []))["environment"]["points"] == 0
    good = score(SESSION, readings("good"), [])
    assert all(p["points"] == p["max"] for p in good["parts"])
    assert all(p["detail"] for p in good["parts"])
    assert good["excluded"] == []


def test_part_excluded_and_total_rescaled_when_sensor_missing():
    s = score(SESSION, readings("restless", drop=("heart_rate",)), whole("heart_rate"))
    assert s["excluded"] == ["heart_rate"]
    assert sum(p["max"] for p in s["parts"]) == 80
    assert s["total"] == round(sum(p["points"] for p in s["parts"]) / 80 * 100)


def test_part_kept_when_gaps_cover_half():
    gap = [{"sensor": "heart_rate", "start": "2025-10-31T23:00:00Z", "end": "2025-11-01T03:00:00Z"}]
    s = score(SESSION, readings("good"), gap)
    assert "heart_rate" in parts(s)
    assert s["excluded"] == []


def test_environment_scored_from_humidity_alone():
    s = score(SESSION, readings("good", drop=("temperature",)), whole("temperature"))
    env = parts(s)["environment"]
    assert (env["points"], env["max"]) == (20, 20)
    assert s["excluded"] == []
    s = score(SESSION, readings("good", drop=("temperature", "humidity")), whole("temperature", "humidity"))
    assert "environment" in s["excluded"]


def test_no_usable_sensor_gives_null_score():
    assert score(SESSION, [], whole("heart_rate", "temperature", "humidity", "motion")) is None


def test_running_session_score_null_in_list_and_detail(client):
    client.post("/api/sessions", json={"started_at": "2025-10-31T23:00:00Z"})
    client.post("/api/readings", json=readings("good")[:4])
    assert client.get("/api/sessions").json[0]["score"] is None
    assert client.get("/api/sessions/1").json["score"] is None


def test_finished_session_scored_in_list_and_detail(client):
    client.post("/api/sessions", json={"started_at": SESSION["started_at"]})
    client.post("/api/readings", json=readings("good"))
    client.post("/api/sessions/1/stop", json={"ended_at": SESSION["ended_at"]})
    listed = client.get("/api/sessions").json[0]["score"]
    assert listed == client.get("/api/sessions/1").json["score"]
    assert listed["total"] >= 90
