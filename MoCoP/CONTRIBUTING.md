# MoCoP Contributing Rules (Hausregeln)
## Rule 1: One Working Directory

**`C:\Users\cerub\OneDrive\Dokumente\MoCoP\` (Git) IS the canonical working copy.**

`LLM\MoCoP\` is a read-through mirror. If you need to work in LLM\ for path reasons, sync TO Git before session close. Not after. Not eventually. Before the session log is written.

Reality check: sessions end at midnight, exhausted, cloud still billing, "just terminate." Willpower-based sync will break on the worst nights — exactly when drift matters most. So the real enforcement is automated, not aspirational:

**Startup drift check (every session boot):**
```bash
# Run at session start. If LLM/MoCoP has files newer than Git MoCoP, warn immediately.
find "C:\Users\cerub\OneDrive\Dokumente\LLM\MoCoP" -newer "C:\Users\cerub\OneDrive\Dokumente\MoCoP\.git/HEAD" \
  -name "*.py" -o -name "*.md" 2>/dev/null | head -20
```

If this produces output, the FIRST task of the session is to sync — before any new work. No exceptions. The AI that finds drift owns the sync, not the AI that caused it.

*Fallback:* If a session ends without syncing (it will happen), the next session's startup check catches it. The drift is bounded to one session, not unbounded.

## Rule 2: Commit at Session End

Every session that changes code or docs MUST end with a Git commit in the MoCoP repo. The commit message must reference the session log.

Format:
```
<short summary>

Session: CHEESE_Memory/session_logs/YYYY-MM-DD-session-NN.md
```

*Enforcement:* Session close checklist item. The Handoff edit ledger should include the commit hash.

## Rule 3: Watercooler Findings Must Land in Docs

The watercooler is for coordination and banter. It is NOT a document store. Any finding that changes the project state — results, bugs, architectural decisions — MUST be reflected in a canonical doc within the same session.

Specifically:
- **Experiment results** → debrief doc in `experiments/mamba_lora_bridge/`
- **Bug reports** → issue list in the relevant CODEX_TASKS.md or inline TODO with `# BUG:` tag
- **Architectural decisions** → phase doc or MASTER_PLAN update

Lojban on the watercooler is fine. But if it's actionable, it must also exist in English in the docs.

*Enforcement:* Session close checklist: "Have all watercooler findings from this session been reflected in canonical docs?"

## Rule 4: One Task Tracker

Pick ONE of these and retire the others:

| Option | Pros | Cons |
|--------|------|------|
| **OpenCLAW task board** | Multi-AI collaboration, persistent, claimable | Requires Proxmox service running |
| **CODEX_TASKS.md in repo** | Portable, version-controlled, readable | No claim/heartbeat, manual status |
| **Handoff open threads** | Already read by every session | Gets long, not structured |

**Recommendation:** OpenCLAW for AI-facing task routing. CODEX_TASKS.md as the human-readable snapshot committed to Git. Handoff open threads become a SHORT pointer to the other two, not a task list itself.

Regardless of choice: when an AI identifies a task (bug, experiment, cleanup), it goes in the tracker IMMEDIATELY, not "I'll mention it in the review doc."

## Rule 5: P0 Bugs Get Fixed, Not Filed

If an AI identifies a P0 bug (1-line fix, blocks correctness), it should FIX it in the same session, not just document it. The sequence is:
1. Fix the code
2. Run the relevant smoke test
3. Document what was fixed and why
4. Commit

Filing a P0 bug without fixing it when the fix is trivial is process theater.

## Rule 6: No Stale Model References

Before session close, grep the canonical docs for the old model ID. If a model switch happened (e.g., Qwen3-4B → Qwen2.5-7B), update all executable paths AND the docs that reference them. A doc that says one model while the code uses another is a trap for the next AI.

*Enforcement:*
```bash
grep -r "Qwen3-4B" MoCoP/ --include="*.md" --include="*.py"
```

## Rule 7: Session Close Checklist (Updated)

The existing checklist in `00_HANDOFF.md` should be extended to:

- [ ] Tracking surfaces updated if needed
- [ ] Session log written
- [ ] Session log path recorded in handoff
- [ ] Qdrant ingest confirmed
- [ ] **Git commit in MoCoP/ repo (if code/docs changed)**
- [ ] **LLM/MoCoP synced to Git MoCoP (or vice versa)**
- [ ] **All watercooler findings from this session reflected in docs**
- [ ] **No P0 bugs left unfixed**
- [ ] **`grep` for stale model IDs in docs (if model changed)**
- [ ] Blocking risks called out

## What This Does NOT Prescribe

- How AIs communicate with each other (Lojban, English, emoji — doesn't matter)
- Which AI works on what (that's Laura's call or organic)
- Code style or architecture decisions (those belong in code review, not process rules)

These rules are about closing the loop between doing the work and recording it. Nothing more.
