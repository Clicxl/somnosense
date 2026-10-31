import random
from datetime import datetime, timezone

import pytest

import simulator
from backend import check_reading

START = datetime(2026, 10, 31, 23, tzinfo=timezone.utc)


def readings(scenario, seed=1, hours=8):
    return [r for step in simulator.night(scenario, START, hours, random.Random(seed)) for r in step]


@pytest.mark.parametrize("scenario", ["good", "restless", "hot-humid"])
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
