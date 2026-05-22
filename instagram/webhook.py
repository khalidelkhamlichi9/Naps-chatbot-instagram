import os
import json
import hashlib
import hmac
import logging
from typing import Iterator

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse

from database.engine import AsyncSessionLocal
from core.pipeline import process_message
from instagram.sender import send_instagram_message

logger = logging.getLogger("naps-chatbot.instagram")
router = APIRouter(prefix="/webhook", tags=["Instagram Webhook"])

META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")


def _is_meta_dashboard_test(sender_id: str, text: str) -> bool:
    """Sample payload from Meta 'Test' button uses fake ids — do not call Send API."""
    return sender_id in ("12334",) or text in ("random_text", "meta_webhook_test")


def _yield_from_message_value(value: dict) -> Iterator[tuple[str, str]]:
    message = value.get("message", {}) or {}
    if message.get("is_echo"):
        return
    sender_id = value.get("sender", {}).get("id")
    text = (message.get("text") or "").strip()
    # Meta "Send to My Server" test often sends only mid, no text
    if not text and message.get("mid") and _is_meta_dashboard_test(str(sender_id or ""), ""):
        text = "meta_webhook_test"
    if sender_id and text:
        yield sender_id, text


def _iter_incoming_messages(payload: dict) -> Iterator[tuple[str, str]]:
    """Yield (sender_id, text) from Meta webhook payloads."""
    # Meta dashboard "Send to My Server" sample format
    sample = payload.get("sample")
    if isinstance(sample, dict) and sample.get("field") == "messages":
        yield from _yield_from_message_value(sample.get("value") or {})

    # Alternate test shape: { "field": "messages", "value": { ... } }
    if payload.get("field") == "messages":
        yield from _yield_from_message_value(payload.get("value") or {})

    for entry in payload.get("entry", []):
        for messaging in entry.get("messaging", []):
            sender_id = messaging.get("sender", {}).get("id")
            message = messaging.get("message", {}) or {}
            if message.get("is_echo"):
                continue
            text = (message.get("text") or "").strip()
            if not text and "quick_reply" in message:
                text = (message["quick_reply"].get("payload") or "").strip()
            if sender_id and text:
                yield sender_id, text

        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue
            value = change.get("value", {}) or {}
            message = value.get("message", {}) or {}
            if message.get("is_echo"):
                continue
            sender_id = value.get("sender", {}).get("id")
            text = (message.get("text") or "").strip()
            if sender_id and text:
                yield sender_id, text


@router.get("/instagram")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        logger.info("Meta webhook verified")
        return PlainTextResponse(content=challenge or "")

    raise HTTPException(status_code=403, detail="Webhook verification failed")


async def _handle_dm(sender_id: str, text: str):
    logger.info("DM from %s: %s", sender_id, text[:80])

    if _is_meta_dashboard_test(sender_id, text):
        logger.info(
            "Meta dashboard test received OK (sample user — no Instagram reply sent)"
        )
        return

    async with AsyncSessionLocal() as session:
        try:
            answer = await process_message(
                message=text,
                user_id=sender_id,
                session=session,
                stream=False,
            )
            ok = await send_instagram_message(recipient_id=sender_id, text=answer)
            if not ok:
                logger.error("Failed to send Instagram reply to %s", sender_id)
        except Exception as e:
            logger.exception("Pipeline error for user %s: %s", sender_id, e)
            await send_instagram_message(
                recipient_id=sender_id,
                text="Désolé, une erreur est survenue. Réessayez dans quelques instants.",
            )


@router.post("/instagram")
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
):
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()
    _verify_signature(body, signature)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid webhook JSON body")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    obj = payload.get("object")
    logger.info("Instagram webhook POST: object=%s entries=%s", obj, len(payload.get("entry", [])))

    if obj and obj not in ("instagram", "page"):
        logger.warning("Unexpected webhook object type: %s", obj)

    found = False
    for sender_id, text in _iter_incoming_messages(payload):
        found = True
        background_tasks.add_task(_handle_dm, sender_id, text)

    if not found:
        logger.warning(
            "Webhook POST received but no message parsed. Keys: %s",
            list(payload.keys()),
        )

    return {"status": "ok"}


def _verify_signature(body: bytes, signature: str):
    if not META_APP_SECRET:
        return
    if not signature:
        raise HTTPException(status_code=403, detail="Missing X-Hub-Signature-256")
    expected = "sha256=" + hmac.new(
        META_APP_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        logger.warning(
            "Invalid Meta webhook signature — vérifiez META_APP_SECRET "
            "(Instagram App Secret du même app que le webhook, pas un autre app)"
        )
        raise HTTPException(status_code=403, detail="Invalid Meta signature")
