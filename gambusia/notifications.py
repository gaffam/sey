from __future__ import annotations
import os
from firebase_admin import messaging, credentials, initialize_app
from twilio.rest import Client

from .config import settings

registered_device_tokens: dict[str, str] = {}

# Initialize Firebase if credentials are available
firebase_ready = False
if os.path.exists("firebase-credentials.json"):
    cred = credentials.Certificate("firebase-credentials.json")
    initialize_app(cred)
    firebase_ready = True
else:
    print("Firebase credentials missing - push notifications disabled")


async def send_push_notification(device_id: str, risk_score: float) -> None:
    if not firebase_ready:
        return
    token = registered_device_tokens.get(device_id)
    if not token:
        return
    message = messaging.Message(
        notification=messaging.Notification(
            title="Yüksek Risk!",
            body=f"{device_id} noktasında risk skoru: {risk_score}",
        ),
        token=token,
    )
    messaging.send(message)


async def send_sms_alert(device_id: str, risk_score: float) -> None:
    sid = settings.TWILIO_SID
    token = settings.TWILIO_TOKEN
    from_number = settings.TWILIO_NUMBER
    to_number = settings.ALERT_PHONE
    if not all([sid, token, from_number, to_number]):
        return
    client = Client(sid, token)
    client.messages.create(
        body=f"Risk Uyarısı: {device_id} skor {risk_score}",
        from_=from_number,
        to=to_number,
    )
