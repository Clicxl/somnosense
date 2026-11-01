"""Plays a Scenario against the API as Simulated Readings, one Sleep Session per night."""
import argparse
import json
import math
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, time as dtime, timedelta, timezone

FMT = "%Y-%m-%dT%H:%M:%SZ"
STEP = timedelta(seconds=30)

SCENARIOS = {
    "good": {"hr": 62, "dip": 8, "temp": (19, 21), "hum": (45, 55), "move": 0.05},
    "restless": {"hr": 75, "dip": 2, "temp": (19, 21), "hum": (45, 55), "move": 0.35},
    "hot-humid": {"hr": 66, "dip": 5, "temp": (27, 30), "hum": (70, 80), "move": 0.1},
    # sound: quiet room level (dB) and the chance per 30 s of a louder event; loudness only, never audio (#11)
    "noisy": {"hr": 68, "dip": 4, "temp": (19, 21), "hum": (45, 55), "move": 0.15, "sound": (32, 0.15)},
}


def night(scenario, start, hours, rng):
    sc = SCENARIOS[scenario]
    steps = round(hours * 120)
    for i in range(steps):
        at = (start + i * STEP).astimezone(timezone.utc).strftime(FMT)
        # HR dips towards mid-night and recovers by morning
        hr = round(sc["hr"] - sc["dip"] * math.sin(math.pi * i / steps) + rng.gauss(0, 2))
        temp = round(rng.uniform(*sc["temp"]), 1)
        hum = round(rng.uniform(*sc["hum"]), 1)
        move = rng.randint(1, 8) if rng.random() < sc["move"] else 0
        values = {
            "heart_rate": hr,
            "temperature": min(max(temp, sc["temp"][0]), sc["temp"][1]),
            "humidity": min(max(hum, sc["hum"][0]), sc["hum"][1]),
            "motion": move,
        }
        if "sound" in sc:
            quiet, loud = sc["sound"]
            values["sound"] = round(rng.uniform(55, 75) if rng.random() < loud else quiet + rng.gauss(0, 2), 1)
        yield [{"sensor": k, "value": v, "recorded_at": at, "simulated": True} for k, v in values.items()]


def call(api, method, path, body=None):
    req = urllib.request.Request(
        api + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)
    except ValueError:
        sys.exit(f"Simulator: {method} {path} did not return JSON")
    except OSError as e:
        sys.exit(f"Simulator: cannot reach the API at {api} ({getattr(e, 'reason', e)})")


def post(api, path, body):
    status, data = call(api, "POST", path, body)
    if status == 409 and path != "/api/sessions":
        print("Sleep Session was stopped; exiting")
        sys.exit(0)
    if status >= 300:
        sys.exit(f"Simulator: POST {path} failed ({status}: {data})")
    return data


def play(api, scenario, session_id, start, hours, speed, rng):
    batch = []
    t0 = time.monotonic()
    for i, step in enumerate(night(scenario, start, hours, rng), 1):
        batch += step
        if speed > 0 or i % 120 == 0:
            post(api, "/api/readings", batch)
            batch = []
            if speed > 0:
                time.sleep(max(0, t0 + i * 30 / speed - time.monotonic()))
    if batch:
        post(api, "/api/readings", batch)
    end = (start + round(hours * 120) * STEP).astimezone(timezone.utc).strftime(FMT)
    post(api, f"/api/sessions/{session_id}/stop", {"ended_at": end})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario", default="good", help=f"comma list of {', '.join(SCENARIOS)}")
    p.add_argument("--speed", type=float, default=1, help="1 = real time, 0 = as fast as possible")
    p.add_argument("--hours", type=float, default=8)
    # not localhost: on Windows it tries IPv6 first and costs ~2 s per request
    p.add_argument("--api", default="http://127.0.0.1:5000")
    p.add_argument("--seed", type=int)
    p.add_argument("--start", type=date.fromisoformat, help="backfill from this date (YYYY-MM-DD)")
    p.add_argument("--nights", type=int, default=1)
    a = p.parse_args()

    scenarios = a.scenario.split(",")
    unknown = [s for s in scenarios if s not in SCENARIOS]
    if unknown:
        p.error(f"unknown scenario: {', '.join(unknown)}")
    if a.start is None and (a.nights != 1 or len(scenarios) > 1):
        p.error("--nights and more than one --scenario need --start")
    rng = random.Random(a.seed)

    status, current = call(a.api, "GET", "/api/sessions/current")
    if a.start is None:
        if status != 200:
            current = post(a.api, "/api/sessions", {})
        start = datetime.strptime(current["started_at"], FMT).replace(tzinfo=timezone.utc)
        play(a.api, scenarios[0], current["id"], start, a.hours, a.speed, rng)
        return

    if status == 200:
        sys.exit("A Sleep Session is running; stop it before backfilling.")
    for k in range(a.nights):
        d = a.start + timedelta(days=k)
        start = datetime.combine(d, dtime(23)).astimezone() + timedelta(minutes=rng.randint(-30, 30))
        s = post(a.api, "/api/sessions", {"started_at": start.astimezone(timezone.utc).strftime(FMT)})
        play(a.api, scenarios[k % len(scenarios)], s["id"], start, a.hours, 0, rng)


if __name__ == "__main__":
    main()
