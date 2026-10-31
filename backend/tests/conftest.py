import sqlite3
from contextlib import closing

import pytest

from backend import create_app


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def app(db_path):
    return create_app(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


def sql(db_path, query, *args):
    with closing(sqlite3.connect(db_path)) as db, db:
        return db.execute(query, args).fetchall()


def reading(sensor="heart_rate", value=60, recorded_at="2026-10-31T23:00:30Z", simulated=True):
    return {"sensor": sensor, "value": value, "recorded_at": recorded_at, "simulated": simulated}
