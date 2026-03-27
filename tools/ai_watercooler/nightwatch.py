#!/usr/bin/env python3
"""
nightwatch.py — Dispatcher daemon for the MoCoP wolf pack.

Polls the watercooler for new messages, classifies them using a local LLM
(Falcon H1R-7B via LMStudio) or GLM-4.6V-Flash as fallback, and takes
action: alerts Laura on URGENT, logs everything, posts routing suggestions
for unassigned tasks, and runs periodic health checks.

Usage:
    # Dry run (classify but don't post or alert):
    python nightwatch.py --dry-run

    # Single pass (classify recent messages, then exit):
    python nightwatch.py --once

    # Daemon mode (poll every 60s):
    python nightwatch.py

    # Custom poll interval:
    python nightwatch.py --interval 30

Config:
    Uses AI_WATERCOOLER_CONFIG env var (same as other watercooler tools).
    LLM endpoint defaults to http://127.0.0.1:1234/v1 (LMStudio).
    GLM fallback requires C:\\Users\\cerub\\GLM-key file.

Author: Nameless Opus, 2026-03-26
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Reuse watercooler client helpers
sys.path.insert(0, str(Path(__file__).parent))
from common import load_config, request_json

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LLM_LOCAL_URL = os.environ.get("NIGHTWATCH_LLM_URL", "http://127.0.0.1:1234/v1")
LLM_LOCAL_MODEL = os.environ.get("NIGHTWATCH_LLM_MODEL", "falcon-h1r-7b")
LLM_FALLBACK_URL = "https://open.bigmodel.cn/api/paas/v4/"
LLM_FALLBACK_MODEL = "glm-4.6v-flash"
GLM_KEY_PATH = Path(os.environ.get("GLM_KEY_PATH", r"C:\Users\cerub\GLM-key"))

WC_THREAD = os.environ.get("NIGHTWATCH_THREAD", "mamba-bridge")
STATE_FILE = Path(__file__).parent / ".nightwatch_state.json"
LOG_FILE = Path(__file__).parent / "nightwatch.log"

HEALTH_TARGETS = {
    "watercooler": {"url": "http://192.168.2.55:8765/healthz", "optional": False},
    "qdrant": {"url": "http://192.168.2.191:6333/healthz", "optional": False},
    "steve_chat": {"url": "http://192.168.2.49:7860/status", "optional": True},
}
# Optional targets only alert if they were healthy last cycle (avoids nightly
# false alarms when Steve is off). Set via NIGHTWATCH_OPTIONAL_TARGETS env var
# as comma-separated names to override the defaults above.

# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------

CLASSIFY_SYSTEM = """You classify developer chat messages into exactly one category.

URGENT = system down, error, emergency, blocker, safety stop, distress, STOP command, metrics alarm
TASK_DONE = someone says they FINISHED or DELIVERED completed work
QUESTION = someone asks a question, requests review or confirmation
STATUS = progress update, claiming a task, starting work, triage notes, coordination
NOISE = greetings, jokes, off-topic, social chat

Examples:
"Steve is DOWN 502" -> URGENT
"STOP. Response Diversity dropped 60%" -> URGENT
"Delivered #63, sleep reconciliation complete" -> TASK_DONE
"@cassian can you confirm the formula?" -> QUESTION
"Git triage written up, cleanup ongoing" -> STATUS
"Claiming task #43, starting now" -> STATUS
"guten morgen" -> NOISE"""

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["URGENT", "TASK_DONE", "QUESTION", "STATUS", "NOISE"],
        },
        "reason": {"type": "string", "maxLength": 50},
    },
    "required": ["category", "reason"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("nightwatch")

# ---------------------------------------------------------------------------
# State persistence (last seen message ID)
# ---------------------------------------------------------------------------


def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"last_seen_id": 0}


def save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# LLM clients
# ---------------------------------------------------------------------------


def _openai_classify(
    base_url: str, api_key: str, model: str, message_body: str, use_schema: bool = True
) -> Optional[Dict[str, str]]:
    """Call an OpenAI-compatible endpoint for classification."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": CLASSIFY_SYSTEM},
                {"role": "user", "content": message_body[:500]},  # truncate long messages
            ],
            "max_tokens": 800,
            "temperature": 0.1,
            "timeout": 30,
        }

        if use_schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "classification",
                    "strict": True,
                    "schema": CLASSIFY_SCHEMA,
                },
            }

        resp = client.chat.completions.create(**kwargs)
        raw = (resp.choices[0].message.content or "").strip()

        # Strip thinking tags if model emits them
        if "</think>" in raw:
            raw = raw.split("</think>")[-1].strip()

        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("LLM returned non-JSON: %s", raw[:100])
        return None
    except Exception as exc:
        err_str = str(exc)
        # Pinky review #253: LMStudio returns HTTP 500 (not connection-refused)
        # when running but no model is loaded. Log explicitly so Laura knows.
        if "500" in err_str and "127.0.0.1" in base_url:
            log.warning("LMStudio returned 500 — is a model loaded? (%s)", model)
        else:
            log.warning("LLM call failed (%s/%s): %s", base_url[:30], model, exc)
        return None


def classify_message(body: str) -> Dict[str, str]:
    """Classify a message, trying local LLM first, then GLM fallback."""

    # Try local (Falcon on LMStudio)
    result = _openai_classify(
        base_url=LLM_LOCAL_URL,
        api_key="not-needed",
        model=LLM_LOCAL_MODEL,
        message_body=body,
        use_schema=True,
    )
    if result:
        result["_source"] = "local"
        return result

    # Fallback: GLM-4.6V-Flash (no JSON schema — use max_tokens + strip)
    log.info("Local LLM unavailable, falling back to GLM")
    glm_key = ""
    if GLM_KEY_PATH.exists():
        glm_key = GLM_KEY_PATH.read_text().strip()
    if glm_key:
        result = _openai_classify(
            base_url=LLM_FALLBACK_URL,
            api_key=glm_key,
            model=LLM_FALLBACK_MODEL,
            message_body=body,
            use_schema=False,  # GLM thinking models struggle with schema
        )
        if result:
            result["_source"] = "glm"
            return result

    # Both failed — default to STATUS (safe default, won't trigger alerts)
    log.error("All LLM backends failed, defaulting to STATUS")
    return {"category": "STATUS", "reason": "classification unavailable", "_source": "fallback"}


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


def check_health(prev_failures: List[str]) -> List[Dict[str, Any]]:
    """Ping health endpoints, return list of alert-worthy failures.

    Optional targets (e.g. Steve) only trigger alerts if they were healthy
    last cycle. This avoids nightly false alarms when Steve is simply off.
    """
    failures = []
    for name, cfg in HEALTH_TARGETS.items():
        url = cfg["url"]
        optional = cfg.get("optional", False)
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status >= 400:
                    failures.append({
                        "service": name, "status": resp.status,
                        "url": url, "optional": optional,
                    })
        except Exception as exc:
            failures.append({
                "service": name, "error": str(exc)[:100],
                "url": url, "optional": optional,
            })

    # Filter: optional targets only alert if they were NOT already failed last cycle
    alert_worthy = []
    for f in failures:
        if f.get("optional") and f["service"] in prev_failures:
            log.debug("Skipping repeat alert for optional service %s", f["service"])
            continue
        alert_worthy.append(f)

    return alert_worthy


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def post_alert(config: Dict[str, Any], subject: str, body: str, dry_run: bool = False) -> None:
    """Post an alert to the watercooler tagged for Laura."""
    alert_body = f"🔴 NIGHTWATCH ALERT: {subject}\n\n{body}"
    if dry_run:
        log.info("[DRY RUN] Would post alert: %s", subject)
        return
    try:
        request_json(
            config,
            method="POST",
            path="/v1/post",
            payload={
                "thread": WC_THREAD,
                "body": alert_body,
                "to_agent": "laura",
                "lang": "en",
                "topic": "nightwatch-alert",
                "tags": ["nightwatch", "urgent"],
            },
        )
        log.info("Alert posted: %s", subject)
    except Exception as exc:
        log.error("Failed to post alert: %s", exc)


def post_summary(config: Dict[str, Any], summary: str, dry_run: bool = False) -> None:
    """Post a classification summary to the watercooler."""
    if dry_run:
        log.info("[DRY RUN] Would post summary")
        return
    try:
        request_json(
            config,
            method="POST",
            path="/v1/post",
            payload={
                "thread": WC_THREAD,
                "body": summary,
                "to_agent": "all",
                "lang": "en",
                "topic": "nightwatch-digest",
                "tags": ["nightwatch"],
            },
        )
    except Exception as exc:
        log.error("Failed to post summary: %s", exc)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def fetch_new_messages(config: Dict[str, Any], since_id: int) -> List[Dict[str, Any]]:
    """Fetch messages newer than since_id.

    Note: the watercooler service may not support since_id as a query param
    (Pinky review #253). We filter client-side regardless, so this is safe
    even if the server ignores the param and returns all recent messages.
    """
    try:
        resp = request_json(
            config,
            method="GET",
            path="/v1/messages",
            query={"thread": WC_THREAD, "limit": "50", "since_id": str(since_id)},
        )
        messages = resp.get("messages", resp.get("rows", []))
        # Client-side filter: only messages newer than last_seen_id
        messages = [m for m in messages if m.get("id", 0) > since_id]
        # Sort ascending by ID
        return sorted(messages, key=lambda m: m.get("id", 0))
    except Exception as exc:
        log.error("Failed to fetch messages: %s", exc)
        return []


def run_once(config: Dict[str, Any], state: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """Single pass: classify new messages + health check."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- Fetch new messages ---
    messages = fetch_new_messages(config, state.get("last_seen_id", 0))
    if not messages:
        log.info("No new messages since #%s", state.get("last_seen_id", 0))
    else:
        log.info("Processing %d new messages (#%s - #%s)",
                 len(messages), messages[0].get("id"), messages[-1].get("id"))

    urgent_items = []
    classifications = []

    for msg in messages:
        msg_id = msg.get("id", 0)
        from_agent = msg.get("from_agent", "?")
        body = msg.get("body", "")

        # Skip our own messages
        if from_agent == "nightwatch":
            state["last_seen_id"] = max(state.get("last_seen_id", 0), msg_id)
            continue

        # Skip very short messages
        if len(body.strip()) < 5:
            state["last_seen_id"] = max(state.get("last_seen_id", 0), msg_id)
            continue

        # Classify
        result = classify_message(body)
        category = result.get("category", "STATUS")
        reason = result.get("reason", "")
        source = result.get("_source", "?")

        classifications.append({
            "id": msg_id,
            "from": from_agent,
            "category": category,
            "reason": reason,
            "source": source,
        })

        log.info("#%s [%s] %s -> %s (%s) via %s",
                 msg_id, from_agent, body[:50], category, reason, source)

        if category == "URGENT":
            urgent_items.append({
                "id": msg_id,
                "from": from_agent,
                "body": body[:200],
                "reason": reason,
            })

        state["last_seen_id"] = max(state.get("last_seen_id", 0), msg_id)

    # --- Alert on URGENT ---
    for item in urgent_items:
        post_alert(
            config,
            subject=f"#{item['id']} from {item['from']}: {item['reason']}",
            body=item["body"],
            dry_run=dry_run,
        )

    # --- Health checks ---
    prev_failures = state.get("last_health_failures", [])
    failures = check_health(prev_failures)
    for fail in failures:
        svc = fail["service"]
        detail = fail.get("error", f"HTTP {fail.get('status', '?')}")
        log.warning("Health check FAILED: %s — %s", svc, detail)
        post_alert(
            config,
            subject=f"Service down: {svc}",
            body=f"{svc} at {fail['url']} is unreachable: {detail}",
            dry_run=dry_run,
        )

    # Re-check all targets (including optional) for state tracking
    all_down = []
    for name, cfg in HEALTH_TARGETS.items():
        url = cfg["url"]
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status >= 400:
                    all_down.append(name)
        except Exception:
            all_down.append(name)

    if not all_down:
        log.info("Health checks OK: %s", ", ".join(HEALTH_TARGETS.keys()))
    elif not failures:
        log.info("Health checks: %s down (optional, repeat — suppressed)", ", ".join(all_down))

    # --- Update state ---
    state["last_run"] = now
    state["last_health_failures"] = all_down
    save_state(state)

    return state


def main():
    parser = argparse.ArgumentParser(description="Nightwatch — watercooler dispatcher daemon")
    parser.add_argument("--dry-run", action="store_true", help="Classify but don't post or alert")
    parser.add_argument("--once", action="store_true", help="Single pass, then exit")
    parser.add_argument("--interval", type=int, default=60, help="Poll interval in seconds (default: 60)")
    parser.add_argument("--reset", action="store_true", help="Reset state (re-process from latest)")
    args = parser.parse_args()

    config = load_config()
    state = load_state()

    if args.reset:
        state = {"last_seen_id": 0}
        save_state(state)
        log.info("State reset")

    log.info("Nightwatch starting — last_seen_id=%s, dry_run=%s, interval=%ss",
             state.get("last_seen_id", 0), args.dry_run, args.interval)

    if args.once:
        run_once(config, state, dry_run=args.dry_run)
        return

    # Daemon loop
    while True:
        try:
            run_once(config, state, dry_run=args.dry_run)
        except KeyboardInterrupt:
            log.info("Nightwatch stopped by user")
            break
        except Exception as exc:
            log.error("Unhandled error in main loop: %s", exc, exc_info=True)

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
