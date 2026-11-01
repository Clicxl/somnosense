# Panel demo

About 12 to 13 minutes. All data is Simulated: every Reading comes from the Simulator, not real hardware.

## Before the panel (not timed)

```
uv sync
cd frontend
npm ci
cd ..
```

## 1. Start the app (~1 min)

Use a fresh database, so a Sleep Session left running from earlier cannot block step 2.

Terminal 1, in the repo root:

```
# bash
SOMNOSENSE_DB=demo.db uv run flask --app backend run
```

```
# PowerShell
$env:SOMNOSENSE_DB="demo.db"; uv run flask --app backend run
```

Terminal 2:

```
cd frontend
npm run dev
```

Open http://localhost:5173. The Live View says "No Sleep Session running".

## 2. Fill the History (under 30 s)

In a third terminal, backfill seven nights ending last night. It prints nothing.

```
# bash
uv run python simulator/simulator.py --start $(date -d '7 days ago' +%F) --nights 7 --scenario good,good,restless,good,hot-humid,good,good --seed 1
```

```
# PowerShell
uv run python simulator/simulator.py --start (Get-Date).AddDays(-7).ToString('yyyy-MM-dd') --nights 7 --scenario good,good,restless,good,hot-humid,good,good --seed 1
```

## 3. History (~2 min)

Open History.

- Seven Sleep Sessions, each with its Sleep Score.
- The dashed Baseline line starts at the 4th Sleep Session: it needs three earlier scored ones.
- The restless night and the hot and humid night dip below the good ones.
- The Simulated stamp: every Reading behind these scores is Simulated.

## 4. Live View (~4 min of playback, ~5 min with talk)

1. In the Live View press "Going to bed".
2. In the third terminal:

```
uv run python simulator/simulator.py --scenario restless --speed 120 --gap motion
```

At 120 times real time the 8 h night plays in 240 s. The Live View refreshes every 5 s: the elapsed time, the latest Reading of each Sensor, a remark for each.

About 2 min in, motion goes quiet for 30 simulated minutes (about 15 s real). Once it has been silent for 5 min of the night, the Live View flags it: the Motion remark turns red with "no Reading since ...". That is how the Live View shows a Data Gap while the night is still running.

Do not press "Woke up": it would end the Sleep Session at real time, and the Simulator would then exit. Let the Simulator stop the Sleep Session itself; the Live View then says "This Sleep Session ended outside this page." with a link, "Open its Morning Report". The Sleep Session ends about 8 h in the future, because the Simulator plays on its own clock.

## 5. Morning Report (~3 min)

Follow the link. Walk through:

- The Sleep Score gauge: the outer arc is the Sleep Score, the thin grey inner arc is the Baseline, and the difference against it is beside the gauge.
- Each part's remark, and its Baseline under the points: duration, restlessness, heart rate, environment.
- The total: the points of the four parts, rounded.
- The motion Data Gap: a pale red band in the Motion chart, about the middle of the night, and a red "Data Gap" line with its start and end times under it. (Only the wireframe hatches the band.) It is only 30 min, under half the Sleep Session, so restlessness is still scored.
- The Simulated stamp.

## Reset

Stop both servers, then delete `demo.db`.
