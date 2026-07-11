#!/usr/bin/env bash
# Load the ML-WS writer credential file only for the command explicitly passed.
# The credential file is user-local, mode 0600, and intentionally not tracked.
set -euo pipefail

if [[ "$#" -eq 0 ]]; then
    echo "usage: $0 <command> [args...]" >&2
    exit 2
fi

ENV_FILE="${MOCOP_QDRANT_WRITER_ENV:-$HOME/.config/mocop/qdrant-writer.env}"
if [[ ! -r "$ENV_FILE" ]]; then
    echo "Qdrant writer environment is missing or unreadable: $ENV_FILE" >&2
    exit 2
fi

MODE="$(stat -c '%a' "$ENV_FILE")"
if (( (8#$MODE & 8#077) != 0 )); then
    echo "Refusing group/world-readable Qdrant writer environment (mode=$MODE): $ENV_FILE" >&2
    exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${QDRANT_URL:?QDRANT_URL is required in $ENV_FILE}"
: "${QDRANT_CA_CERT:?QDRANT_CA_CERT is required in $ENV_FILE}"
: "${QDRANT_API_KEY:?QDRANT_API_KEY is required in $ENV_FILE}"

exec "$@"
