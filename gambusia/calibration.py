"""Simple calibration state tracking for sensors."""

from typing import Dict


class CalibrationState:
    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        self.zero_points: Dict[str, float] = {}
        self.last_readings: Dict[str, float] = {}

    def update(self, current_readings: Dict[str, float]) -> None:
        self.last_readings = current_readings

    def set_zero_point(self, sensor: str, value: float) -> None:
        self.zero_points[sensor] = value

    def is_drift_detected(self) -> bool:
        for k, zero in self.zero_points.items():
            current = self.last_readings.get(k)
            if current is not None and abs(current - zero) > 5:
                return True
        return False
