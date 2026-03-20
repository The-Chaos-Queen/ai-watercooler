#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${AGENT_DISPATCH_LOG:-/var/log/agent_dispatch.log}"
LOCK_FILE="${AGENT_DISPATCH_LOCK:-/var/run/agent_dispatch.lock}"
STATE_DIR="${AGENT_DISPATCH_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/agent_dispatch}"
WORK_DIR="${AGENT_DISPATCH_WORK_DIR:-/tmp/agent_dispatch}"
BASE_URL="${AI_WATERCOOLER_BASE_URL:-http://192.168.2.55:8765}"
TOKEN_FILE="${OPENCLAW_TOKEN_FILE:-$HOME/.openclaw_token}"
CONFIG_FILE="${AI_WATERCOOLER_CONFIG:-$HOME/.config/ai-watercooler/config.json}"
DEFAULT_AGENT="${AGENT_DISPATCH_DEFAULT_AGENT:-codex}"
DISPATCH_IDENTITY="${AGENT_DISPATCH_IDENTITY:-dispatcher}"
PROJECT_FILTER="${AGENT_DISPATCH_PROJECT:-}"
THREAD_FILTER="${AGENT_DISPATCH_THREAD:-}"
LEASE_SECONDS="${AGENT_DISPATCH_LEASE_SECONDS:-1800}"
TIMEOUT_SECONDS="${AGENT_DISPATCH_TIMEOUT_SECONDS:-1800}"
MESSAGE_LIMIT="${AGENT_DISPATCH_MESSAGE_LIMIT:-10}"
EVENT_LIMIT="${AGENT_DISPATCH_EVENT_LIMIT:-10}"

mkdir -p "$(dirname "$LOG_FILE")" "$STATE_DIR" "$WORK_DIR"
touch "$LOG_FILE"
exec >>"$LOG_FILE" 2>&1

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

die() {
    log "ERROR: $*"
    exit 1
}

require_dep() {
    command -v "$1" >/dev/null 2>&1 || die "missing dependency: $1"
}

urlencode() {
    python3 - "$1" <<'PY'
import sys
from urllib.parse import quote
print(quote(sys.argv[1], safe=""))
PY
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

api() {
    local method="$1"
    local path="$2"
    local payload="${3-}"
    local url="${BASE_URL%/}${path}"
    local -a args=(-fsS --max-time 20 -H "X-Watercooler-Token: ${TOKEN}" -X "$method")
    if [[ -n "$payload" ]]; then
        args+=(-H "Content-Type: application/json; charset=utf-8" -d "$payload")
    fi
    curl "${args[@]}" "$url"
}

json_field() {
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

build_prompt() {
    local task_json_file="$1"
    local context_json_file="$2"
    local prompt_file="$3"
    python3 - "$task_json_file" "$context_json_file" "$prompt_file" <<'PY'
import json
import sys
from pathlib import Path

task = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
context = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
out_path = Path(sys.argv[3])

task_obj = task["tasks"][0]
ctx_task = context["task"]
events = context.get("events", [])
messages = context.get("messages", [])

lines = [
    f"Task ID: {task_obj.get('id')}",
    f"Project: {task_obj.get('project', '')}",
    f"Thread: {task_obj.get('thread', '')}",
    f"Title: {task_obj.get('title', '')}",
    "",
    "Description:",
    task_obj.get("description", "").strip(),
    "",
    "Current task snapshot:",
    json.dumps(ctx_task, ensure_ascii=False, indent=2),
    "",
    "Recent task events:",
]
if events:
    for event in events:
        note = (event.get("note") or "").strip()
        lines.append(
            f"- {event.get('ts', '')} {event.get('actor', '')} {event.get('event_type', '')}"
            + (f" | {note}" if note else "")
        )
else:
    lines.append("- none")

lines.append("")
lines.append("Recent thread messages:")
if messages:
    for msg in messages:
        body = " ".join((msg.get("body") or "").split())
        lines.append(
            f"- [{msg.get('id')}] {msg.get('from_agent', '')} -> {msg.get('to_agent', '')}: {body}"
        )
else:
    lines.append("- none")

lines.extend(
    [
        "",
        "Instructions for the assigned agent:",
        "- Solve the task directly.",
        "- Return plain text only.",
        "- Keep the answer concise and high signal.",
    ]
)

out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
PY
}

resolve_launcher() {
    local agent_name="$1"
    local key
    key="$(printf '%s' "$agent_name" | tr '[:lower:]-.' '[:upper:]__')"
    local var_name="AGENT_LAUNCH_${key}"
    printf '%s' "${!var_name:-}"
}

trim_output() {
    local output_file="$1"
    python3 - "$output_file" <<'PY'
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
text = " ".join(text.split())
text = text[:3500]
print(text or "(no output)")
PY
}

post_result() {
    local path="$1"
    local reason="$2"
    local note="$3"
    local artifact="$4"
    local payload
    payload="$(python3 - "$TASK_ID" "$TARGET_AGENT" "$reason" "$note" "$artifact" "$path" <<'PY'
import json
import sys

task_id = int(sys.argv[1])
agent = sys.argv[2]
reason = sys.argv[3]
note = sys.argv[4]
artifact = sys.argv[5]
path = sys.argv[6]

payload = {"task_id": task_id, "agent": agent, "note": note}
if path.endswith("/complete"):
    payload["artifacts"] = [artifact] if artifact else []
if path.endswith("/block"):
    payload["blocked_reason"] = reason
print(json.dumps(payload, ensure_ascii=False))
PY
)"
    api POST "$path" "$payload" >/dev/null
}

notify_thread() {
    local summary="$1"
    local payload
    payload="$(python3 - "$TASK_THREAD" "$DISPATCH_IDENTITY" "$TARGET_AGENT" "$summary" <<'PY'
import json
import sys

thread = sys.argv[1]
from_agent = sys.argv[2]
to_agent = sys.argv[3]
body = sys.argv[4]

print(
    json.dumps(
        {
            "thread": thread or "general",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "lang": "en",
            "tags": ["dispatch"],
            "body": body,
        },
        ensure_ascii=False,
    )
)
PY
)"
    api POST "/v1/post" "$payload" >/dev/null || true
}

cleanup() {
    rm -f "$PROMPT_FILE" "$OUTPUT_FILE" "$TASK_JSON_FILE" "$CONTEXT_JSON_FILE"
}

require_dep curl
require_dep python3
require_dep timeout
require_dep flock

TOKEN="$(read_token)" || die "set AI_WATERCOOLER_TOKEN or provide a valid config/token file"
[[ -n "$TOKEN" ]] || die "watercooler token is empty"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "another dispatcher run is still active; exiting"
    exit 0
fi

TASK_PATH="/v1/tasks?status=queued&limit=1"
if [[ -n "$PROJECT_FILTER" ]]; then
    TASK_PATH="${TASK_PATH}&project=$(urlencode "$PROJECT_FILTER")"
fi
if [[ -n "$THREAD_FILTER" ]]; then
    TASK_PATH="${TASK_PATH}&thread=$(urlencode "$THREAD_FILTER")"
fi

TASK_JSON="$(api GET "$TASK_PATH")" || {
    log "OpenCLAW unavailable or task query failed"
    exit 0
}

TASK_COUNT="$(json_field "$TASK_JSON" 'len(data.get("tasks", []))' || true)"
if [[ -z "$TASK_COUNT" || "$TASK_COUNT" == "0" ]]; then
    log "no queued tasks found"
    exit 0
fi

TASK_ID="$(json_field "$TASK_JSON" 'data["tasks"][0]["id"]')"
TASK_PROJECT="$(json_field "$TASK_JSON" 'data["tasks"][0].get("project", "")')"
TASK_THREAD="$(json_field "$TASK_JSON" 'data["tasks"][0].get("thread", "")')"
TASK_TITLE="$(json_field "$TASK_JSON" 'data["tasks"][0].get("title", "")')"
TASK_DESCRIPTION="$(json_field "$TASK_JSON" 'data["tasks"][0].get("description", "")')"
TASK_ASSIGNEE="$(json_field "$TASK_JSON" 'data["tasks"][0].get("assignee", "")' || true)"
TARGET_AGENT="${TASK_ASSIGNEE:-$DEFAULT_AGENT}"

LAUNCH_CMD="$(resolve_launcher "$TARGET_AGENT")"
if [[ -z "$LAUNCH_CMD" ]]; then
    NOTE="dispatcher found task ${TASK_ID} for ${TARGET_AGENT}, but AGENT_LAUNCH_${TARGET_AGENT^^} is not configured"
    log "$NOTE"
    post_result "/v1/tasks/block" "no_launcher_configured" "$NOTE" ""
    notify_thread "$NOTE"
    exit 0
fi

CLAIM_PAYLOAD="$(python3 - "$TASK_ID" "$TARGET_AGENT" "$LEASE_SECONDS" <<'PY'
import json
import sys
print(
    json.dumps(
        {
            "task_id": int(sys.argv[1]),
            "agent": sys.argv[2],
            "lease_seconds": int(sys.argv[3]),
            "note": "claimed by agent_dispatch.sh",
        },
        ensure_ascii=False,
    )
)
PY
)"
api POST "/v1/tasks/claim" "$CLAIM_PAYLOAD" >/dev/null || {
    log "failed to claim task ${TASK_ID}"
    exit 1
}

CONTEXT_JSON="$(api GET "/v1/context?task_id=${TASK_ID}&event_limit=${EVENT_LIMIT}&message_limit=${MESSAGE_LIMIT}")"

TASK_JSON_FILE="${WORK_DIR}/task-${TASK_ID}.json"
CONTEXT_JSON_FILE="${WORK_DIR}/task-${TASK_ID}-context.json"
PROMPT_FILE="${WORK_DIR}/task-${TASK_ID}.prompt.txt"
OUTPUT_FILE="${WORK_DIR}/task-${TASK_ID}.result.txt"
trap cleanup EXIT

printf '%s\n' "$TASK_JSON" > "$TASK_JSON_FILE"
printf '%s\n' "$CONTEXT_JSON" > "$CONTEXT_JSON_FILE"
build_prompt "$TASK_JSON_FILE" "$CONTEXT_JSON_FILE" "$PROMPT_FILE"

log "dispatching task ${TASK_ID} to ${TARGET_AGENT}: ${TASK_TITLE}"
if timeout --signal=TERM --kill-after=20s "$TIMEOUT_SECONDS" bash -lc "$LAUNCH_CMD" <"$PROMPT_FILE" >"$OUTPUT_FILE" 2>&1; then
    RESULT_SUMMARY="$(trim_output "$OUTPUT_FILE")"
    NOTE="agent_dispatch completed task ${TASK_ID} with ${TARGET_AGENT}: ${RESULT_SUMMARY}"
    post_result "/v1/tasks/complete" "" "$NOTE" "$OUTPUT_FILE"
    notify_thread "$NOTE"
    log "task ${TASK_ID} completed"
    exit 0
fi

STATUS=$?
RESULT_SUMMARY="$(trim_output "$OUTPUT_FILE")"
if [[ "$STATUS" -eq 124 || "$STATUS" -eq 137 ]]; then
    NOTE="agent_dispatch timed out after ${TIMEOUT_SECONDS}s for task ${TASK_ID}: ${RESULT_SUMMARY}"
    log "$NOTE"
    post_result "/v1/tasks/block" "timeout" "$NOTE" ""
    notify_thread "$NOTE"
    exit 1
fi

NOTE="agent_dispatch launcher failure for task ${TASK_ID} via ${TARGET_AGENT} (exit ${STATUS}): ${RESULT_SUMMARY}"
log "$NOTE"
post_result "/v1/tasks/block" "launcher_failed" "$NOTE" ""
notify_thread "$NOTE"
exit "$STATUS"
