#!/usr/bin/env bash
set -euo pipefail

MAX_DURATION="${SAFE_RENT_MAX_DURATION:-2h}"
LOG_FILE="${SAFE_RENT_LOG:-$HOME/vast_rentals.log}"
STATE_DIR="${SAFE_RENT_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/safe_rent}"
MIN_CREDIT="10"
VASTAI_BIN="${VASTAI_BIN:-vastai}"

usage() {
    cat <<'EOF'
Usage:
  safe_rent.sh [--max-duration 2h] -- vastai create instance <offer_id> [args...]

Notes:
  - Refuses to run if Vast.ai credit is below $10.
  - Requires compute capability >= 7.0.
  - Starts a background watchdog that destroys the instance after max duration.
  - Logs rentals to ~/vast_rentals.log by default.
EOF
}

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

die() {
    log "ERROR: $*"
    exit 1
}

duration_to_seconds() {
    python3 - "$1" <<'PY'
import re
import sys

text = sys.argv[1].strip().lower()
match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([smhd]?)", text)
if not match:
    raise SystemExit(1)
value = float(match.group(1))
unit = match.group(2) or "h"
scale = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
print(int(value * scale))
PY
}

extract_credit() {
    local text="$1"
    python3 - "$text" <<'PY'
import json
import re
import sys

text = sys.argv[1].strip()
if not text:
    raise SystemExit(1)

try:
    data = json.loads(text)
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict):
        for key in ("credit", "balance", "credits", "credit_balance"):
            if key in data:
                print(float(data[key]))
                raise SystemExit(0)
except Exception:
    pass

match = re.search(r"(?i)\b(?:credit|balance|credits)\b[^0-9-]*([0-9]+(?:\.[0-9]+)?)", text)
if not match:
    raise SystemExit(1)
print(match.group(1))
PY
}

extract_instance_id() {
    local text="$1"
    python3 - "$text" <<'PY'
import json
import re
import sys

text = sys.argv[1].strip()
if not text:
    raise SystemExit(1)

try:
    data = json.loads(text)
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict):
        for key in ("new_contract", "instance_id", "id"):
            if key in data and str(data[key]).strip():
                print(str(data[key]).strip())
                raise SystemExit(0)
except Exception:
    pass

patterns = [
    r"(?i)\bnew_contract\b[^0-9]*([0-9]+)",
    r"(?i)\binstance[_ ]id\b[^0-9]*([0-9]+)",
    r"\b([0-9]{4,})\b",
]
for pattern in patterns:
    match = re.search(pattern, text)
    if match:
        print(match.group(1))
        raise SystemExit(0)

raise SystemExit(1)
PY
}

extract_instance_fields() {
    local text="$1"
    python3 - "$text" <<'PY'
import json
import re
import sys

text = sys.argv[1].strip()
gpu_type = ""
cost = ""

try:
    data = json.loads(text)
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict):
        for key in ("gpu_name", "gpu_type", "gpu_model", "gpu_display_name"):
            value = data.get(key)
            if value:
                gpu_type = str(value)
                break
        for key in ("dph_total", "cost_per_hour", "dph"):
            value = data.get(key)
            if value not in (None, ""):
                cost = str(value)
                break
except Exception:
    pass

if not gpu_type:
    match = re.search(r"(?i)\b(?:gpu(?:_type|_name)?|model)\b[^A-Za-z0-9]*([A-Za-z0-9 ._-]+)", text)
    if match:
        gpu_type = match.group(1).strip()
if not cost:
    match = re.search(r"(?i)\b(?:dph_total|cost_per_hour|dph)\b[^0-9]*([0-9]+(?:\.[0-9]+)?)", text)
    if match:
        cost = match.group(1)

print(gpu_type)
print(cost)
PY
}

compute_capability_for_gpu() {
    local gpu="${1^^}"
    case "$gpu" in
        *P40*|*P100*|*K80*|*M60*)
            printf '6.1'
            ;;
        *V100*)
            printf '7.0'
            ;;
        *T4*|*RTX\ 20*|*2080*|*TITAN\ RTX*)
            printf '7.5'
            ;;
        *A100*|*A30*|*A800*)
            printf '8.0'
            ;;
        *A10*|*A40*|*RTX\ 30*|*3090*|*3080*)
            printf '8.6'
            ;;
        *L4*|*L40*|*RTX\ 40*|*4090*|*4080*)
            printf '8.9'
            ;;
        *H100*|*H200*)
            printf '9.0'
            ;;
        *)
            return 1
            ;;
    esac
}

compare_capability() {
    python3 - "$1" "$2" <<'PY'
import sys
print("ok" if float(sys.argv[1]) >= float(sys.argv[2]) else "no")
PY
}

mkdir -p "$STATE_DIR"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --max-duration)
            [[ $# -ge 2 ]] || die "--max-duration requires a value"
            MAX_DURATION="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            break
            ;;
    esac
done

[[ $# -gt 0 ]] || {
    usage
    exit 1
}

command -v "$VASTAI_BIN" >/dev/null 2>&1 || die "vastai CLI not found in PATH"

MAX_SECONDS="$(duration_to_seconds "$MAX_DURATION")" || die "invalid --max-duration: $MAX_DURATION"

USER_OUTPUT="$("$VASTAI_BIN" show user --raw 2>/dev/null || true)"
if [[ -z "$USER_OUTPUT" ]]; then
    USER_OUTPUT="$("$VASTAI_BIN" show user 2>/dev/null || true)"
fi
[[ -n "$USER_OUTPUT" ]] || die "unable to query vastai account credit"
CREDIT="$(extract_credit "$USER_OUTPUT")" || die "unable to parse vastai credit"

if [[ "$(compare_capability "$CREDIT" "$MIN_CREDIT")" != "ok" ]]; then
    die "credit ${CREDIT} is below ${MIN_CREDIT}; refusing to rent"
fi

log "credit check passed: credit=${CREDIT}"
log "running: $VASTAI_BIN $*"

COMMAND_OUTPUT="$("$VASTAI_BIN" "$@" 2>&1)" || {
    printf '%s\n' "$COMMAND_OUTPUT"
    die "vastai command failed"
}
printf '%s\n' "$COMMAND_OUTPUT"

INSTANCE_ID="$(extract_instance_id "$COMMAND_OUTPUT")" || die "unable to parse instance id from vastai output"
INSTANCE_OUTPUT="$("$VASTAI_BIN" show instance "$INSTANCE_ID" --raw 2>/dev/null || true)"
if [[ -z "$INSTANCE_OUTPUT" ]]; then
    INSTANCE_OUTPUT="$("$VASTAI_BIN" show instance "$INSTANCE_ID" 2>/dev/null || true)"
fi
[[ -n "$INSTANCE_OUTPUT" ]] || die "unable to inspect instance ${INSTANCE_ID}"

mapfile -t INSTANCE_FIELDS < <(extract_instance_fields "$INSTANCE_OUTPUT")
GPU_TYPE="${INSTANCE_FIELDS[0]:-unknown}"
COST_PER_HOUR="${INSTANCE_FIELDS[1]:-unknown}"
CAPABILITY="$(compute_capability_for_gpu "$GPU_TYPE")" || {
    "$VASTAI_BIN" destroy instance "$INSTANCE_ID" >/dev/null 2>&1 || true
    die "unknown GPU type '${GPU_TYPE}', destroyed instance ${INSTANCE_ID}"
}

if [[ "$(compare_capability "$CAPABILITY" "7.0")" != "ok" ]]; then
    "$VASTAI_BIN" destroy instance "$INSTANCE_ID" >/dev/null 2>&1 || true
    die "GPU '${GPU_TYPE}' has compute capability ${CAPABILITY} < 7.0; destroyed instance ${INSTANCE_ID}"
fi

if [[ ! -f "$LOG_FILE" ]]; then
    printf 'timestamp,cost,duration,instance_id,gpu_type\n' > "$LOG_FILE"
fi
printf '%s,%s,%s,%s,%s\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    "$COST_PER_HOUR" \
    "$MAX_DURATION" \
    "$INSTANCE_ID" \
    "$GPU_TYPE" >> "$LOG_FILE"

WATCHDOG_LOG="${STATE_DIR}/watchdog-${INSTANCE_ID}.log"
PID_FILE="${STATE_DIR}/watchdog-${INSTANCE_ID}.pid"
(
    sleep "$MAX_SECONDS"
    printf '[%s] watchdog destroying instance %s after %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$INSTANCE_ID" "$MAX_DURATION" >> "$WATCHDOG_LOG"
    "$VASTAI_BIN" destroy instance "$INSTANCE_ID" >> "$WATCHDOG_LOG" 2>&1 || true
) &
WATCHDOG_PID=$!
echo "$WATCHDOG_PID" > "$PID_FILE"

log "instance ${INSTANCE_ID} is active on ${GPU_TYPE} (cc ${CAPABILITY})"
log "watchdog pid ${WATCHDOG_PID} will destroy it after ${MAX_DURATION}"
log "rental logged to ${LOG_FILE}"
