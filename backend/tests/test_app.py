import sqlite3

import pytest

from backend import create_app


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def app(db_path):
    return create_app(db_path)


def columns(db_path, table):
    with sqlite3.connect(db_path) as db:
        return [row[1] for row in db.execute(f"PRAGMA table_info({table})")]


def test_health_returns_200(app):
    assert app.test_client().get("/api/health").status_code == 200


def test_creates_db_file_on_start(db_path):
    assert not db_path.exists()
    create_app(db_path)
    assert db_path.exists()


def test_env_var_sets_db_path(tmp_path, monkeypatch):
    path = tmp_path / "from_env.db"
    monkeypatch.setenv("SOMNOSENSE_DB", str(path))
    create_app()
    assert path.exists()


def test_sessions_columns(app, db_path):
    assert columns(db_path, "sessions") == ["id", "started_at", "ended_at", "auto_closed", "opened_at"]


def test_readings_columns(app, db_path):
    assert columns(db_path, "readings") == ["id", "session_id", "sensor", "value", "recorded_at", "simulated"]


def test_readings_index(app, db_path):
    with sqlite3.connect(db_path) as db:
        cols = [row[2] for row in db.execute("PRAGMA index_info(idx_readings_session_sensor_time)")]
    assert cols == ["session_id", "sensor", "recorded_at"]


def test_opened_at_set_by_server(app, db_path):
    with sqlite3.connect(db_path) as db:
        db.execute("INSERT INTO sessions (started_at) VALUES ('2026-10-31T23:00:00Z')")
        (opened_at,) = db.execute("SELECT opened_at FROM sessions").fetchone()
    assert opened_at is not None


def test_create_app_twice_is_idempotent(db_path):
    create_app(db_path)
    create_app(db_path)
