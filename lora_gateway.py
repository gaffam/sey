import serial
import requests
import json

API_URL = "http://localhost:8000/submit"
API_KEY = "your_api_key"

SERIAL_PORT = "/dev/ttyUSB0"
BAUDRATE = 9600


def parse_lora_message(line: str) -> dict:
    parts = line.strip().split(",")
    return {
        "temp": float(parts[0]),
        "humidity": float(parts[1]),
        "freq": int(parts[2]),
        "image_verified": parts[3].lower() == "true",
        "lat": float(parts[4]),
        "lon": float(parts[5]),
    }


def main() -> None:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=2)
    print("LoRa Gateway listening...")
    while True:
        line = ser.readline().decode("utf-8").strip()
        if not line:
            continue
        try:
            data = parse_lora_message(line)
            headers = {"x-api-key": API_KEY}
            r = requests.post(API_URL, json=data, headers=headers)
            print("Submitted:", data, "\u2192", r.status_code)
        except Exception as exc:
            print("Error:", exc)


if __name__ == "__main__":
    main()
