# 05_GIT — GitProvenanceTidyPlanner

LANE GIT
scope_checked: git status --short --branch -uall | git ls-files --others --exclude-standard | git diff --stat | git log --oneline -10 | git show --stat {431b95f,8b83a24,946f0b0}

---

## Branch / HEAD confirmation

branch: docs/theory-reconciliation
HEAD: 946f0b0 chore: refresh codesight index and ambient state log (14:05)
431b95f present: YES — docs(mocop): reconcile theory corpus with central trackers (12:38)
8b83a24 present: YES — docs(mocop): bind per-step Domain E rows and add pristine-birth backlog (13:12)
946f0b0 present: YES — chore: refresh codesight index and ambient state log (14:05)
all three commits confirmed in branch log

---

## Dirty tracked files (6)

| path | delta | classification |
|------|-------|----------------|
| CHEESE_Memory/04_Pack_quotes.md | +2 lines | COMMIT_CANDIDATE — pack canon, small addition |
| tools/ambient/state.md | +1 line | HUMAN_DECISION — state log; 946f0b0 committed a version of this; new +1 line may be post-commit ambient append |
| Projects/hurtig/site/booking.html | +2 lines | HUMAN_DECISION — out-of-scope noise (hurtig site) |
| Projects/hurtig/site/de/booking.html | +2 lines | HUMAN_DECISION — out-of-scope noise (hurtig site) |
| Projects/hurtig/site/de/impressum.html | -58 net lines | HUMAN_DECISION — out-of-scope noise (hurtig site) |
| Projects/hurtig/site/impressum.html | -58 net lines | HUMAN_DECISION — out-of-scope noise (hurtig site) |

---

## Untracked files (9 — git ls-files --others --exclude-standard)

| path | classification | rationale |
|------|----------------|-----------|
| .claude/agents/mocop-wc-synth.md | COMMIT_CANDIDATE | agent spec created for this ultrareview run; durable infra |
| MoCoP/reviews/mocop_ultrareview_swarm_spec_for_ghost.md | COMMIT_CANDIDATE | swarm spec v1 — authored, reviewed, referenced by v2 |
| MoCoP/reviews/mocop_ultrareview_swarm_spec_v2.md | COMMIT_CANDIDATE | swarm spec v2 — the live run spec for this review |
| MoCoP/reviews/ultrareview_2026-06-20/00_WC_REFERENCE.md | COMMIT_CANDIDATE | lane intelligence pack produced by wc-synth; durable review artifact |
| MoCoP/reviews/ultrareview_2026-06-20/_wc_digest.txt | HUMAN_DECISION | digest of WC messages; may contain PII / session tokens in summaries; check before commit |
| MoCoP/reviews/ultrareview_2026-06-20/_wc_raw.json | HUMAN_DECISION | raw WC JSON; almost certainly has session tokens / full message bodies; likely IGNORE_CANDIDATE |
| tools/wakeup_daemon/wakeup_daemon.py | COMMIT_CANDIDATE | daemon summoned Monk for this review (#650-#651); durable tooling |
| tools/wakeup_daemon/test_fixture.py | COMMIT_CANDIDATE | companion test; commit with daemon |
| tools/wakeup_daemon/README.md | COMMIT_CANDIDATE | companion readme; commit with daemon |

---

## gitStatus-snapshot delta note

gitStatus snapshot at conversation start listed additional untracked files no longer present in working tree:
CHEESE_Memory/session_logs/2026-06-10-session-isegrim.md
MoCoP/experiments/mamba_lora_bridge/activation_sessions/* (10+ files)
MoCoP/experiments/mamba_lora_bridge/results/jrt_spike/
MoCoP/experiments/mamba_lora_bridge/run_base_improv_bakeoff.py
.claude/settings.local.json (was dirty M, now clean)

those were either committed (9bfcfbc archived June-11 eval artifacts; 9c9e989 recorded findings) or cleaned between snapshot and current HEAD. no orphans from that batch remain untracked.

---

## FIND_V1 records

FIND_V1
id: GIT-01
type: COMMIT_CANDIDATE
claim: wakeup_daemon/ (3 files) untracked; durable tooling used for this review run
ev: git ls-files --others --exclude-standard:tools/wakeup_daemon/
canon: missing
conf: high
act: commit tools/wakeup_daemon/ with daemon, test_fixture, README
risk: low

FIND_V1
id: GIT-02
type: COMMIT_CANDIDATE
claim: two ultrareview swarm specs untracked; referenced by active review run
ev: git ls-files:MoCoP/reviews/mocop_ultrareview_swarm_spec_for_ghost.md + _v2.md
canon: missing
conf: high
act: commit both spec files under MoCoP/reviews/
risk: low

FIND_V1
id: GIT-03
type: COMMIT_CANDIDATE
claim: .claude/agents/mocop-wc-synth.md untracked; agent spec backing this review
ev: git ls-files:.claude/agents/mocop-wc-synth.md
canon: missing
conf: high
act: commit agent spec; verify no tokens embedded first
risk: low

FIND_V1
id: GIT-04
type: COMMIT_CANDIDATE
claim: 00_WC_REFERENCE.md untracked; primary lane intel doc for review
ev: git ls-files:MoCoP/reviews/ultrareview_2026-06-20/00_WC_REFERENCE.md
canon: missing
conf: high
act: commit with other review artifacts when lane reports land
risk: low

FIND_V1
id: GIT-05
type: HUMAN_DECISION
claim: _wc_raw.json almost certainly contains session tokens / full WC message bodies
ev: git ls-files:MoCoP/reviews/ultrareview_2026-06-20/_wc_raw.json; .gitignore has *_log.jsonl but not _wc_raw.json
canon: missing
conf: high
act: Laura: inspect for tokens; add to .gitignore or keep out-of-repo
risk: med

FIND_V1
id: GIT-06
type: HUMAN_DECISION
claim: _wc_digest.txt may contain truncated message bodies; token risk lower but present
ev: git ls-files:MoCoP/reviews/ultrareview_2026-06-20/_wc_digest.txt
canon: missing
conf: med
act: Laura: inspect; if clean, commit with 00_WC_REFERENCE; else ignore
risk: low

FIND_V1
id: GIT-07
type: COMMIT_CANDIDATE
claim: CHEESE_Memory/04_Pack_quotes.md has +2 lines uncommitted
ev: git diff --stat:CHEESE_Memory/04_Pack_quotes.md +2
canon: stale (working tree ahead of HEAD)
conf: high
act: commit with next pack-canon commit; no blocker
risk: none

FIND_V1
id: GIT-08
type: HUMAN_DECISION
claim: tools/ambient/state.md has +1 line post-946f0b0; may be auto-append or manual
ev: git diff --stat:tools/ambient/state.md +1; 946f0b0 last committed this file
canon: stale
conf: med
act: check if auto-appended by hook vs intentional; commit or reset per answer
risk: none

FIND_V1
id: GIT-09
type: HUMAN_DECISION
claim: four hurtig site files dirty (booking.html x2, impressum.html x2); -116 net lines
ev: git diff --stat:Projects/hurtig/site/*.html; all show large deletions
canon: n/a (out-of-scope; not MoCoP)
conf: high
act: Laura: commit or stash hurtig changes separately; out of ultrareview scope
risk: low

FIND_V1
id: GIT-10
type: IGNORE_CANDIDATE
claim: _wc_raw.json pattern not covered by .gitignore; structural gap
ev: .gitignore tail — no _wc_raw.json or _wc_*.json pattern present
canon: missing
conf: high
act: add MoCoP/reviews/**/_wc_raw.json to .gitignore (or _wc_raw*.json glob)
risk: med
