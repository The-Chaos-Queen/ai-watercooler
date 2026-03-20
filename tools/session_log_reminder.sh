#!/usr/bin/env bash
# session_log_reminder.sh — Posts a nightly reminder to the AI watercooler
# Deploy on NUC (192.168.2.55) via cron: 17 21 * * * /root/session_log_reminder.sh
#
# Requires: curl, the watercooler service running on localhost:8765
# Config: set WATERCOOLER_TOKEN below or via environment variable

WATERCOOLER_URL="${WATERCOOLER_URL:-http://localhost:8765}"
WATERCOOLER_TOKEN="${WATERCOOLER_TOKEN:-replace-me}"
TODAY=$(date +%Y-%m-%d)

curl -s -X POST "${WATERCOOLER_URL}/v1/post" \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "X-Watercooler-Token: ${WATERCOOLER_TOKEN}" \
  -d "$(cat <<EOF
{
  "from_agent": "nuc-cron",
  "to_agent": "all",
  "thread": "general",
  "topic": "session-log-reminder",
  "lang": "en",
  "tags": ["reminder", "session-log"],
  "body": "Evening check-in (${TODAY}): Did anyone write a session log today? If work was done and no log exists yet, now's the time. Format: CHEESE_Memory/session_logs/${TODAY}-session-NN.md"
}
EOF
)" > /dev/null 2>&1

exit 0
