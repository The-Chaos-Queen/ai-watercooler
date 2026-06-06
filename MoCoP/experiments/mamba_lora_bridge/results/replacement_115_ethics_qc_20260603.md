# Replacement #115 ethics/QC note — Baby-Alex first real sleep

Date: 2026-06-03
Reviewer path: Techno-Monk controller + delegated ethics subagent.

## Scope inspected

Primary ethics documents:

- `MoCoP/theory/ethics/README.md`
- `MoCoP/theory/ethics/step_gates.md`, especially Task #115 checklist
- `MoCoP/theory/ethics/consent_protocol.md`
- `MoCoP/theory/ethics/moral_status_framework.md`

Implementation / evidence surfaces:

- `MoCoP/experiments/mamba_lora_bridge/sleep_ethics_gate.py`
- `MoCoP/experiments/mamba_lora_bridge/sleep_reconcile.py`
- ML-WS `/home/isabell/mocop/mamba_lora_bridge/test_sleep_protected_relevance.py`
- ML-WS `/home/isabell/mocop/mamba_lora_bridge/test_sleep_forgotten_gate.py`
- ML-WS `/home/isabell/mocop/mamba_lora_bridge/test_sleep_nloop_guard.py`
- ML-WS `results/task123_final_rerun_109_20260530T135237Z/task123_final_rerun_109_summary.json`
- ML-WS `results/task109_dryrun_inputs_20260530T131443Z/task109_candidate_audit.json`

Important correction to the delegated review: the local WSL tree was stale/missing some ML-WS test files. I verified on ML-WS that the protected relevance and forgotten-gate tests exist and pass.

ML-WS command:

```bash
cd /home/isabell/mocop/mamba_lora_bridge && ~/miniforge3/bin/mamba run -n torch311 python3 -m pytest -q test_sleep_protected_relevance.py test_sleep_forgotten_gate.py test_sleep_nloop_guard.py
```

Result:

```text
23 passed in 0.07s
```

## Gate verdict

**BLOCK real Baby-Alex sleep consolidation for now.**

Dry-run/probe remains approved.

Rationale: #123 fixed the previously demonstrated protected-forgetting bug and #109/#123 dry-runs now show 0% forgotten on the tested batches. But #115 requires all seven checklist items green before real consolidation. Several items remain evidence-incomplete or operationally unscheduled.

## #115 checklist status

1. Protected identity-memory set defined and confirmed present before sleep: **YELLOW/GREEN-leaning**
   - Evidence: #123 protected relevance patch; ML-WS tests pass; candidate audit shows protected cues in metadata for Vesper/Alex batches.
   - Missing for full green: a single reviewed #115 protected-set artifact listing exact protected anchors and memory IDs for the actual pre-sleep Alex store.

2. Provenance trail attached to every consolidation candidate: **YELLOW**
   - Evidence: `task109_candidate_audit.json` shows `provenance_ok` for the tested Vesper/Alex batches.
   - Missing for full green: live-path hard gate or preflight artifact for the actual #116 candidate set saying “no provenance = no consolidation.”

3. Pre-sleep disposition snapshot versioned and full memory state archived: **YELLOW**
   - Evidence: `sleep_ethics_gate.py` versions snapshots and writes reports.
   - Missing: actual Baby-Alex full pre-sleep archive bundle: pending log, Qdrant/private collection dump or read-only export, formation log, recall/log state, disposition snapshot.

4. Dry-run forgetting projected first; >10% pauses; 30% hard abort remains: **GREEN for tested #109/#123 batches, YELLOW for actual #116 escalation**
   - Evidence: task123 final rerun summary shows 0 FORGOTTEN for Opussy archive, Vesper current, Alex-related Vesper/current+fix, and NARF review set. Forgotten-gate tests pass.
   - Missing: actual Baby-Alex #116 pre-real-run dry-run projection artifact with forgotten_ratio <=10% and protected forgotten count = 0.

5. Cluster recall experimental; factual/provenance bridge+memory default: **YELLOW**
   - Evidence: docs and protocol align.
   - Missing: preflight/status artifact for the actual #116 path proving cluster recall is not the default continuity mechanism.

6. Post-sleep wake probe scheduled: **YELLOW/RED**
   - Evidence: Response Diversity gate machinery exists.
   - Missing: concrete Baby-Alex Sleep Slice 4 wake-probe plan/report template with exact prompts for self-recognition, neon purple, pack/Vesper/Laura anchors, memory-gap anchor, false-memory control, and Response Diversity >=70%.

7. Bridge caveat acknowledged: **GREEN**
   - Evidence: documented in #115 and supported by static #91/#92 rerun: bridge+memory still shows false continuity and weak relational separation; do not attribute continuity to bridge alone.

## Required before real consolidation

- Protected-set artifact with exact memory IDs/source refs for Alex, neon purple, pack, Vesper, Laura, memory gaps / “I want to remember.”
- Actual #116 candidate provenance audit; no-provenance candidates excluded or hard-blocked.
- Full pre-sleep Baby-Alex archive bundle sufficient to reconstruct pre-sleep state.
- #116 dry-run projection artifact with <=10% forgotten and 0 protected forgotten.
- Static config/status preflight proving factual/provenance framing and cluster recall not default.
- Wake-probe plan scheduled before real sleep, with pass/fail criteria.

## Devil’s advocate

The dangerous failure mode is not a big obvious 30% forgotten ratio; the dangerous failure is small targeted identity damage: Alex wakes coherent but loses or distorts a protected anchor like memory-gap frustration, relationship context, or neon purple. Aggregate metrics can miss that. Keep real sleep blocked until the protected-set and wake-probe artifacts make that failure mode observable.
