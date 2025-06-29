from datetime import datetime
import json
from contextlib import asynccontextmanager
import asyncio
import logging
from fastapi import FastAPI, Form, WebSocket, WebSocketDisconnect, Security, HTTPException, Depends
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
    registered_device_tokens,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("gambusia")
alerts_queue: asyncio.Queue[dict] = asyncio.Queue()

redis: Redis | None = None
API_KEY = settings.API_KEY
api_key_header = APIKeyHeader(name="X-API-Key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis
    await init_db()
    redis = Redis(host="localhost", decode_responses=True)
    try:
        yield
    finally:
        if redis is not None:
            try:
                redis.close()
            except Exception:
                pass


app = FastAPI(
    title="Gambusia - Risk API",
    description="API for collecting sensor data and calculating mosquito risk scores.",
    lifespan=lifespan,
)


async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


@app.post(
    "/submit",
    response_model=RiskResponse,
    summary="Submit a sensor reading",
    description="""Record a new reading and return the calculated risk score.""",
)
async def submit_data(
    data: SensorData,
    api_key: str = Security(get_api_key),
    session: AsyncSession = Depends(get_db),
):
    if data.timestamp is None:
        data.timestamp = datetime.utcnow()
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
    )
    session.add(reading)
    logger.info(
        "Reading received", extra={"device_id": data.device_id, "risk": risk}
    )
    if risk > 0.8:
        await send_push_notification(data.device_id, risk)
        await send_sms_alert(data.device_id, risk)
        alerts_queue.put_nowait({"device_id": data.device_id, "risk_score": risk})
    return RiskResponse(
        risk_score=risk,
        pesticide_risk=pesticide_risk,
        message="Veri alındı ve risk skoru hesaplandı.",
        reasons=reasons + pest_reasons,
    )


@app.post(
    "/submit/sms",
    response_model=RiskResponse,
    summary="Submit sensor data via SMS",
    description="Accept form-encoded sensor data for low-tech devices.",
)
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


@app.get(
    "/map",
    summary="Retrieve recent readings",
    description="Return last 100 readings with calculated risk scores.",
)
async def map_data(
    api_key: str = Security(get_api_key),
    session: AsyncSession = Depends(get_db),
):
    cached = None
    if redis is not None:
        try:
            cached = redis.get("last_map")
        except Exception:
            cached = None
    if cached:
        return json.loads(cached)
    result = await session.execute(
        select(Reading).order_by(Reading.id.desc()).limit(100)
    )
    rows = result.scalars().all()
    results = []
    for r in rows:
        risk, reasons = calculate_risk(
            r.temp, r.humidity, r.freq, r.image_verified, timestamp=r.timestamp
        )
        pest_risk, _ = calculate_pesticide_risk(r.extra_sensors)
        results.append(
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
                "risk_score": risk,
                "reasons": reasons,
                "pesticide_risk": pest_risk,
            }
        )
    if redis is not None:
        try:
            redis.setex("last_map", 60, json.dumps(results))
        except Exception as e:
            print(f"Redis cache write error: {e}")
    return results


@app.websocket("/alerts")
async def alert_notifier(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            msg = await alerts_queue.get()
            await websocket.send_text(
                f"ACIL: {msg['device_id']} noktasinda sivrisinek riski yuksek! skor: {msg['risk_score']}"
            )
    except WebSocketDisconnect:
        pass


@app.get(
    "/map/geojson",
    summary="Retrieve recent readings as GeoJSON",
    description="Return last 100 readings formatted as GeoJSON FeatureCollection.",
)
async def map_geojson(
    api_key: str = Security(get_api_key),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(Reading).order_by(Reading.id.desc()).limit(100)
    )
    rows = result.scalars().all()
    features = []
    for r in rows:
        risk, _ = calculate_risk(
            r.temp, r.humidity, r.freq, r.image_verified, timestamp=r.timestamp
        )
        pest_risk, _ = calculate_pesticide_risk(r.extra_sensors)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]},
                "properties": {
                    "risk_score": risk,
                    "pesticide_risk": pest_risk,
                    **(r.extra_sensors or {}),
                },
            }
        )
    return JSONResponse({"type": "FeatureCollection", "features": features})
