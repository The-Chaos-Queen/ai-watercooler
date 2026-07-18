#!/usr/bin/env bash
set -uo pipefail

BASE_URL="${AI_WATERCOOLER_BASE_URL:-http://192.168.2.55:8765}"
TOKEN_FILE="${OPENCLAW_TOKEN_FILE:-$HOME/.openclaw_token}"
CONFIG_FILE="${AI_WATERCOOLER_CONFIG:-$HOME/.config/ai-watercooler/config.json}"
STATE_DIR="${MORNING_BRIEF_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/morning_brief}"
LAST_ID_FILE="${STATE_DIR}/last_watercooler_id"
EMAIL_TO="${MORNING_BRIEF_EMAIL_TO:-lauraweishaeupl@gmail.com}"
OUTPUT_FILE="${MORNING_BRIEF_FALLBACK_FILE:-/tmp/morning_brief.txt}"
PROJECT_FILTER="${MORNING_BRIEF_PROJECT:-MoCoP}"
HANDOFF_FILE_OVERRIDE="${MORNING_BRIEF_HANDOFF_FILE:-}"
HANDOFF_RCLONE_PATH="${MORNING_BRIEF_HANDOFF_RCLONE:-}"
HANDOFF_REMOTE_MAX_LINES="${MORNING_BRIEF_HANDOFF_LINES:-10}"

mkdir -p "$STATE_DIR"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

read_token() {
    if [[ -n "${AI_WATERCOOLER_TOKEN:-}" ]]; then
        printf '%s' "$AI_WATERCOOLER_TOKEN"
        return 0
    fi
    if [[ -f "$CONFIG_FILE" ]]; then
        python3 - "$CONFIG_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
except Exception:
    raise SystemExit(1)
print((data.get("token") or "").strip())
PY
        return 0
    fi
    if [[ -f "$TOKEN_FILE" ]]; then
        tr -d '\r\n[:space:]' < "$TOKEN_FILE"
        return 0
    fi
    return 1
}

api_get() {
    local path="$1"
    curl -fsS --max-time 20 \
        -H "X-Watercooler-Token: ${TOKEN}" \
        "${BASE_URL%/}${path}"
}

python_json() {
    local json_text="$1"
    local expr="$2"
    python3 - "$json_text" "$expr" <<'PY'
import json
import sys

data = json.loads(sys.argv[1])
expr = sys.argv[2]
namespace = {"data": data}
safe_builtins = {"len": len, "max": max, "min": min, "sum": sum, "sorted": sorted}
value = eval(expr, {"__builtins__": safe_builtins}, namespace)
if value is None:
    raise SystemExit(1)
if isinstance(value, bool):
    print("true" if value else "false")
elif isinstance(value, (dict, list)):
    print(json.dumps(value, ensure_ascii=False))
else:
    print(value)
PY
}

find_handoff_file() {
    local candidates=()
    if [[ -n "$HANDOFF_FILE_OVERRIDE" ]]; then
        candidates+=("$HANDOFF_FILE_OVERRIDE")
    fi
    candidates+=(
        "/root/llm/CHEESE_Memory/00_HANDOFF.md"
        "/home/laura/llm/CHEESE_Memory/00_HANDOFF.md"
        "/mnt/llm/CHEESE_Memory/00_HANDOFF.md"
        "/opt/llm/CHEESE_Memory/00_HANDOFF.md"
    )
    local path
    for path in "${candidates[@]}"; do
        if [[ -f "$path" ]]; then
            printf '%s' "$path"
            return 0
        fi
    done
    return 1
}

read_handoff_block() {
    local source=""
    if source="$(find_handoff_file)"; then
        sed -n "1,${HANDOFF_REMOTE_MAX_LINES}p" "$source"
        return 0
    fi
    if [[ -n "$HANDOFF_RCLONE_PATH" ]] && command -v rclone >/dev/null 2>&1; then
        rclone cat "$HANDOFF_RCLONE_PATH" 2>/dev/null | sed -n "1,${HANDOFF_REMOTE_MAX_LINES}p"
        return 0
    fi
    return 1
}

collapse_lines() {
    local text="$1"
    python3 - "$text" <<'PY'
import sys
text = sys.argv[1]
parts = [line.strip() for line in text.splitlines() if line.strip()]
if not parts:
    print("(handoff unavailable)")
else:
    merged = " | ".join(parts)
    print(merged[:320])
PY
}

send_email() {
    local subject="$1"
    local body="$2"
    if [[ "${MORNING_BRIEF_DISABLE_EMAIL:-0}" == "1" ]]; then
        return 1
    fi
    if command -v msmtp >/dev/null 2>&1; then
        {
            printf 'Subject: %s\n' "$subject"
            printf 'To: %s\n' "$EMAIL_TO"
            printf 'Content-Type: text/plain; charset=utf-8\n'
            printf '\n%s\n' "$body"
        } | msmtp -t
        return $?
    fi
    if command -v sendmail >/dev/null 2>&1; then
        {
            printf 'Subject: %s\n' "$subject"
            printf 'To: %s\n' "$EMAIL_TO"
            printf 'Content-Type: text/plain; charset=utf-8\n'
            printf '\n%s\n' "$body"
        } | sendmail -t
        return $?
    fi
    if command -v mail >/dev/null 2>&1; then
        printf '%s\n' "$body" | mail -s "$subject" "$EMAIL_TO"
        return $?
    fi
    return 1
}

# ── Bug 1 fix: bootstrap last ID from DB max if state file holds a stale count
# Read stored last ID
TOKEN="$(read_token 2>/dev/null || true)"
LAST_ID=0
if [[ -f "$LAST_ID_FILE" ]]; then
    LAST_ID="$(tr -d '\r\n[:space:]' < "$LAST_ID_FILE")"
fi

# If the stored LAST_ID looks like it might be a message count rather than a
# real message ID (i.e. a query with since_id=LAST_ID still returns LAST_ID
# messages), bootstrap by querying the current max ID from the API so the
# next run only reports genuinely new messages.
if [[ -n "$TOKEN" && "$LAST_ID" =~ ^[0-9]+$ ]]; then
    # Ask for a single message with no since_id filter to get the true max ID
    BOOTSTRAP_JSON="$(api_get "/v1/messages?limit=1" 2>/dev/null || true)"
    if [[ -n "$BOOTSTRAP_JSON" ]]; then
        BOOTSTRAP_MAX="$(python_json "$BOOTSTRAP_JSON" \
            'max([msg.get("id", 0) for msg in data.get("messages", [])], default=0)' \
            2>/dev/null || echo "0")"
        # If the true max ID is larger than LAST_ID, the state file held a stale
        # count — reset it to the current max so we start tracking from now.
        if [[ "$BOOTSTRAP_MAX" =~ ^[0-9]+$ && "$BOOTSTRAP_MAX" -gt "$LAST_ID" ]]; then
            log "bootstrapping last_id from ${LAST_ID} → ${BOOTSTRAP_MAX} (stale count detected)"
            LAST_ID="$BOOTSTRAP_MAX"
            printf '%s\n' "$LAST_ID" > "$LAST_ID_FILE"
        fi
    fi
fi

WATERCOOLER_UNREAD="unavailable"
LATEST_MESSAGE_ID="$LAST_ID"
OPENCLAW_COUNTS="unavailable"
# Bug 2 fix: handoff lives on Laura's Windows machine, not on the NUC
HANDOFF_SUMMARY="(read locally on Laura's machine: C:\\Users\\cerub\\OneDrive\\Dokumente\\LLM\\CHEESE_Memory\\00_HANDOFF.md)"

if [[ -n "$TOKEN" ]]; then
    MESSAGES_JSON="$(api_get "/v1/messages?since_id=${LAST_ID}&limit=200" 2>/dev/null || true)"
    if [[ -n "$MESSAGES_JSON" ]]; then
        WATERCOOLER_UNREAD="$(python_json "$MESSAGES_JSON" 'data.get("count", 0)' 2>/dev/null || echo "unavailable")"
        LATEST_MESSAGE_ID="$(python_json "$MESSAGES_JSON" 'max([msg.get("id", 0) for msg in data.get("messages", [])], default=0)' 2>/dev/null || echo "$LAST_ID")"
        if [[ "$LATEST_MESSAGE_ID" == "0" ]]; then
            LATEST_MESSAGE_ID="$LAST_ID"
        fi
    fi

    BOARD_JSON="$(api_get "/v1/board?project=${PROJECT_FILTER}" 2>/dev/null || true)"
    if [[ -n "$BOARD_JSON" ]]; then
        OPENCLAW_COUNTS="$(python3 - "$BOARD_JSON" <<'PY'
import json
import sys

data = json.loads(sys.argv[1])
counts = data.get("counts", {})
print(
    "queued={0} claimed={1} blocked={2} done={3}".format(
        counts.get("queued", 0),
        counts.get("claimed", 0),
        counts.get("blocked", 0),
        counts.get("done", 0),
    )
)
PY
        )"
    fi
fi

# Try to find handoff on local paths or rclone; if not available use the
# graceful note set above (Bug 2 fix).
HANDOFF_BLOCK="$(read_handoff_block 2>/dev/null || true)"
if [[ -n "$HANDOFF_BLOCK" ]]; then
    HANDOFF_SUMMARY="$(collapse_lines "$HANDOFF_BLOCK")"
fi

SUMMARY=$(cat <<EOF
Morning Brief $(date '+%Y-%m-%d %H:%M')
Watercooler unread: ${WATERCOOLER_UNREAD}
Taskboard ${PROJECT_FILTER}: ${OPENCLAW_COUNTS}
Handoff top 10: ${HANDOFF_SUMMARY}
Fallback file: ${OUTPUT_FILE}
EOF
)

# Bug 1 fix: persist the latest message ID BEFORE attempting email, so the
# watermark is always updated even when email delivery fails.
if [[ "$LATEST_MESSAGE_ID" =~ ^[0-9]+$ && "$LATEST_MESSAGE_ID" -gt "${LAST_ID:-0}" ]]; then
    printf '%s\n' "$LATEST_MESSAGE_ID" > "$LAST_ID_FILE"
fi

SUBJECT="Morning Brief $(date '+%Y-%m-%d')"
if send_email "$SUBJECT" "$SUMMARY" >/dev/null 2>&1; then
    log "morning brief emailed to ${EMAIL_TO}"
    exit 0
fi

printf '%s\n' "$SUMMARY" > "$OUTPUT_FILE"
log "email failed; wrote fallback brief to ${OUTPUT_FILE}"
exit 0
