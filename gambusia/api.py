from datetime import datetime, timezone
import json
from contextlib import asynccontextmanager
import asyncio
import logging
from fastapi import FastAPI, Form, WebSocket, WebSocketDisconnect, Security, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from redis import Redis

from .models import SensorData, RiskResponse
from .risk import calculate_risk, calculate_pesticide_risk, is_rice_field
from .database import get_db, init_db, Reading
from .config import settings
from .notifications import (
    send_push_notification,
    send_sms_alert,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("gambusia")

redis: Redis | None = None
API_KEY = settings.API_KEY
api_key_header = APIKeyHeader(name="X-API-Key")


class AlertBroadcaster:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, message: str) -> None:
        stale_connections: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_text(message)
            except Exception:
                stale_connections.append(ws)
        for ws in stale_connections:
            self.disconnect(ws)


alerts = AlertBroadcaster()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis
    await init_db()
    redis = Redis(host=settings.REDIS_HOST, decode_responses=True)
    try:
        yield
    finally:
        if redis is not None:
            try:
                redis.close()
            except Exception as exc:
                logger.warning("Redis close failed: %s", exc)


app = FastAPI(
    title="Gambusia - Risk API",
    description="API for collecting sensor data and calculating mosquito risk scores.",
    lifespan=lifespan,
)


async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


@app.post("/submit", response_model=RiskResponse)
async def submit_data(
    data: SensorData,
    api_key: str = Security(get_api_key),
    session: AsyncSession = Depends(get_db),
):
    if data.timestamp is None:
        data.timestamp = datetime.now(timezone.utc)
    cfg = "ipsala_risk_config.json" if is_rice_field(data.lat, data.lon) else None
    risk, reasons = calculate_risk(
        data.temp,
        data.humidity,
        data.freq,
        data.image_verified,
        timestamp=data.timestamp,
        config=cfg,
    )
    pesticide_risk, pest_reasons = calculate_pesticide_risk(data.extra_sensors)
    reading = Reading(
        timestamp=data.timestamp,
        device_id=data.device_id,
        temp=data.temp,
        humidity=data.humidity,
        freq=data.freq,
        image_verified=data.image_verified,
        lat=data.lat,
        lon=data.lon,
        extra_sensors=data.extra_sensors,
        risk_score=risk,
        pesticide_risk=pesticide_risk,
    )
    session.add(reading)
    logger.info("Reading received", extra={"device_id": data.device_id, "risk": risk})
    if risk >= 0.8:
        await send_push_notification(data.device_id, risk)
        await send_sms_alert(data.device_id, risk)
        await alerts.broadcast(
            f"ACIL: {data.device_id} noktasinda sivrisinek riski yuksek! skor: {risk}"
        )
    return RiskResponse(
        risk_score=risk,
        pesticide_risk=pesticide_risk,
        message="Veri alındı ve risk skoru hesaplandı.",
        reasons=reasons + pest_reasons,
    )


@app.post("/submit/sms", response_model=RiskResponse)
async def submit_via_sms(
    device_id: str = Form(...),
    temp: float = Form(...),
    humidity: float = Form(...),
    freq: int = Form(0),
    image_verified: bool = Form(False),
    lat: float = Form(...),
    lon: float = Form(...),
    api_key: str = Security(get_api_key),
    session: AsyncSession = Depends(get_db),
):
    data = SensorData(
        device_id=device_id,
        temp=temp,
        humidity=humidity,
        freq=freq,
        image_verified=image_verified,
        lat=lat,
        lon=lon,
    )
    return await submit_data(data, api_key=api_key, session=session)


@app.get("/map")
async def map_data(api_key: str = Security(get_api_key), session: AsyncSession = Depends(get_db)):
    cached = None
    if redis is not None:
        try:
            cached = redis.get("last_map")
        except Exception as exc:
            logger.warning("Redis cache read error: %s", exc)
    if cached:
        return json.loads(cached)
    result = await session.execute(select(Reading).order_by(Reading.id.desc()).limit(100))
    rows = result.scalars().all()
    results = [
        {
            "device_id": r.device_id,
            "lat": r.lat,
            "lon": r.lon,
            "temp": r.temp,
            "humidity": r.humidity,
            "freq": r.freq,
            "image_verified": r.image_verified,
            "extra_sensors": r.extra_sensors,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "risk_score": r.risk_score,
            "pesticide_risk": r.pesticide_risk,
        }
        for r in rows
    ]
    if redis is not None:
        try:
            redis.setex("last_map", 60, json.dumps(results))
        except Exception as exc:
            logger.warning("Redis cache write error: %s", exc)
    return results


@app.websocket("/alerts")
async def alert_notifier(websocket: WebSocket):
    api_key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")
    if api_key != API_KEY:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await alerts.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        alerts.disconnect(websocket)


@app.get("/map/geojson")
async def map_geojson(api_key: str = Security(get_api_key), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Reading).order_by(Reading.id.desc()).limit(100))
    rows = result.scalars().all()
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]},
            "properties": {
                "risk_score": r.risk_score,
                "pesticide_risk": r.pesticide_risk,
                **(r.extra_sensors or {}),
            },
        }
        for r in rows
    ]
    return JSONResponse({"type": "FeatureCollection", "features": features})
