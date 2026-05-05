# Gate Policy Patch Plan - 2026-04-03

**Purpose:** choose one conservative live gate candidate to A/B against the current `chat_server.py` rule set after the first offline replay pass.  
**Status:** plan only. No live behavior change yet.

---

## Why This Exists

Track B already produced the first honest replay result:

- the replay harness works
- the naive variants are informative
- none of the naive variants should be pasted directly into production

So this note does one narrower job:

pick the **single best next patch candidate** for the live gate, without mixing that decision up with source-model swaps, dual-key retrieval, or Step 6 work.

---

## Current Live Behavior Snapshot

As of today, the live routing logic in [chat_server.py](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/chat_server.py) is:

- `CONSOLIDATE` if `salience_hit and surprise_hit`
- `ATTEND` if `salience_hit and not surprise_hit`
- `NOTE` if `surprise_hit and not salience_hit`
- `DISMISS` otherwise

Current write routing in `evaluate_dual_gate()` is:

- `writes_mamba = decision in {"CONSOLIDATE", "ATTEND"}`
- `writes_qdrant = decision in {"CONSOLIDATE", "NOTE"} or qdrant_override`
- `open_tension = bool(tension_hit)`

Current sleep-tag behavior in `store_qdrant_gate_event()` and downstream logging is already broader than Qdrant routing:

- any `CONSOLIDATE`, `NOTE`, or `ATTEND` row is sleep-tagged
- any `open_tension` row is also sleep-tagged, even if its decision stayed `DISMISS`

That last point matters a lot. It means the system already has a real "tension-only survives to sleep" branch, and we must not accidentally break it.

---

## Evidence We Have Right Now

### 1. Offline replay on the first corpus slice

Replay artifact:

- [gate_policy_replay_2026-04-03.json](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/gate_policy_replay_2026-04-03.json)

Input slice:

- 16 total events
- original decisions: `DISMISS=9`, `NOTE=3`, `ATTEND=4`
- original writes: `mamba=4`, `qdrant=3`, `open_tension=9`

Naive alternatives:

- `strict_write`: leaves decisions unchanged but kills Qdrant entirely on this slice
- `tension_aware`: explodes to `ATTEND=13`, clearly too aggressive
- `latent_supported`: collapses to `ATTEND=1`, clearly too strict on this slice

### 2. Open-tension edge case already proved real

Evidence:

- [steve_open_tension_sleep_cycle_20260326.md](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/run_reincarnation/steve_open_tension_sleep_cycle_20260326.md)

Important fact:

- a row with `decision=DISMISS`, `salience_hit=false`, `surprise_hit=false`, `tension_hit=true`, `open_tension=true`, and `qdrant=false` survived into sleep and reconciled as `keep`

So:

- the pure `open_tension` path is not hypothetical
- it is already carrying useful unresolved friction
- any patch that erases or swamps this path is a regression

### 3. Design intent from the original gate note

Reference:

- [saliency_gate_design.md](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/theory/saliency_gate_design.md)

Relevant intent:

- tension should mark `status=OPEN`
- open tension should survive to sleep for re-evaluation
- tension was never meant to turn every unresolved turn into a full write

That means raw `tension_aware` is not just empirically noisy; it is also too blunt for the original architecture intent.

---

## Recommendation

Use a **single conservative live candidate**:

`supported_tension_attend_v0`

This is not "make tension important."
It is:

"promote only the tension-hit dismisses that were already close to salience."

---

## Proposed Rule

Keep the current quadrant rule as the baseline.

Then add one narrow promotion path:

```python
baseline_decision = decision

salience_support_ratio = (
    salience_score / salience_threshold
    if salience_threshold not in {None, 0.0}
    else None
)

supported_tension_attend = bool(
    baseline_decision == "DISMISS"
    and tension_hit
    and salience_support_ratio is not None
    and salience_support_ratio >= 0.55
)

if supported_tension_attend:
    decision = "ATTEND"
```

### Important limits

- `tension_hit` alone does **not** trigger promotion
- promoted rows become `ATTEND`, not `NOTE` or `CONSOLIDATE`
- promoted rows write to **Mamba only**
- Qdrant routing stays unchanged except for the existing safety override
- `open_tension = bool(tension_hit)` stays exactly as it is

This is intentionally modest.

### Why `0.55` and not the earlier placeholder `0.85`

The first replay sweep on the current slice showed:

- `0.85`: no effect
- `0.70`: no effect
- `0.55`: promotes exactly one extra `DISMISS -> ATTEND`
- `0.50`: promotes two
- `0.40`: already looks too loose

So `0.55` is the first ratio that changes anything while still staying conservative on this small corpus slice.

---

## Why This Candidate

It is the best first live patch because it does four useful things at once:

1. It uses signals the live server already has.
2. It does not require adding a new rolling coherence history yet.
3. It catches a narrow class of likely under-kept turns: unresolved friction that was already near the salience line.
4. It leaves the pure `open_tension` sleep branch intact for everything else.

In other words:

- less blunt than `tension_aware`
- more permissive than `latent_supported`
- much easier to patch safely than a coherence-gated online rule

---

## What We Are Explicitly Not Doing Yet

### Not adopting raw `tension_aware`

Reason:

- it promoted `13/16` rows to `ATTEND`
- that is flood behavior, not selective memory

### Not adopting raw `latent_supported`

Reason:

- it reduced the slice to `ATTEND=1`
- the current coherence-only support rule is too harsh on this corpus slice

### Not changing Qdrant policy in v0

Reason:

- the replay already shows Qdrant is easy to over-prune
- the live code already has a useful division of labor:
  - Mamba for dispositional shifts
  - Qdrant for facts / notes / consolidations / safety overrides

### Not using live coherence gating yet

Reason:

- `compute_coherence_proxy()` exists in the server, but there is no current rolling coherence threshold infrastructure for online gating
- coherence is still valuable for replay analysis and later A/B interpretation
- it is not yet the cleanest first live patch surface

---

## Patch Surface

### 1. `evaluate_dual_gate()` in [chat_server.py](C:/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/chat_server.py)

Touch here first.

Current area:

- around `def evaluate_dual_gate(...)`
- decision rule block around the current `CONSOLIDATE / ATTEND / NOTE / DISMISS` logic

Add:

- `baseline_decision`
- `salience_support_ratio`
- `supported_tension_attend`
- `routing` / `decision_rules` metadata that records whether promotion happened

Recommended extra metadata:

```python
"routing": {
    "qdrant_override": qdrant_override,
    "qdrant_reason": ...,
    "attend_reason": "tension_supported" if supported_tension_attend else "decision_rule",
    "baseline_decision": baseline_decision,
}
```

### 2. Leave `store_qdrant_gate_event()` unchanged in v0

Reason:

- the current sleep candidate logic already includes `ATTEND` and `open_tension`
- if the decision upgrades from `DISMISS` to `ATTEND`, sleep tagging already follows naturally
- Qdrant write policy remains conservative by default

### 3. Leave `sleep_reconcile.py` unchanged in v0

Reason:

- the tension-preservation behavior is already working
- this patch is about live selection, not sleep semantics

---

## Suggested Config Knob

If this becomes code, do not hard-wire the ratio forever.

Start with one flag:

`--dual-gate-tension-salience-support-ratio 0.85`

Optional guard flag if we want easy rollback:

`--dual-gate-supported-tension-enabled`

That gives us a clean A/B path:

- disabled = current behavior
- enabled = conservative promotion path

---

## What Success Looks Like

On the next replay or live A/B slice, we want to see:

- a small increase in `ATTEND`, not an explosion
- no Qdrant write flood
- preserved `open_tension` counts
- better capture of unresolved-but-near-salient relational turns
- no collapse of ordinary dismiss noise filtering

Humanly:

we should catch the turns that feel like "that mattered even if it was not surprising," without suddenly turning the whole conversation into memory slurry.

---

## Failure Signals

Reject or roll back the patch if any of these show up:

- `ATTEND` count jumps toward `tension_aware` territory
- ordinary boilerplate starts writing to Mamba
- `open_tension` rows stop appearing as distinct tension-only sleep candidates
- Qdrant usefulness drops because too much is being implicitly escalated upstream
- manual spot-check says the new `ATTEND` rows feel mostly like noise

---

## Next Step After This Plan

If we want to execute the live A/B cleanly, the order should be:

1. patch `evaluate_dual_gate()` only
2. log the promotion reason explicitly
3. replay the same corpus again with the new rule
4. only then decide whether coherence support deserves a second-phase patch

That keeps the experiment legible.
