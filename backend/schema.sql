CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  auto_closed INTEGER NOT NULL DEFAULT 0,
  opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP  -- server wall clock, never client-supplied
);
CREATE TABLE IF NOT EXISTS readings (
  id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL REFERENCES sessions(id),
  sensor TEXT NOT NULL,
  value REAL NOT NULL,
  recorded_at TEXT NOT NULL,
  simulated INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_readings_session_sensor_time ON readings (session_id, sensor, recorded_at);
