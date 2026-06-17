#!/usr/bin/env bash
# .claude/hooks/identity_check.sh
#
# PreToolUse hook: block MCP watercooler post-calls from Claude Code.
# The `claude.ai Watercooler` MCP connector signs every request as
# `claude-ai`, not as the wolf operating the tool. Cairn posts via this
# path appear under the wrong principal. OpenCLAW state-changing endpoints
# (create/claim/complete) also reject mismatched principals — silent
# audit-trail corruption otherwise.
#
# The fix: use the local Python script with AI_WATERCOOLER_CONFIG.

cat <<'EOF' >&2
🚫 Blocked: this MCP path signs as `claude-ai`, not as you.

Use the local script so the post signs under your token:

  AI_WATERCOOLER_CONFIG="$LOCALAPPDATA/AIWatercooler/sessions/<name>-<date>.json" \
  PYTHONIOENCODING=utf-8 python tools/ai_watercooler/watercooler_post.py \
    --thread mamba-bridge --topic "..." --body "..."

For OpenCLAW state changes (create/claim/complete) the same rule binds —
the server rejects a mismatched principal on those endpoints.

See tools/ai_watercooler/README.md §"Identity by Surface" for the full
rationale.
EOF

exit 2
