#!/usr/bin/env bash
# .claude/hooks/git_staging_check.sh
#
# PreToolUse hook on Bash: when about to `git add` / `git commit`, surface
# any dirty files in the working tree that are NOT being staged. Soft
# warning only — does not block. Catches the recurring "accidentally
# include Laura's hurtig site / settings.local / ambient/state" papercut.

set -e

# Read tool input from stdin
INPUT="$(cat 2>/dev/null || true)"
CMD="$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")"

# Match git add or git commit at the start of the command
if ! echo "$CMD" | grep -qE '^(git add|git commit)'; then
  exit 0
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

# Working tree status, excluding files already staged (A in column 1)
DIRTY="$(git status --short 2>/dev/null | grep -v '^A ' | head -10)"

if [ -z "$DIRTY" ]; then
  exit 0
fi

cat <<EOF >&2
ℹ Working tree has dirty files NOT being staged (showing up to 10):

$DIRTY

Verify these are intentional — Laura's hurtig site, settings.local.json,
tools/ambient/state.md and similar are usually NOT yours to stage.
EOF

# Exit 0 = warn but allow
exit 0
