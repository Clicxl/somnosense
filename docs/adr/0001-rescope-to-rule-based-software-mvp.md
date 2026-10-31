# Re-scope to a rule-based software MVP

The Phase 1 report proposed ML-based sleep staging, breathing-event detection (snoring, apnea, hypopnea) and multi-modal sensor fusion from accelerometer, microphone and PPG/SpO₂. For this semester we build only the software suite (React + Tailwind web app, Flask, SQLite) with a Simulator in place of the sensor hardware, a rule-based Sleep Score, and no ML. That is what a team can finish and demo to the Phase 3 panel without hardware or labelled training data. The ingest contract (devices send only Readings; the backend assigns them to the running Sleep Session) is kept simple so next semester's hardware can plug in unchanged.

## Consequences

- The sensors are heart rate, temperature, humidity and motion, with sound level as a stretch goal. Raw audio, sleep-stage classification and apnea detection move to future work.
- The Phase 3 objectives replace the report's three:
  1. Collect and display Readings from every Sensor per Sleep Session.
  2. Compute an explainable Sleep Score.
  3. Compare each session with the Sleeper's Baseline.
- The report's "low-confidence" idea survives as rule-based data checks: impossible values are rejected at ingest, gaps are flagged, and a score part without enough data is left out rather than guessed.
