---
name: how-full
description: Measure this session's current context usage from its own JSONL (input + cache tokens of the latest API call) and advise whether it's time for capsule/handoff work or safe to start long tasks.
---

# /how-full — how much context window is left?

Read the current session's own transcript JSONL and report context usage. Wolves use this to decide:
start long work, or start writing the capsule/handoff first.

## Run

Execute with Bash (ASCII-only output — Windows consoles choke on fancy glyphs):

```bash
python - <<'EOF'
import json, os, glob, time
from datetime import datetime, timezone
home = os.path.expanduser("~")

# SOURCE 0 (authoritative): harness-pushed numbers cached by statusline.py
# (~/.claude/context_cache/<sid>.json, written on every statusline render).
# Same feed the statusline displays - no JSONL parsing, no races.
sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
cache = os.path.join(home, ".claude", "context_cache", sid + ".json") if sid else ""
if cache and os.path.isfile(cache):
    c = json.load(open(cache, encoding="utf-8"))
    age_s = time.time() - os.path.getmtime(cache)
    used = c.get("used_percentage", 0.0)
    size = c.get("context_window_size", 0)
    print("source       : statusline cache (harness-authoritative, %.0fs old)" % age_s)
    print("model        : %s" % c.get("model", "?"))
    print("window       : %sk" % (size // 1000))
    print("fill level   : %.1f%%" % used)
    if age_s > 600:
        print("NOTE: cache is stale (>10 min) - falling through to JSONL method below.")
    else:
        raise SystemExit(0)

# FALLBACK: parse this session's transcript JSONL.
cwd = os.getcwd()
slug = cwd.replace(":", "-").replace("\\", "-").replace("/", "-")
proj = os.path.join(home, ".claude", "projects", slug)

# Identify THIS session's file exactly. The mtime heuristic is FORBIDDEN as
# primary: in a multi-session house the most recently written JSONL is often
# another session's (this bug made /how-full report a sibling's 763k window
# as the caller's own, 2026-07-17).
sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
p = os.path.join(proj, sid + ".jsonl") if sid else ""
how = "CLAUDE_CODE_SESSION_ID"
if not (sid and os.path.isfile(p)):
    files = sorted(glob.glob(os.path.join(proj, "*.jsonl")), key=os.path.getmtime, reverse=True)
    if not files:
        print("no session JSONL found for", proj); raise SystemExit(1)
    p = files[0]
    how = "mtime fallback"
    print("WARNING: CLAUDE_CODE_SESSION_ID missing or file absent; fell back to")
    print("WARNING: newest-file heuristic. In a multi-session repo this may be")
    print("WARNING: ANOTHER session's window. Treat the number as suspect.")

size = os.path.getsize(p)
age_min = (time.time() - os.path.getmtime(p)) / 60
last = None
with open(p, "rb") as f:
    f.seek(max(0, size - 2_000_000))
    for line in f.read().decode("utf-8", errors="ignore").splitlines():
        if '"usage"' not in line or '"input_tokens"' not in line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("isSidechain"):
            continue  # subagent call: small fresh context, not this window
        msg = obj.get("message") or {}
        u = msg.get("usage") or obj.get("usage")
        if u and "input_tokens" in u and msg.get("model") != "<synthetic>":
            last = (u, msg.get("model", "?"))
if not last:
    print("no usage block found in", os.path.basename(p)); raise SystemExit(1)
u, model = last
ctx = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)
print("session file : %s (%.1f MB, via %s)" % (os.path.basename(p), size / 1e6, how))
print("model        : %s" % model)
print("context now  : %s tokens" % format(ctx, ","))
if ctx > 200_000:
    print("window       : 1M-class (usage exceeds 200k)")
    print("fill level   : %.1f%% of 1M" % (ctx / 1_000_000 * 100))
else:
    print("fill level   : %.1f%% of 200k  (or %.1f%% if this is a 1M window)"
          % (ctx / 200_000 * 100, ctx / 1_000_000 * 100))
if age_min > 15:
    print("NOTE: file last modified %.0f min ago; if you have been active more" % age_min)
    print("NOTE: recently than that, this may be a stale/forked file (ccdiag).")
EOF
```

## Interpret and advise

Report the numbers, then ONE line of advice by fill level (of the applicable window):

- **< 50%** — open road. Long reviews, big builds, deep reading: all fine.
- **50–75%** — fine, but plan: finish what you start; prefer subagents for token-heavy exploration.
- **75–85%** — housekeeping window: update capsule/handoff/session log NOW while judgment is cheap;
  do not start work you cannot finish in ~50k tokens.
- **> 85%** — capsule first, everything else second. Bank state durably (files, board posts, commits),
  keep replies lean, expect compaction and write for your heir.

Caveats to state honestly: the measurement is the LAST API call's usage — it lags by one turn. If the
script printed the mtime-fallback WARNING, say so explicitly and treat the number as a guess, not a
measurement (the fallback can pick a sibling session's file — the exact bug that misled Gidim on
2026-07-17). A context drop between runs usually means a compaction happened, not a broken instrument.
