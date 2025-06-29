"""Risk scoring utilities."""

import json
import os
from typing import Tuple, Union
from .fusion import fuse_pesticide_signals
from datetime import datetime
from shapely.geometry import Point, Polygon

# polygon for Ipsala rice fields (rough bounding box)
IPSALA_POLYGON = [
    (26.3, 40.9),
    (26.5, 40.9),
    (26.5, 41.0),
    (26.3, 41.0),
]
_POLYGON = Polygon(IPSALA_POLYGON)


def is_rice_field(lat: float, lon: float) -> bool:
    """Return True if given coordinates fall into the Ipsala rice field area."""
    return Point(lon, lat).within(_POLYGON)


def get_seasonal_weight(month: int) -> float:
    """Return risk multiplier based on the month."""
    return 0.8 if 6 <= month <= 9 else 0.2


DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "risk_config.json")


def load_config(path: str = DEFAULT_CONFIG) -> dict:
    """Load risk calculation configuration from ``path``."""

    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def calculate_risk(
    temp: float,
    humidity: float,
    freq: int,
    image_verified: bool,
    *,
    timestamp: datetime | None = None,
    config: Union[dict, str, None] = None,
) -> Tuple[float, list[str]]:
    """Calculate risk score using a configuration file.

    Parameters
    ----------
    temp : float
        Temperature reading.
    humidity : float
        Humidity reading.
    freq : int
        Wing beat frequency.
    image_verified : bool
        Whether an image verification succeeded.
    timestamp : datetime | None
        Time of the reading for seasonal weighting.
    config : dict | None
        Optional configuration. If not provided, ``risk_config.json`` is used.

    Returns
    -------
    Tuple[float, list[str]]
        Final risk score and a list of reasons that contributed to the score.
    """

    if config is None:
        config_dict = load_config()
    elif isinstance(config, str):
        config_dict = load_config(config)
    else:
        config_dict = config

    score = 0.0
    reasons: list[str] = []

    # temperature check
    temp_cfg = config_dict.get("temp", {})
    if temp_cfg:
        if temp_cfg.get("min") <= temp <= temp_cfg.get("max"):
            score += temp_cfg.get("weight", 0)
            reasons.append(temp_cfg.get("reason", "temperature"))

    # humidity check
    hum_cfg = config_dict.get("humidity", {})
    if hum_cfg:
        if humidity > hum_cfg.get("threshold", 0):
            score += hum_cfg.get("weight", 0)
            reasons.append(hum_cfg.get("reason", "humidity"))

    # frequency check
    freq_cfg = config_dict.get("freq", {})
    if freq_cfg:
        if freq_cfg.get("min") <= freq <= freq_cfg.get("max"):
            score += freq_cfg.get("weight", 0)
            reasons.append(freq_cfg.get("reason", "freq"))

    # image verification check
    img_cfg = config_dict.get("image_verified", {})
    if img_cfg and image_verified:
        score += img_cfg.get("weight", 0)
        reasons.append(img_cfg.get("reason", "image_verified"))

    if timestamp is None:
        timestamp = datetime.utcnow()
    weight = get_seasonal_weight(timestamp.month)
    score *= weight
    reasons.append(f"seasonal_weight={weight}")

    return round(score, 2), reasons


def calculate_pesticide_risk(extra: dict | None) -> Tuple[float, list[str]]:
    """Wrapper around :func:`fuse_pesticide_signals` for convenience."""

    score, reasons = fuse_pesticide_signals(extra)
    return score, reasons

