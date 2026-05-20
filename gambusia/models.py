from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class SensorData(BaseModel):
    """Incoming sensor reading."""

    device_id: str
    timestamp: Optional[datetime] = None
    temp: float = Field(..., ge=10, le=50, description="Temperature in Celsius")
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity %")
    freq: int = Field(..., ge=0, le=2000, description="Wing beat frequency in Hz")
    image_verified: bool
    lat: float
    lon: float
    extra_sensors: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional chemical sensor readings as key/value pairs",
    )


class RiskResponse(BaseModel):
    risk_score: float
    pesticide_risk: float | None = None
    message: str
    reasons: list[str]
