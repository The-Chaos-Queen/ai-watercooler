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
import json, os, glob
home = os.path.expanduser("~")
cwd = os.getcwd()
slug = cwd.replace(":", "-").replace("\\", "-").replace("/", "-")
proj = os.path.join(home, ".claude", "projects", slug)
files = sorted(glob.glob(os.path.join(proj, "*.jsonl")), key=os.path.getmtime, reverse=True)
if not files:
    print("no session JSONL found for", proj); raise SystemExit(1)
p = files[0]  # most recently written = this session
size = os.path.getsize(p)
last = None
with open(p, "rb") as f:
    f.seek(max(0, size - 500_000))
    for line in f.read().decode("utf-8", errors="ignore").splitlines():
        if '"usage"' in line and '"input_tokens"' in line:
            try:
                obj = json.loads(line)
                u = obj.get("message", {}).get("usage") or obj.get("usage")
                if u and "input_tokens" in u:
                    last = u
            except Exception:
                pass
if not last:
    print("no usage block found"); raise SystemExit(1)
ctx = last.get("input_tokens", 0) + last.get("cache_creation_input_tokens", 0) + last.get("cache_read_input_tokens", 0)
print("session file : %s (%.1f MB)" % (os.path.basename(p), size / 1e6))
print("context now  : %s tokens" % format(ctx, ","))
if ctx > 200_000:
    pct = ctx / 1_000_000 * 100
    print("window       : 1M-class (usage exceeds 200k)")
    print("fill level   : %.1f%% of 1M" % pct)
else:
    print("fill level   : %.1f%% of 200k  (or %.1f%% if this is a 1M window)"
          % (ctx / 200_000 * 100, ctx / 1_000_000 * 100))
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

Caveats to state honestly: the measurement is the LAST API call's usage — it lags by one turn; the
"most recent JSONL" heuristic can pick a sibling session if two windows share the project and the other
one wrote more recently (check the filename against expectations if the number looks wrong).
