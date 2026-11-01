import io
import random
import sys
import urllib.error
from datetime import datetime, timezone

import pytest

import simulator
from backend import check_reading

START = datetime(2026, 10, 31, 23, tzinfo=timezone.utc)


def readings(scenario, seed=1, hours=8):
    return [r for step in simulator.night(scenario, START, hours, random.Random(seed)) for r in step]


@pytest.mark.parametrize("scenario", ["good", "restless", "hot-humid", "noisy"])
def test_values_in_range(scenario):
    lo_t, hi_t = simulator.SCENARIOS[scenario]["temp"]
    lo_h, hi_h = simulator.SCENARIOS[scenario]["hum"]
    for r in readings(scenario):
        assert check_reading(r) is None, r
        assert r["simulated"] is True
        if r["sensor"] == "temperature":
            assert lo_t <= r["value"] <= hi_t
        if r["sensor"] == "humidity":
            assert lo_h <= r["value"] <= hi_h


def test_same_seed_same_readings():
    assert readings("restless", seed=7) == readings("restless", seed=7)
    assert readings("restless", seed=7) != readings("restless", seed=8)


def test_one_reading_per_sensor_every_30s():
    steps = list(simulator.night("good", START, 8, random.Random(1)))
    assert len(steps) == 960
    assert all(sorted(r["sensor"] for r in s) == ["heart_rate", "humidity", "motion", "temperature"] for s in steps)
    assert steps[1][0]["recorded_at"] == "2026-10-31T23:00:30Z"


def fake_call(monkeypatch, stopped_path):
    calls = []

    def call(api, method, path, body=None):
        calls.append(path)
        return (409, {}) if path == stopped_path else (201, {})

    monkeypatch.setattr(simulator, "call", call)
    return calls


@pytest.mark.parametrize("stopped_path, expected", [
    ("/api/readings", ["/api/readings"]),
    ("/api/sessions/1/stop", ["/api/readings", "/api/sessions/1/stop"]),
])
def test_stopped_during_last_batch_or_stop_exits_cleanly(monkeypatch, capsys, stopped_path, expected):
    calls = fake_call(monkeypatch, stopped_path)
    with pytest.raises(SystemExit) as e:
        simulator.play("http://x", "good", 1, START, 0.25, 0, random.Random(1))
    assert e.value.code == 0
    assert "Sleep Session was stopped; exiting" in capsys.readouterr().out
    assert calls == expected


def run_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["simulator.py", "--api", "http://x", *args])
    simulator.main()


@pytest.mark.parametrize("args", [["--nights", "2"], ["--scenario", "good,restless"]])
def test_live_mode_rejects_nights_and_multiple_scenarios(monkeypatch, capsys, args):
    monkeypatch.setattr(simulator, "call", lambda *a, **k: pytest.fail("called the API"))
    with pytest.raises(SystemExit) as e:
        run_main(monkeypatch, *args)
    assert e.value.code == 2
    assert "--start" in capsys.readouterr().err


def test_api_down_prints_one_line_and_exits_1(monkeypatch):
    def down(*a, **k):
        raise urllib.error.URLError(ConnectionRefusedError("refused"))

    monkeypatch.setattr(simulator.urllib.request, "urlopen", down)
    with pytest.raises(SystemExit) as e:
        run_main(monkeypatch)
    assert e.value.code.startswith("Simulator: ")
    assert "\n" not in e.value.code


def test_non_json_response_exits_1(monkeypatch):
    def bad(*a, **k):
        raise urllib.error.HTTPError("http://x", 502, "Bad Gateway", {}, io.BytesIO(b"<html>"))

    monkeypatch.setattr(simulator.urllib.request, "urlopen", bad)
    with pytest.raises(SystemExit) as e:
        simulator.call("http://x", "GET", "/api/sessions/current")
    assert e.value.code.startswith("Simulator: ")


def test_non_2xx_on_readings_exits_1(monkeypatch):
    monkeypatch.setattr(simulator, "call", lambda *a, **k: (500, {"error": "boom"}))
    with pytest.raises(SystemExit) as e:
        simulator.play("http://x", "good", 1, START, 0.25, 0, random.Random(1))
    assert e.value.code.startswith("Simulator: POST /api/readings")


@pytest.mark.parametrize("status", [400, 409])
def test_failed_session_start_exits_1(monkeypatch, status):
    monkeypatch.setattr(
        simulator, "call", lambda api, method, path, body=None: (404 if path.endswith("current") else status, {"error": "x"})
    )
    with pytest.raises(SystemExit) as e:
        run_main(monkeypatch)
    assert e.value.code.startswith("Simulator: POST /api/sessions")


def test_only_noisy_has_sound():
    assert {r["sensor"] for r in readings("good")} == {"heart_rate", "humidity", "motion", "temperature"}
    sound = [r["value"] for r in readings("noisy") if r["sensor"] == "sound"]
    assert len(sound) == 960
    assert min(sound) < 40 and max(sound) > 55
    # loudness only: a Reading is one number, never an audio sample
    assert all(set(r) == {"sensor", "value", "recorded_at", "simulated"} for r in readings("noisy"))
