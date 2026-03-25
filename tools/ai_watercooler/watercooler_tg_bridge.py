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


# --- Telegram handlers ---

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

async def poll_watercooler(context: ContextTypes.DEFAULT_TYPE):
    new_msgs = await fetch_new_messages()
    if not new_msgs:
        return

    # Don't forward Laura's own messages back to her
    new_msgs = [m for m in new_msgs if m.get("from_agent") != "laura"]

    if not new_msgs:
        return

    log.info("Forwarding %d new message(s) to Laura", len(new_msgs))
    for msg in new_msgs:
        text = format_for_telegram(msg)
        try:
            await context.bot.send_message(
                chat_id=LAURA_CHAT_ID,
                text=text,
            )
        except Exception as exc:
            log.error("Failed to send to Laura: %s", exc)


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

    laura_filter = filters.User(user_id=LAURA_CHAT_ID) & filters.TEXT & ~filters.COMMAND
    app.add_handler(MessageHandler(laura_filter, handle_message))
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
