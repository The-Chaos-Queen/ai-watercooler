# Option B Note (Post Option A)

Date: 2026-04-07
Scope: investigative note only (no CUDA patching, no selective-scan surgery)

## Option A Status

`trajectory_windowed_onepass.py` is implemented and validated on the tiny fixture with explicit approximate/windowed labeling.

Sanity report (2.8B, tiny fixture):
- one-pass vs tokenwise (exact references): min cosine `0.9999988`, final cosine `0.9999996` (PASS)
- windowed vs one-pass: min cosine `0.9838015` (expected approximate drift on later samples)

Artifacts:
- `trajectory_windowed_sanity_run_20260407_28b_v2/windowed_trajectory_report.json`
- `trajectory_windowed_sanity_run_20260407_28b_v2/windowed_sanity_equivalence_report.json`

## Option B: Separate-Branch Investigation Plan

Recommended branch:
- `option-b-state-spaces-mamba-probe`

Goal:
- test original `state-spaces/mamba` runtime path as first exact full-recurrence candidate
- keep this isolated from Hugging Face Option A workflow

Suggested steps:
1. Create a clean branch and a dedicated script (`trajectory_state_spaces_probe.py`) that does not modify current Option A runner.
2. Install/clone `state-spaces/mamba` in a separate test directory under WSL Debian (`/root/mamba_venv`).
3. Start with tiny fixture + short slice only.
4. Implement layer-state capture hook in the Option B probe path.
5. Compare against current references (`one_pass_reference`, `tokenwise_reference`) with the same cosine/L2 harness.
6. Continue only if exactness and runtime both clear the bar.

Do not do in Option B branch yet:
- no custom CUDA kernel edits
- no `selective_scan_fn(initial_state=...)` API surgery
- no Hugging Face cache-path “fixups” pretending to be exact continuation
