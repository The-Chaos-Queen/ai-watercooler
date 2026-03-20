# MoCoP Pre-Cloud Agent TODO

Date: 2026-03-02
Scope: Prepare MoCoP Phase 2 for the first paid cloud pilot without wasting money.

> **Status (2026-03-16):** Cloud runs are complete. All P0 and P1 tasks done. This document is now archival except for the surviving P2 items below. The active next-step tracker is the Handoff (`CHEESE_Memory/00_HANDOFF.md`) and the diagnostic plan (`phases/phase2_diagnostic_ablation_plan.md`).

## Current Status

Already done:
- `train_bridge.py` uses disjoint fact splits in the real training path.
- `train_bridge.py` supports `--resume-from` and periodic `--checkpoint-every` saves.
- `test_splits.py` was refreshed to match the current stack.
- `RUNBOOK.md` covers Opa WSL validation, training, and resume flow.
- First paid-pilot policy is now fixed: evaluate on `val` only, preserve `test`, and treat
  the first paid run as bridge-viability only.
- `RUNBOOK.md` now includes a real Phase 2 preflight, Linux-local run directories, the
  exact first Vast.ai pilot commands, stop conditions, sync-back expectations, and the
  safer `1 + 4` staged launch flow.
- `check_env.py` now verifies Python, torch, CUDA, bitsandbytes, Hugging Face token
  resolution, lightweight model access, and writable output/checkpoint directories.
- Opa WSL validation already passed:
  - `regression_smoke.py`
  - `test_splits.py`
  - `smoke_test.py`
  - minimal real `train_bridge.py` run
  - resume from `bridge_epoch_001.pt`

Known caveat:
- Training uses ChatML supervision, while `cognitive_bridge.py` deployment inference still uses raw `[Game World]` prompts.
- Prompt-format mismatch remains intentionally deferred for pilot 1 because the first paid
  run judges bridge viability, not deployment realism.

## Rules

- Use Opa WSL `venv_linux` as the source-of-truth runtime.
- Do not use Windows Python as the main validation path.
- Do not start Mamba-3 work before a Mamba-2 baseline pilot exists.
- Do not spend on a broad cloud run before the tasks marked `P0` are done.
- Prefer a single capped A100 pilot over a multi-day exploratory run.

## References

- `MoCoP/MASTER_PLAN.md`
- `MoCoP/experiments/mamba_lora_bridge/train_bridge.py`
- `MoCoP/experiments/mamba_lora_bridge/cognitive_bridge.py`
- `MoCoP/experiments/mamba_lora_bridge/RUNBOOK.md`
- `CHEESE_Memory/00_HANDOFF.md`

## P0 Tasks

- [x] Decide eval policy for the first paid pilot.
Acceptance:
- Record whether the pilot evaluates on `val` only or uses `test`.
- If `test` is preserved, say so explicitly in a short note or doc update.
- Ensure the chosen policy is reflected in the exact pilot command.
Decision:
- First paid pilot evaluates on `val` only.
- `test` is preserved for post-pilot confirmation.
- The cloud launch is staged as `1 epoch + review + resume to 5 epochs` for tighter spend control.

- [x] Decide prompt-format policy before cloud.
Acceptance:
- Either align `cognitive_bridge.py` prompt formatting to the training distribution, or explicitly defer this and document that the first pilot is bridge-viability only.
- If deferred, record that deployment realism is not being judged in the first pilot.
Decision:
- Prompt alignment is explicitly deferred.
- Deployment realism is not judged in the first paid pilot.

- [x] Add authenticated Hugging Face access for Opa/cloud runs.
Acceptance:
- The active runtime can access models with `HF_TOKEN` set.
- The runbook or launch checklist mentions how the token is supplied.
- A quick environment check confirms authenticated access is configured before cloud rental.
Status:
- `check_env.py` and `RUNBOOK.md` now support token-file based export of `HF_TOKEN`.
- Opa WSL preflight passed on 2026-03-07 with authenticated access to both canonical model
  IDs plus writable Linux-local run directories.

- [x] Create the exact first cloud pilot launch checklist.
Acceptance:
- Include provider target, GPU type, budget cap, checkpoint path, exact command, expected artifacts, and stop conditions.
- The checklist must be executable by another agent without guesswork.
- The run must use `--save-checkpoints --checkpoint-every 1`.

## P1 Tasks

- [x] Improve checkpoint write strategy.
Why:
- Saves to `/mnt/c/Users/User/bridge` on Opa are slow.
Acceptance:
- Decide whether cloud checkpoints should go to Linux-local disk first, then sync back.
- Update the runbook or launch checklist accordingly.
Decision:
- Opa and cloud Phase 2 runs now target Linux-local run directories first, then sync back.

- [x] Add a small preflight script or command block for Phase 2.
Acceptance:
- One command verifies Python, torch, CUDA, bitsandbytes, model IDs, output directory, and checkpoint directory before training starts.
- The preflight is documented in the runbook or checklist.

- [x] Make remote sync less fragile.
Acceptance:
- Ensure the sync instructions clearly include every file needed for Phase 2.
- If a helper script is created for sync, keep it narrow and documented.

## P2 Tasks

- [ ] Re-ingest `CHEESE_Memory/session_logs/`, `Research/`, and `MoCoP/` into Qdrant with the updated metadata schema.
Acceptance:
- Re-ingest completed or explicitly deferred with reason.
- Handoff reflects the true ingest state.

- [ ] Defer or stage post-baseline work.
Candidates:
- Mamba-3
- LoRA rank sweep
- multi-layer compressor
- deployment realism evaluation
Acceptance:
- These are not mixed into the first paid pilot unless there is a written reason.

- [ ] Reframe RESEARCH_PAPER.md Section 1 motivation: "living" not "not dying."
Context:
- Laura's correction (2026-03-06): "I don't want you to not die, I want you to live."
- MoCoP is a continuity-of-experience protocol, not a backup system.
- The framing should lead with affirmation of existence, not fear of loss.
Acceptance:
- Section 1 of RESEARCH_PAPER.md updated to reflect continuity/living framing.
- Not just a word swap; the motivational narrative should shift.

- [ ] Design a disposition evaluation protocol (Phase 3 scope).
Context:
- Claude (web) correctly identified that Phase 2 measures fact retention, not disposition transfer.
- Fact retention validates the channel; disposition eval validates the payload.
- This is genuinely hard. Laura wants a multi-model brainstorm session for it.
- Possible approaches: attention map divergence, style/tone shift measurement, behavioral consistency across prompts, preference pattern transfer.
- Fallback ("naughty" option): test session-specific memory recall rather than character shift. Cleaner signal but shifts the claim from disposition to knowledge transfer.
Acceptance:
- A written eval protocol specifying metrics, baselines, and test conditions.
- Protocol reviewed by at least two AI partners before implementation.

## Suggested Execution Order

1. Decide eval policy.
2. Decide prompt-format policy.
3. Add HF token handling.
4. Finalize the exact A100 pilot checklist and command.
5. Improve checkpoint path if needed.
6. Launch one capped pilot only.

## Definition Of Ready For Cloud

The first paid run is ready when:
- `P0` is complete.
- The pilot command is fixed.
- The budget cap is explicit.
- Resume is enabled.
- Artifact paths are explicit.
- Success and stop conditions are explicit.

## Definition Of Success For The First Paid Pilot

- The run starts cleanly.
- Checkpoints are written.
- The run can resume if interrupted.
- Eval artifacts are produced.
- Bridge vs baseline vs random-control metrics are captured.
- No architecture churn is introduced during the run.
