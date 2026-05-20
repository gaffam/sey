from __future__ import annotations
import os
import asyncio
import logging
from firebase_admin import messaging, credentials, initialize_app
from twilio.rest import Client

from .config import settings

registered_device_tokens: dict[str, str] = {}
logger = logging.getLogger("gambusia")
_firebase_ready: bool | None = None


def _ensure_firebase_initialized() -> bool:
    global _firebase_ready
    if _firebase_ready is not None:
        return _firebase_ready
    if os.path.exists("firebase-credentials.json"):
        cred = credentials.Certificate("firebase-credentials.json")
        initialize_app(cred)
        _firebase_ready = True
    else:
        logger.warning("Firebase credentials missing - push notifications disabled")
        _firebase_ready = False
    return _firebase_ready


def _send_firebase_message(device_id: str, risk_score: float, token: str) -> None:
    message = messaging.Message(
        notification=messaging.Notification(
            title="Yüksek Risk!",
            body=f"{device_id} noktasında risk skoru: {risk_score}",
        ),
        token=token,
    )
    messaging.send(message)


async def send_push_notification(device_id: str, risk_score: float) -> None:
    if not _ensure_firebase_initialized():
        return
    token = registered_device_tokens.get(device_id)
    if not token:
        return
    await asyncio.to_thread(_send_firebase_message, device_id, risk_score, token)


def _send_twilio_message(device_id: str, risk_score: float, sid: str, token: str, from_number: str, to_number: str) -> None:
    client = Client(sid, token)
    client.messages.create(
        body=f"Risk Uyarısı: {device_id} skor {risk_score}",
        from_=from_number,
        to=to_number,
    )


async def send_sms_alert(device_id: str, risk_score: float) -> None:
    sid = settings.TWILIO_SID
    token = settings.TWILIO_TOKEN
    from_number = settings.TWILIO_NUMBER
    to_number = settings.ALERT_PHONE
    if not all([sid, token, from_number, to_number]):
        return
    await asyncio.to_thread(_send_twilio_message, device_id, risk_score, sid, token, from_number, to_number)
