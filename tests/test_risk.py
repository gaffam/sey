import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime
from gambusia.risk import calculate_risk, is_rice_field, get_seasonal_weight


def test_calculate_risk_positive():
    ts = datetime(2024, 6, 1)
    score, reasons = calculate_risk(30, 65, 300, True, timestamp=ts)
    assert score == 0.8
    assert reasons


def test_calculate_risk_zero():
    ts = datetime(2024, 6, 1)
    score, reasons = calculate_risk(10, 40, 100, False, timestamp=ts)
    assert score == 0.0
    assert "seasonal_weight" in reasons[-1]


def test_custom_config():
    config = {
        "temp": {"min": 0, "max": 10, "weight": 0.5, "reason": "soğuk"},
    }
    ts = datetime(2024, 1, 1)
    score, reasons = calculate_risk(5, 0, 0, False, timestamp=ts, config=config)
    assert score == 0.1
    assert "soğuk" in reasons


def test_is_rice_field():
    assert is_rice_field(40.95, 26.4)
    assert not is_rice_field(39.0, 28.0)


def test_get_seasonal_weight():
    assert get_seasonal_weight(6) == 0.8
    assert get_seasonal_weight(1) == 0.2
