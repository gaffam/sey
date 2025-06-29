import os
import sys
import tempfile
import sqlite3
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# configure temp db
path = os.path.join(tempfile.gettempdir(), "extra.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
os.environ["API_KEY"] = "tkey"

from gambusia.api import app
from gambusia.database import init_db

import asyncio
asyncio.get_event_loop().run_until_complete(init_db())
client = TestClient(app)


def clear_db():
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM readings")
        conn.commit()


def test_extra_sensor_storage():
    clear_db()
    payload = {
        "device_id": "e1",
        "temp": 25,
        "humidity": 70,
        "freq": 250,
        "image_verified": False,
        "lat": 0,
        "lon": 0,
        "extra_sensors": {"nh3": 55},
    }
    resp = client.post("/submit", json=payload, headers={"X-API-Key": "tkey"})
    assert resp.status_code == 200
    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT extra_sensors FROM readings").fetchone()
    assert row[0] is not None
