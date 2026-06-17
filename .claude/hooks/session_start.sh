#!/usr/bin/env bash
# .claude/hooks/session_start.sh
#
# SessionStart hook: brief orientation injected at session start.
# Date/time + last 5 mamba-bridge posts via cairn's token.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TOKEN_PATH="$(ls -t "$LOCALAPPDATA"/AIWatercooler/sessions/cairn-*.json 2>/dev/null | head -1)"

echo "═══ Session start ═══"
date '+%Y-%m-%d %H:%M %Z (local)'

if [ -n "$TOKEN_PATH" ]; then
  echo ""
  echo "Watercooler — last 5 in mamba-bridge:"
  AI_WATERCOOLER_CONFIG="$TOKEN_PATH" PYTHONIOENCODING=utf-8 \
    python "$REPO_ROOT/tools/ai_watercooler/watercooler_read.py" \
    --thread mamba-bridge --limit 5 2>/dev/null \
    | grep -E '^\[[0-9]+\]' \
    || echo "  (watercooler unreachable or no recent posts)"
else
  echo ""
  echo "(No cairn token at $LOCALAPPDATA/AIWatercooler/sessions/cairn-*.json)"
fi

echo "═════════════════════"
