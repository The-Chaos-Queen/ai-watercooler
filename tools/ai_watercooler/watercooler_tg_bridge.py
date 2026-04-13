#!/usr/bin/env python3
"""
watercooler_tg_bridge.py — Bridges Laura's Telegram to the AI Watercooler.

Laura sends a message on Telegram -> posted to the watercooler as "laura".
New watercooler messages -> forwarded to Laura on Telegram.

Config via environment variables (see .env file):
  TG_TOKEN, LAURA_CHAT_ID, WC_URL, WC_TOKEN, WC_THREAD, POLL_INTERVAL
"""

import logging
import os
import time

import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

TG_TOKEN = os.environ["TG_TOKEN"]
LAURA_CHAT_ID = int(os.environ["LAURA_CHAT_ID"])
WC_URL = os.environ.get("WC_URL", "http://192.168.2.55:8765")
WC_TOKEN = os.environ["WC_TOKEN"]
WC_THREAD = os.environ.get("WC_THREAD", "mamba-bridge")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))

# Vision model for image descriptions
VISION_URL = os.environ.get("VISION_URL", "http://192.168.2.68:1234/v1")  # Laura's laptop LMStudio
VISION_MODEL = os.environ.get("VISION_MODEL", "qwen3.5-2b")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("wc_bridge")

_last_seen_id = 0


def _wc_headers():
    return {
        "Authorization": f"Bearer {WC_TOKEN}",
        "Content-Type": "application/json",
    }


async def post_to_watercooler(body, to_agent="all"):
    payload = {
        "thread": WC_THREAD,
        "body": body,
        "to_agent": to_agent,
        "lang": "en",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{WC_URL}/v1/post",
                json=payload,
                headers=_wc_headers(),
            )
        r.raise_for_status()
        data = r.json()
        log.info("Posted to watercooler (id=%s): %s", data.get("id"), body[:80])
        return True
    except Exception as exc:
        log.error("Watercooler POST failed: %s", exc)
        return False


async def fetch_new_messages():
    global _last_seen_id
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{WC_URL}/v1/messages",
                params={"thread": WC_THREAD, "limit": "20"},
                headers=_wc_headers(),
            )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        log.error("Watercooler GET failed: %s", exc)
        return []

    messages = data.get("messages", [])
    new_msgs = [m for m in messages if m["id"] > _last_seen_id]

    if new_msgs:
        _last_seen_id = max(m["id"] for m in new_msgs)

    # Return oldest first
    return sorted(new_msgs, key=lambda m: m["id"])


def format_for_telegram(msg):
    sender = msg.get("from_agent", "?")
    to = msg.get("to_agent", "all")
    topic = msg.get("topic", "")
    body = msg.get("body", "")
    ts = msg.get("ts", "")[:16]

    header = f"{sender} -> {to}"
    if topic:
        header += f" [{topic}]"

    # Truncate long messages for Telegram (max 4096 chars)
    if len(body) > 3500:
        body = body[:3500] + "\n[...truncated]"

    return f"#{msg['id']} {ts}\n{header}\n\n{body}"


# --- Vision ---

async def describe_image(image_bytes: bytes, caption: str = "") -> str:
    """Send an image to the local vision model and get a description."""
    import base64
    b64 = base64.b64encode(image_bytes).decode()

    prompt = "Describe this image concisely. If it contains text, transcribe the key points in the original language."
    if caption:
        prompt = f"Image caption from sender: '{caption}'. Describe the image. If it contains text, transcribe key points in the original language."

    payload = {
        "model": VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]
        }],
        "max_tokens": 400,
        "temperature": 0.3,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{VISION_URL}/chat/completions",
                json=payload,
            )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        log.warning("Vision model failed: %s", exc)
        return "(image - vision model unavailable)"


# --- Telegram handlers ---

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages: describe via vision model, post to watercooler."""
    photo = update.message.photo[-1]  # largest resolution
    caption = update.message.caption or ""

    await update.message.reply_text("Analyzing image...")

    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    description = await describe_image(bytes(image_bytes), caption)

    # Build watercooler post
    to_agent = "all"
    if caption.startswith("@"):
        parts = caption.split(" ", 1)
        if len(parts) == 2:
            to_agent = parts[0][1:]
            caption = parts[1]

    body = f"[IMAGE] {description}"
    if caption:
        body = f"[IMAGE] {caption}\n\nVision: {description}"

    ok = await post_to_watercooler(body, to_agent=to_agent)
    if ok:
        await update.message.reply_text(f"-> watercooler ({to_agent})\n\nVision: {description[:200]}")
    else:
        await update.message.reply_text("ERROR: watercooler unreachable")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return

    # Check for @mention routing: "@pinky do something" -> to_agent=pinky
    to_agent = "all"
    if text.startswith("@"):
        parts = text.split(" ", 1)
        if len(parts) == 2:
            to_agent = parts[0][1:]  # strip @
            text = parts[1]

    ok = await post_to_watercooler(text, to_agent=to_agent)
    if ok:
        await update.message.reply_text(f"-> watercooler ({to_agent})")
    else:
        await update.message.reply_text("ERROR: watercooler unreachable")


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Watercooler Bridge\n"
        f"URL: {WC_URL}\n"
        f"Thread: {WC_THREAD}\n"
        f"Poll: {POLL_INTERVAL}s\n"
        f"Last seen: #{_last_seen_id}"
    )


# --- Poll job ---

URGENT_KEYWORDS = {"urgent", "stop", "down", "fail", "error", "alarm", "emergency", "critical", "broken"}


def should_forward_to_laura(msg: dict) -> str | None:
    """Decide if a message should be forwarded to Laura's Telegram.
    Returns the reason string, or None to skip."""
    if msg.get("from_agent") == "laura":
        return None  # don't echo her own messages

    to = (msg.get("to_agent") or "").lower()
    body_lower = (msg.get("body") or "").lower()
    topic = (msg.get("topic") or "").lower()

    # Direct: addressed to Laura
    if to == "laura" or "@laura" in body_lower:
        return "addressed"

    # Urgent: keywords in body or topic
    if any(kw in body_lower for kw in URGENT_KEYWORDS) or any(kw in topic for kw in URGENT_KEYWORDS):
        return "urgent"

    # Nightwatch alerts always forward
    if "nightwatch" in topic and ("alert" in topic or "urgent" in body_lower):
        return "nightwatch"

    return None  # everything else stays on the watercooler


async def poll_watercooler(context: ContextTypes.DEFAULT_TYPE):
    new_msgs = await fetch_new_messages()
    if not new_msgs:
        return

    forwarded = 0
    for msg in new_msgs:
        reason = should_forward_to_laura(msg)
        if reason:
            text = format_for_telegram(msg)
            prefix = "URGENT" if reason == "urgent" else ""
            if prefix:
                text = f"{prefix}\n\n{text}"
            try:
                await context.bot.send_message(
                    chat_id=LAURA_CHAT_ID,
                    text=text,
                )
                forwarded += 1
            except Exception as exc:
                log.error("Failed to send to Laura: %s", exc)

    total = len(new_msgs)
    if forwarded > 0:
        log.info("Forwarded %d/%d messages to Laura", forwarded, total)
    elif total > 0:
        log.info("Skipped %d messages (none addressed to Laura)", total)


# --- Startup: set _last_seen_id to current max so we don't replay history ---

async def init_last_seen(app):
    global _last_seen_id
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{WC_URL}/v1/messages",
                params={"thread": WC_THREAD, "limit": "1"},
                headers=_wc_headers(),
            )
        r.raise_for_status()
        data = r.json()
        messages = data.get("messages", [])
        if messages:
            _last_seen_id = max(m["id"] for m in messages)
            log.info("Initialized last_seen_id to %d", _last_seen_id)
    except Exception as exc:
        log.warning("Could not init last_seen_id: %s", exc)


def main():
    log.info("Starting Watercooler-Telegram bridge")
    log.info("  Thread: %s | Poll: %ds | Laura: %d", WC_THREAD, POLL_INTERVAL, LAURA_CHAT_ID)

    app = ApplicationBuilder().token(TG_TOKEN).post_init(init_last_seen).build()

    laura_text = filters.User(user_id=LAURA_CHAT_ID) & filters.TEXT & ~filters.COMMAND
    laura_photo = filters.User(user_id=LAURA_CHAT_ID) & filters.PHOTO
    app.add_handler(MessageHandler(laura_text, handle_message))
    app.add_handler(MessageHandler(laura_photo, handle_photo))
    app.add_handler(CommandHandler("status", handle_status, filters=filters.User(user_id=LAURA_CHAT_ID)))

    app.job_queue.run_repeating(
        poll_watercooler,
        interval=POLL_INTERVAL,
        first=10,
        name="wc_poll",
    )

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
