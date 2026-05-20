import os
import sys
import tempfile
import sqlite3
import asyncio
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# configure temporary database before importing the app
db_path = os.path.join(tempfile.gettempdir(), "test_gambusia.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
os.environ["API_KEY"] = "testkey"

from gambusia.api import app
from gambusia.database import init_db

asyncio.run(init_db())
client = TestClient(app)


def clear_db():
    path = db_path
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM readings")
        conn.commit()


def test_submit_endpoint_inserts_row():
    clear_db()
    payload = {
        "device_id": "dev1",
        "temp": 30,
        "humidity": 65,
        "freq": 300,
        "image_verified": True,
        "lat": 1.0,
        "lon": 2.0,
        "extra_sensors": {"voc": 500, "nh3": 60},
    }
    response = client.post("/submit", json=payload, headers={"X-API-Key": "testkey"})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] > 0
    assert data["pesticide_risk"] > 0

    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("SELECT COUNT(*) FROM readings")
        count = cur.fetchone()[0]
    assert count == 1


def test_submit_invalid_input():
    clear_db()
    payload = {
        "device_id": "dev2",
        "temp": -100,
        "humidity": 50,
        "freq": 100,
        "image_verified": False,
        "lat": 0,
        "lon": 0,
    }
    resp = client.post("/submit", json=payload, headers={"X-API-Key": "testkey"})
    assert resp.status_code == 422


def test_timestamp_and_reasons_added():
    clear_db()
    payload = {
        "device_id": "dev3",
        "temp": 30,
        "humidity": 70,
        "freq": 300,
        "image_verified": True,
        "lat": 5.0,
        "lon": 6.0,
    }
    resp = client.post("/submit", json=payload, headers={"X-API-Key": "testkey"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["reasons"]
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT timestamp FROM readings ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row[0]


def test_map_endpoint_returns_data():
    clear_db()
    payload = {
        "device_id": "dev-map",
        "temp": 28,
        "humidity": 60,
        "freq": 350,
        "image_verified": False,
        "lat": 0,
        "lon": 0,
        "extra_sensors": {"voc": 450},
    }
    client.post("/submit", json=payload, headers={"X-API-Key": "testkey"})
    response = client.get("/map", headers={"X-API-Key": "testkey"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["extra_sensors"] == {"voc": 450}


def test_invalid_api_key():
    payload = {
        "device_id": "devX",
        "temp": 30,
        "humidity": 60,
        "freq": 300,
        "image_verified": False,
        "lat": 0,
        "lon": 0,
    }
    resp = client.post("/submit", json=payload, headers={"X-API-Key": "wrong"})
    assert resp.status_code == 403


def test_geojson_endpoint():
    clear_db()
    payload = {
        "device_id": "geo",
        "temp": 30,
        "humidity": 70,
        "freq": 300,
        "image_verified": True,
        "lat": 1,
        "lon": 1,
        "extra_sensors": {"ph": 6.8},
    }
    client.post("/submit", json=payload, headers={"X-API-Key": "testkey"})
    resp = client.get("/map/geojson", headers={"X-API-Key": "testkey"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert data["features"]
    props = data["features"][0]["properties"]
    assert "ph" in props


def test_websocket_alert():
    with client.websocket_connect("/alerts", headers={"X-API-Key": "testkey"}) as ws:
        payload = {
            "device_id": "ws1",
            "timestamp": "2026-07-15T10:00:00Z",
            "temp": 30,
            "humidity": 90,
            "freq": 300,
            "image_verified": True,
            "lat": 0,
            "lon": 0,
        }
        client.post("/submit", json=payload, headers={"X-API-Key": "testkey"})
        text = ws.receive_text()
        assert "ACIL" in text
