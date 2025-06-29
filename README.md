# Gambusia API

This project exposes a minimal API for collecting mosquito sensor readings and computing a risk score. It uses FastAPI with an async SQLAlchemy ORM layer.
By default the application expects a running PostgreSQL instance and reads the connection string from `DATABASE_URL`.

## Setup

Create a Python environment and install dependencies:

```bash
pip install -r requirements.txt
```

Redis must be running locally for caching features. Endpoints are protected with a simple API key provided via the `X-API-Key` header. Set `API_KEY` in your `.env` file before starting the server.

Database tables are created automatically on startup for convenience. For
production deployments consider managing schema changes with a migration tool
such as **Alembic**.

## Running the server

Use `main.py` to start the service. All configuration values are loaded from
environment variables via `gambusia.config`. Copy `.env.example` to `.env` and
adjust the values before starting the server:

```bash
HOST=0.0.0.0
PORT=8000
API_KEY=your_api_key
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db/gambusia
# optional notification settings
TWILIO_SID=your_account_sid
TWILIO_TOKEN=your_auth_token
TWILIO_NUMBER=+1xxxxxxxxxx
ALERT_PHONE=+1xxxxxxxxxx
```

```bash
python main.py
```

## API Endpoints

### POST /submit
Stores a single sensor reading and returns a risk score with reasons.

### POST /submit/sms
Form-based variant for low-tech devices sending readings via SMS gateway.

### GET /map
Returns the last 100 readings along with their risk scores.

### GET /map/geojson
Returns the same data formatted as GeoJSON for GIS tools.

### WebSocket /alerts
Sends a text alert when incoming data includes a risk score over 0.8.

## Testing

```bash
pytest -q
```

## Docker

Build and run the application inside a container:

```bash
docker build -t gambusia .
docker run -p 8000:8000 gambusia
```

For local development you can start PostgreSQL and Redis using Docker Compose:

```bash
docker-compose up -d
```

## Continuous Integration

This repository includes a simple GitHub Actions workflow that installs dependencies and runs the tests on each push.

## LoRa Gateway

`lora_gateway.py` demonstrates how to read LoRa messages from a serial port and
forward them to the API using HTTP requests. Adjust the serial settings and API
key as needed for your deployment.

## Notifications

Push notifications use Firebase if `firebase-credentials.json` is present.
SMS alerts are sent via Twilio when the following environment variables are set:
`TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_NUMBER` and `ALERT_PHONE`.
