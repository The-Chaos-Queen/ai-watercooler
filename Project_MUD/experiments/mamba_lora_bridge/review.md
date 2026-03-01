# Code Review: `mamba_lora_bridge`

Date: 2026-02-26
Reviewer: Codex
Scope:
- `cognitive_bridge.py`
- `models.py`
- `server.py`

Method:
- Static review only (no runtime execution in this pass).
- Findings are ordered by severity (Critical -> High -> Medium -> Low).

## Executive Summary

The framework is structurally strong (clear separation between orchestration, model modules, and API), but there are several production-blocking risks:
- 1 Critical security issue in state loading.
- Multiple High issues around concurrency safety, cleanup guarantees, and runtime stability.
- Medium/Low issues in scalability and validation.

The top 5 issues should be fixed before using this service in a shared or long-running environment.

---

## Findings

### 1) Critical: Unsafe deserialization exposed over API (RCE risk)

Severity: **Critical**

Evidence:
- `server.py:360`
- `server.py:364`
- `cognitive_bridge.py:525`

Problem:
- `/load_state` accepts a caller-provided path and forwards it to `torch.load(..., weights_only=False)`.
- `torch.load` with pickle-enabled behavior can execute arbitrary code if the file is malicious.

Impact:
- Remote code execution via crafted `.pt` files.

Recommendation:
- Remove arbitrary-path loading from public endpoint.
- Restrict loads to a controlled state directory and filename allowlist.
- Prefer safer serialization formats for state blobs.
- If `torch.load` remains, set `weights_only=True` where possible and strictly validate contents.

---

### 2) High: Global bridge is not concurrency-safe

Severity: **High**

Evidence:
- `server.py:306`
- `server.py:308`
- `cognitive_bridge.py:407`
- `cognitive_bridge.py:313`
- `cognitive_bridge.py:384`

Problem:
- The service uses a single global `cognitive_bridge` instance.
- `generate()` mutates shared state (`turn_count`, Mamba history, dynamic LoRA tensors).
- Concurrent requests can interleave and contaminate each other.

Impact:
- Cross-request state bleed, nondeterministic outputs, and hard-to-debug failures.

Recommendation:
- Serialize bridge access with an `asyncio.Lock`, or
- Move to per-session/per-player bridge state, or
- Use a dedicated single-worker queue for generation.

---

### 3) High: LoRA cleanup is skipped when generation throws

Severity: **High**

Evidence:
- `cognitive_bridge.py:417`
- `cognitive_bridge.py:427`
- `cognitive_bridge.py:443`

Problem:
- `_clear_lora()` is called only on the success path.
- If `qwen_model.generate()` fails, stale LoRA remains active.

Impact:
- Subsequent requests may run with stale/adversarial adapter state.

Recommendation:
- Wrap LoRA injection + generation in `try/finally`, always clearing LoRA in `finally`.

---

### 4) High: `unpatch_transformer()` parses projection name incorrectly

Severity: **High**

Evidence:
- `cognitive_bridge.py:268`
- `cognitive_bridge.py:288`
- `cognitive_bridge.py:291`

Problem:
- Keys are built like `layer_0_q_proj`.
- `split("_")` then `parts[2]` yields `q`, not `q_proj`.
- Unpatching restores wrong attribute and can fail.

Impact:
- Broken unpatch path; model may remain partially patched/corrupted.

Recommendation:
- Store target specs as structured tuples/dicts instead of encoded strings, or
- Parse with controlled splitting and re-join the projection suffix.

---

### 5) High: Mamba fallback path is shape-invalid and likely crashes

Severity: **High**

Evidence:
- `cognitive_bridge.py:337`
- `cognitive_bridge.py:340`
- `cognitive_bridge.py:346`

Problem:
- Fallback path assumes `last_hidden_state` is present and then performs incompatible `expand` operations.
- Tensor rank/dimension logic is inconsistent.

Impact:
- Runtime exception when fallback triggers, exactly when robustness is needed.

Recommendation:
- Implement a valid fallback tensor constructor producing `(batch, layers, d_model, d_state)`.
- If this cannot be done reliably for a given backend, fail fast with an explicit error.

---

### 6) High: CPU execution path uses `float16` for model load

Severity: **High**

Evidence:
- `cognitive_bridge.py:160`
- `cognitive_bridge.py:183`

Problem:
- Non-4bit path loads Qwen as `float16` even on CPU.
- Mamba is always loaded as `float16`.
- Many CPU ops do not support FP16 well.

Impact:
- Startup or inference failures on CPU-only hosts.

Recommendation:
- Use `float32` (or supported `bfloat16`) when CUDA is unavailable.

---

### 7) High: LoRA tensor dtype may mismatch runtime activation dtype

Severity: **High**

Evidence:
- `cognitive_bridge.py:381`
- `cognitive_bridge.py:383`
- `models.py:226`

Problem:
- LoRA A/B are moved to device but not explicitly cast to weight/activation dtype.
- `x @ A @ B` can fail or promote unexpectedly.

Impact:
- Runtime dtype errors or unnecessary compute overhead.

Recommendation:
- Cast A/B to `dynamic_layer.weight.dtype` (or `x.dtype` at forward time).

---

### 8) Medium: State load may fail across devices (missing `map_location`)

Severity: **Medium**

Evidence:
- `cognitive_bridge.py:525`

Problem:
- `torch.load(path, weights_only=False)` has no `map_location`.
- States saved on CUDA can fail to load on CPU-only machines.

Impact:
- Operational fragility across deployment environments.

Recommendation:
- Add `map_location` based on configured runtime device.

---

### 9) Medium: Mamba history grows without bound and full history is recomputed each turn

Severity: **Medium**

Evidence:
- `cognitive_bridge.py:313`
- `cognitive_bridge.py:324`

Problem:
- Every request appends to `_mamba_history_ids`.
- Every request runs Mamba over entire accumulated history.

Impact:
- Increasing latency/memory over long sessions; eventual throughput collapse.

Recommendation:
- Use incremental cache updates or windowing.
- Add max history length / summarization policy.

---

### 10) Medium: Target layer specs are not validated

Severity: **Medium**

Evidence:
- `cognitive_bridge.py:193`
- `cognitive_bridge.py:197`
- `cognitive_bridge.py:234`

Problem:
- Empty/invalid `target_layers` can crash on `target_specs[0]`.
- No checks for projection existence or layer bounds.

Impact:
- Startup failures with poor diagnostics.

Recommendation:
- Validate schema, non-empty list, bounds, and projection names before patching.

---

### 11) Medium: Hypernetwork assumes square projection dimensions

Severity: **Medium**

Evidence:
- `cognitive_bridge.py:198`
- `models.py:105`
- `models.py:140`
- `models.py:226`

Problem:
- Hypernetwork output uses one `target_dim` for both A/B generation.
- This assumes `in_features == out_features` in patched layers.

Impact:
- Potential shape errors if non-square projections are targeted later.

Recommendation:
- Track per-target `(in_features, out_features)` and generate A/B accordingly.

---

### 12) Low: Duplicate compressor computation per turn

Severity: **Low**

Evidence:
- `cognitive_bridge.py:415`
- `cognitive_bridge.py:372`

Problem:
- Context vector is computed once in `generate()` and again in `_inject_lora()`.

Impact:
- Avoidable overhead.

Recommendation:
- Compute once and pass context into `_inject_lora()`.

---

## Testing Gaps

No test coverage was found in this folder for:
- Concurrency safety for `/generate`.
- LoRA cleanup on exception path.
- Patch/unpatch roundtrip integrity.
- Mamba fallback tensor path.
- Cross-device state save/load behavior.
- `/load_state` security hardening.

---

## Suggested Remediation Order

1. Fix unsafe state loading (Critical).
2. Add concurrency guard around cognitive generation.
3. Add `try/finally` LoRA cleanup.
4. Fix `unpatch_transformer` key handling.
5. Fix fallback tensor path and CPU dtype handling.
6. Add validation + tests for all above.

---

## Notes

- This review intentionally prioritizes correctness, security, and production behavior over style.
- The architecture is promising; these changes mainly harden it for reliable real-world operation.
