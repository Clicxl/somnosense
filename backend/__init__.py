import os
import sqlite3
from pathlib import Path

from flask import Flask


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = str(
        db_path or os.environ.get("SOMNOSENSE_DB") or Path(__file__).parent / "somnosense.db"
    )

    db = sqlite3.connect(app.config["DATABASE"])
    try:
        db.executescript((Path(__file__).parent / "schema.sql").read_text())
    finally:
        db.close()  # sqlite3's `with` doesn't close; Windows keeps the file locked

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
