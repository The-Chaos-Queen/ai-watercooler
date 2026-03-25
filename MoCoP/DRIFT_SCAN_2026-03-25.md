# MoCoP Drift Scan — 2026-03-25

**Scope:** `MoCoP/` (excluding `experiments/mamba_lora_bridge/`), `CHEESE_Memory/`
**Scanner:** Anda (Claude Code, Sonnet 4.6)
**Purpose:** Identify stale or dangerous references to superseded architecture decisions.

---

## Summary Counts

| Category | Count |
|----------|-------|
| DANGEROUS IF EXECUTED | 3 |
| NEEDS DOC FIX | 9 |
| HISTORICAL ONLY | 6 |

---

## DANGEROUS IF EXECUTED

These entries describe code patterns or instructions that, if followed literally today, would produce wrong results.

---

### D1 — `MoCoP/theory/Orchestrator Blueprint_ Mamba-to-LoRA Hypernetwork.md` · Module 1 (line ~27)

**Stale content:**
```
Task for AI: Write a PyTorch module that takes the Mamba state tensor and applies
"Mean Pooling" across the layers to compress it into a flat, 1D vector
(e.g., a single 4096-dimension embedding). This becomes the "Context Vector."
```

**Classification:** DANGEROUS IF EXECUTED

**Why:** This directly instructs "mean pooling across layers" as the compressor design. Pinky's 2026-03-20 separation experiment proved that mean-pooling destroys the disposition signal (cosine similarity collapses; only last-token extraction from `output_hidden_states[3][:, -1, :]` produces the 0.036 warm/cold cosine that makes the bridge work). Any AI agent reading this doc to implement a new compressor would build something that replicates the original compressor collapse.

**Suggested fix:** Add a `> **SUPERSEDED (2026-03-20):**` callout block at the top of Module 1 stating: "Mean pooling was the initial design. Phase 1 probes + Pinky's separation analysis (watercooler #154) proved it destroys the disposition signal. The correct approach is last-token extraction: `output_hidden_states[target_layer][:, -1, :]`. See `RESEARCH_LOG.md` lines ~700-704."

---

### D2 — `MoCoP/phases/phase1_results.md` · Implications section (lines 75-77)

**Stale content:**
```
MambaStateCompressor must target Layer 3 specifically. The compressor extracts
mamba_state[:, 3] (shape: (batch, 2560, 16)) and projects it to a context vector.
...
Input flat size is deterministic. At Layer 3, the flattened feature dimension is
d_model * d_state = 2560 * 16 = 40,960.
```

**Classification:** DANGEROUS IF EXECUTED

**Why:** This canonically specifies `cache.ssm_states` geometry (d_model × d_state = 2560 × 16) as the compressor input. But after Pinky's finding, the correct extraction is `output_hidden_states[3][:, -1, :]` which has shape `(batch, 2560)` — a 1D hidden vector, not a 2D SSM state matrix. The flat size is `2560`, not `40,960`. Any developer following this document to configure a new compressor will size the input layer to 40,960 and feed it SSM states — both wrong for the `hidden_last_token` path.

The doc also does not distinguish between the SSM state path (still supported in `cognitive_bridge.py` as `mamba_state_source="ssm"`) and the `hidden_last_token` path. This ambiguity is dangerous.

**Suggested fix:** Add a section "Update 2026-03-20 — Extraction Method Revision" that explains: (a) Phase 1 probes used SSM state (`cache.ssm_states`), which is why the 40,960 figure appears here; (b) Pinky's subsequent separation experiment showed `hidden_states` (last-token, shape `2560`) separates 2.5x better; (c) the canonical bridge path as of 2026-03-20 uses `hidden_last_token` mode with `mamba_d_state=1` (i.e., input_flat_size = 2560). The 40,960 figure is only correct for the deprecated `ssm` mode.

---

### D3 — `MoCoP/experiments/mamba_state_transfer/experiment_04_data_collector.py` · `get_model_state()` (lines 94-109)

**Stale content:**
```python
ssm_states = [s.clone().cpu() for s in cache.ssm_states]
...
return {
    "ssm": ssm_states,
    ...
}
```

**Classification:** DANGEROUS IF EXECUTED

**Why:** This is live, runnable Python code that collects and serializes `cache.ssm_states` as the primary state representation. If anyone runs this script today to generate a training dataset or probe dataset for a new Phase 1-style experiment, all collected states will be SSM states — which Pinky proved separate at cosine ~0.778-0.848 (barely above chance), vs. `hidden_last_token` at 0.036 (strongly separating). The collected data would appear to work (some separation exists in SSM states) but would be ~2.5x weaker than the correct representation, potentially leading to a false negative conclusion about the bridge.

The script has no comment warning about this.

**Suggested fix:** Add a docstring or inline comment to `get_model_state()` stating: "WARNING (2026-03-20): This function collects cache.ssm_states. Pinky's separation experiment (watercooler #154) showed that output_hidden_states (last-token) separates 2.5x better. For bridge training data collection, prefer the `hidden_last_token` path used in `train_cheese_bridge.py`. This file is retained as a Phase 1 artifact."

---

## NEEDS DOC FIX

These entries make claims that are currently stated as present truth but are no longer accurate. No immediate execution risk, but they will mislead a reader trying to understand the current architecture.

---

### N1 — `MoCoP/MASTER_PLAN.md` · Vision section (line 8) and Phase 2 criterion (line 35)

**Stale content:**
> "A trained hypernetwork reads that state and produces LoRA weight matrices that are injected into a frozen Transformer (Qwen)"

> "Criterion: Qwen with dynamic LoRA injection (from Mamba state via hypernetwork) achieves measurably higher fact retention"

**Classification:** NEEDS DOC FIX

**Why:** The current bridge mechanism is **activation bias injection**, not LoRA. LoRA was tried, failed due to over-injection instability, and was replaced by Step 2026-03-17. The Vision section of the master plan still presents LoRA as the primary mechanism. A new reader following MASTER_PLAN.md as their orientation document will have a wrong mental model of what the project currently does.

Additionally, the Phase 2 status column reads "Compressor confirmed as bottleneck via PCA (effective rank 2.53/2048). Next: compressor bypass or repair" — but compressor bypass has now been tested and the compressed path outperformed raw bypass (RESEARCH_PAPER.md §6.5). The status is stale.

**Suggested fix:** Update Vision paragraph to say "activation bias injection (superseding the original LoRA mechanism — see Section 6.2 of RESEARCH_PAPER.md)." Update Phase 2 criterion to reflect activation bias as current mechanism. Update Phase 2 status column to "Activation bias path established; PPL delta −4.04; recall 0/16. Compressor bypass tested and failed. Next: Step 5 substrate change."

**Last updated line:** Still shows 2026-03-16. Should be updated to 2026-03-25 or current.

---

### N2 — `MoCoP/MASTER_PLAN.md` · Infrastructure table (line 52)

**Stale content:**
> "Vast.ai A100 SXM4 80GB | Used for 4 runs (~$11 total, ~$39 remaining credit)"

**Classification:** NEEDS DOC FIX

**Why:** RESEARCH_PAPER.md line 227 states "Total compute cost through Phase 2: ~$15 across all Vast.ai runs." The $11 figure is from an earlier count; total is now ~$15 and remaining credit figure is stale.

**Suggested fix:** Update to "~$15 total; remaining credit unknown."

---

### N3 — `MoCoP/RESEARCH_PAPER.md` · Section 6.1 Architecture (line 125)

**Stale content:**
> "The bridge pipeline extracts Layer 3 hidden state from frozen Mamba-2.8B, compresses it via a learned linear projection from **40,960 dimensions (2560 x 16)** to 2,048"

**Classification:** NEEDS DOC FIX

**Why:** `40,960 = 2560 × 16` is the SSM state geometry (`d_model × d_state`). After Pinky's finding, the canonical bridge path uses `output_hidden_states[3][:, -1, :]` — the last-token hidden state — which has shape `(batch, 2560)`, i.e., **2,560 dimensions**, not 40,960. The RESEARCH_PAPER describes the compressor as if it still consumes SSM states, while the training code (`train_cheese_bridge.py`, `cognitive_bridge.py` with `hidden_last_token` mode) uses the hidden state path with `mamba_d_state=1`.

This is a factual error in the current paper. The numbers are internally inconsistent with the codebase.

**Suggested fix:** Clarify that the 40,960 figure applies to the legacy SSM path (used in Phase 1 probes and `train_bridge.py`), while the current `train_cheese_bridge.py` / `hidden_last_token` path operates on 2,560-dimensional last-token hidden states. Note that `mamba_d_state=1` in `models.py` captures this distinction. Add a brief parenthetical: "(SSM-state path: 40,960 dim = 2560 × 16; current hidden-state path: 2,560 dim = 2560 × 1)."

---

### N4 — `MoCoP/theory/Three_System_Cognitive_Architecture.md` · Section 2.2, 3, and throughout

**Stale content:**
Multiple references to LoRA as the active injection mechanism. For example:
- Line 47: "Phase 2 tests whether that signal can be transferred across architectures via dynamic LoRA injection"
- Lines 89-104: Data flow diagram and text exclusively describe LoRA
- Lines 62, 71, 92, 121: "Frozen Transformer (Qwen, or equivalent) + dynamic LoRA injection" as the Generation System definition

**Classification:** NEEDS DOC FIX

**Why:** The three-system architecture document is listed as foundational theory reading (README.md line 7: "theory/README.md" links to it as "Three organs, one mind"). It presents LoRA injection as the current and correct mechanism. Readers new to the project who follow the recommended reading order will build their mental model around LoRA, which was abandoned. This is especially misleading in the data flow diagram which shows LoRA as the only injection path.

**Suggested fix:** Add a "2026-03-17 Update" note to Section 3 (Data Flow) and the Generation System definition: "LoRA injection was the original design. As of 2026-03-17, activation bias (additive residual-stream injection) replaced LoRA as the primary mechanism after LoRA over-injection instability. The conceptual architecture is unchanged; only the injection surface changes from weight perturbation to activation perturbation. See RESEARCH_PAPER.md §6.2-6.3." The data flow diagram should show "activation bias injection" or "bias/LoRA injection."

---

### N5 — `MoCoP/theory/sleep_architecture.md` · Wake Phase diagram (line 92)

**Stale content:**
```
[Load Mamba state from last sleep] → [Hypernetwork] → [LoRA injection]
```

**Classification:** NEEDS DOC FIX

**Why:** Same LoRA-centric framing in a newer document (2026-03-19). The sleep architecture doc explicitly shows LoRA as the wake-phase injection mechanism. By this date LoRA had already been superseded.

**Suggested fix:** Change `[LoRA injection]` to `[activation bias injection]` in the diagram. Add inline note: "(LoRA was the original mechanism; activation bias replaced it 2026-03-17 — see RESEARCH_PAPER.md §6.3)."

---

### N6 — `MoCoP/phases/phase3_plan.md` · Retrieval Flow (line 83-84)

**Stale content:**
```
4. Feed state through compressor -> hypernetwork -> LoRA injection.
5. Qwen generates with injected LoRA. Behavioral continuity achieved.
```

**Classification:** NEEDS DOC FIX

**Why:** The deployment retrieval flow prescribes LoRA injection as the mechanism. This is the plan that would be executed when Phase 3 transitions to deployment. As written, Phase 3 would implement an architecture that Phase 2 already proved doesn't work.

**Suggested fix:** Update lines 83-84 to: "Feed state through compressor -> hypernetwork -> activation bias injection (or LoRA if re-validated in Phase 3 ablation)." Add a note: "Note: Phase 2 established activation bias as the current stable mechanism. Phase 3 may re-evaluate LoRA with corrected scaling (lora_alpha = lora_rank), but the default deployment path should target activation bias."

---

### N7 — `MoCoP/theory/README.md` · Architecture Layer table (line 36)

**Stale content:**
> `Mamba to LoRA_ The Hypernetwork Injection.md` | "The core bridge: Mamba state → compressor → hypernetwork → LoRA matrices → Transformer. | You want the engineering spec."

**Classification:** NEEDS DOC FIX

**Why:** This document is labelled "The core bridge" and "the engineering spec" in the theory README. But it describes LoRA as the injection mechanism. Anyone sent here to understand the current bridge will read the wrong spec. The doc itself is a pre-experiment theory piece that predates both the failure of LoRA and the switch to activation bias.

**Suggested fix:** Update the table entry description to: "Original bridge concept: Mamba state → compressor → hypernetwork → LoRA matrices → Transformer. LoRA was abandoned (2026-03-17) in favour of activation bias. Read this for historical context; for current engineering spec, see `RESEARCH_PAPER.md` §6.3 and `STEP5_DESIGN_NOTES.md`." Also update the `Mamba-LoRA Hypernetwork Skeleton.md` entry similarly — that skeleton hardcodes `scaling = 2.0`, the exact bug that caused over-injection (alpha=16/rank=8).

---

### N8 — `MoCoP/theory/unified_cognitive_framework.md` · Section on Mamba state representation (lines 556-573)

**Stale content:**
```
IMPORTANT AMBIGUITY (open, flagged by Laughing Opus #64): Two different Mamba
representations exist and MoCoP codepaths use both:
1. Hidden state h — what train_cheese_bridge.py and Pinky's separation analysis use.
   Pinky measured cosine 0.036 on this representation.
2. SSM state s — (cache.ssm_states). This is what cognitive_bridge.py and the original
   train_bridge.py extract. ...
These are different tensors with different geometry. The separation result (0.036) is
proven only for hidden states. Whether SSM states separate similarly is unverified.
```

**Classification:** NEEDS DOC FIX

**Why:** The RESEARCH_LOG.md (line ~698-704) shows that SSM state separation was actually measured: `SSM state (cache.ssm_states): cosine 0.778-0.848` across warm/cold/adversarial — which is barely above random, compared to `hidden_last_token: 0.036`. The ambiguity was resolved. The `unified_cognitive_framework.md` still presents it as an open, unverified question. This document is the top-level architecture reference (README.md: "If you read one thing, read this"). Leaving a resolved question marked as open creates confusion about which path is canonical.

The same doc notes (line 703-704) that the fix is known: "switch cognitive_bridge.py feed_mamba() from cache.ssm_states → output_hidden_states[3][:, -1, :]". The question is not whether to fix it, it is whether the fix has been applied.

**Suggested fix:** Replace the "IMPORTANT AMBIGUITY" block with: "RESOLVED (2026-03-20, watercooler #154): SSM states separate at cosine 0.778-0.848 (barely above chance). Hidden states at last-token separate at cosine 0.036 (strongly separating, 2.5x better). The canonical bridge path is `hidden_last_token` = `output_hidden_states[3][:, -1, :]`. The `ssm` mode remains available in `cognitive_bridge.py` for ablation but is not the production path."

---

### N9 — `MoCoP/experiments/mamba_state_transfer/experiment_02_two_process.py` · Core state transfer (lines 78-117)

**Stale content:**
```python
state_dict = {
    "ssm_states": [s.clone() for s in cache.ssm_states],
    ...
}
...
for i, (ssm, conv) in enumerate(zip(loaded_state_dict["ssm_states"], ...)):
    loaded_cache.ssm_states[i].copy_(ssm)
```

**Classification:** NEEDS DOC FIX

**Why:** This is Phase 1 experimental code (date 2026-02-19) that demonstrates state serialization and transfer using `cache.ssm_states`. It is not intended to be production code, but it lives in a directory that new contributors may treat as reference implementations. Unlike `experiment_04_data_collector.py` (classified DANGEROUS), this experiment tests state injection fidelity (does the injected state produce the same output as the original?), which is a valid use of SSM states. But without a comment explaining that `ssm_states` is not the same as the representation now used in the bridge, a reader will be confused about the relationship between Phase 1 experiments and the current architecture.

**Suggested fix:** Add a module-level docstring note: "This experiment uses cache.ssm_states for state transfer fidelity testing (Phase 1). For bridge training and disposition separation, the current canonical representation is output_hidden_states (last-token). See RESEARCH_LOG.md 2026-03-20 for the separation experiment results."

---

## HISTORICAL ONLY

These entries reference the old architecture or old results, but are clearly dated and presented as past findings. They do not mislead a careful reader about current state.

---

### H1 — `MoCoP/RESEARCH_LOG.md` · 2026-03-20 entry (lines ~695-704)

The research log correctly documents the SSM vs hidden state findings as a dated discovery entry. It explicitly states the fix, labels the old path, and explains the cosine numbers. Presented as historical discovery, not current spec. No fix needed.

---

### H2 — `MoCoP/phases/phase2_diagnostic_ablation_plan.md` · Pilot results (lines 104)

> "bridge 8121.2423"

The 8121 PPL number appears in context as the first pilot run result, within a section headlined as the start of the diagnostic ladder. The document correctly positions it as a baseline failure state, not a current result. No misleading framing.

---

### H3 — `MoCoP/experiments/mamba_lora_bridge/BURST_2_DEBRIEF.md` · PPL comparison (line 50)

> "Pilot 1: PPL 8121. Now: PPL 28.96 at epoch 1"

Clear historical comparison framing. The 8121 is used to show improvement, not as a current claim.

---

### H4 — `MoCoP/archive/RESEARCH_PAPER_old_1stMarch26.md`

The entire archive subdirectory is clearly archival. The old paper describes LoRA as the mechanism, the SSM state as the source, and does not reflect Phase 2 outcomes. As an archive file, no action needed. Dangerous only if mistaken for the current paper.

**Minor recommendation:** The archive directory has no README warning that these are superseded. Adding a single `ARCHIVE_NOTE.md` or a frontmatter warning to each file would reduce risk.

---

### H5 — `CHEESE_Memory/session_logs/2026-03-20-session-02.md` (lines 86-109)

SSM vs hidden_states mentioned as an open question. This was the session *during which* the question was raised, so it is an accurate record of the state of knowledge at that time. Historical only.

---

### H6 — `MoCoP/LAIN_HANDOFF_2026-03-18.md`

References compressor as bottleneck, mentions LoRA failure, uses "ssm" mode in a table. The handoff is dated 2026-03-18 and clearly describes the state of the project as of that date. The LoRA failure table explicitly labels `lora` as "Abandoned." Accurately historical.

---

## Cross-Cutting Observations

### The LoRA-vs-Activation-Bias Drift Pattern

The most pervasive drift is that many theory documents (Three_System, sleep_architecture, phase3_plan, MASTER_PLAN Vision, Mamba-to-LoRA, theory/README) still present LoRA injection as the current or planned mechanism. This is understandable: LoRA was the original design and these documents predate the 2026-03-17 switch. But the theory layer is the orientation layer for new contributors and session-starts. The cumulative effect is that any AI agent or human reading theory/ first will build a LoRA-centric mental model, then have to unlearn it when reading the actual experiment results.

A single "Architecture Change Notice" callout at the top of `theory/README.md` would propagate to all documents that reference it and reduce the total fix burden.

### The SSM-vs-Hidden-State Ambiguity in the Paper

`RESEARCH_PAPER.md` Section 6.1 describes the compressor as consuming `40,960 dimensions (2560 × 16)`, which is the SSM state shape. The current code (`train_cheese_bridge.py`, `cognitive_bridge.py` default) uses last-token hidden states at 2560 dimensions. This inconsistency means the paper's architecture description does not match the code that produced the paper's results. This is the most important single document fix — the paper is the primary external-facing artifact.

### The `experiments/mamba_state_transfer/` Subdirectory

The four Phase 1 experiment scripts (`experiment_01` through `experiment_04`) all use `cache.ssm_states` because they predate Pinky's finding. These scripts are not dangerous if understood as Phase 1 probe code, but they are misleading without context. Adding a `PHASE1_NOTE.md` to that directory explaining the historical context of the SSM representation choice would cost little and prevent confusion.

---

*Scan completed 2026-03-25 by Anda. Priority: fix RESEARCH_PAPER.md §6.1 and MASTER_PLAN.md Vision first — these are the two highest-traffic entry points.*
