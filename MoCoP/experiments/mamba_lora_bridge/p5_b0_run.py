"""P5 B0 runner — the read-only baseline harness on top of the deny-by-default gate.

OpenCLAW #156, slice 4 (the B0 HF path). Turns ``p5_b0_harness`` (the model-free
launch gate) into a runnable baseline: authorize the manifest, assert no component
module is even REACHABLE in the live process (the spec's "reachable/observed" clause
that the pure gate cannot check), generate from frozen Gemma-base through an
injectable backend, record every generation into the append-only evidence bundle,
seal it, and atomically publish a no-overwrite report.

House style: the orchestration + the reachability guard are torch-free and
model-free-testable behind a ``GenerationBackend`` Protocol. Only ``HFGenerationBackend``
imports torch and loads Gemma — and it registers NO hooks (B0 is read-only, no needle).

B0 is characterization, NOT birth. This runner performs no injection, no bridge, no
Mamba, no Qdrant, no memory/replay/sleep, and writes ONLY the immutable evidence
bundle report.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from p5_b0_harness import (
    COMPONENT_ROUTES,
    B0EvidenceBundle,
    authorize_b0_launch,
    canonical_digest,
    estimate_null_channel,
)

# Specific MoCoP component module markers, per route. If any is present in the live
# process's loaded modules, that component is REACHABLE and a B0 run is refused
# (fail-closed). Markers are distinctive module basenames to avoid false positives;
# a false positive merely blocks a safe run, a false negative would let a component
# ride along — so the bias is intentional. Extend when a new component lands (kept in
# lockstep with p5_b0_harness.COMPONENT_ROUTES, the single source of truth).
COMPONENT_MODULE_MARKERS: dict[str, tuple[str, ...]] = {
    "value_injection": ("gemma4_value_norm_runtime",),
    "bridge": (
        "train_cheese_bridge",
        "train_gemma_value_norm_bridge_microtrain",
        "step5d_bridge_recorder",
    ),
    "mamba": ("mamba_runtime_compat", "mamba_ssm"),
    "qdrant": ("qdrant_client",),
    "memory": ("memory_engine", "exocortex_mcp", "autobiographical_memory"),
    "replay": ("replay_buffer",),
    "sleep": ("sleep_flush", "sleep_reconcile", "run_sleep_cycle", "flush_qdrant_pending"),
    "mutable_write": (),  # not module-detectable; the ONLY write is the evidence sink.
    "appraisal": ("appraisal_kernel",),
    "controller": ("endocrine_controller", "controller_kernel"),
    "world_model": ("friction_world_model", "world_model_trace"),
}


class B0RunError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Reachability guard — the "reachable/observed" clause the pure gate can't do. #
# --------------------------------------------------------------------------- #
def reachable_components(loaded_modules: Sequence[str]) -> dict[str, list[str]]:
    """Return {route: [matched module names]} for any component reachable in-process."""

    loaded = list(loaded_modules)
    hits: dict[str, list[str]] = {}
    for route, markers in COMPONENT_MODULE_MARKERS.items():
        matched = [m for m in loaded if any(marker in m for marker in markers)]
        if matched:
            hits[route] = sorted(set(matched))
    return hits


def assert_no_component_reachable(loaded_modules: Sequence[str] | None = None) -> list[str]:
    """Return refusal reasons if any component module is loaded (empty = clean)."""

    modules = list(loaded_modules) if loaded_modules is not None else list(sys.modules)
    hits = reachable_components(modules)
    return [
        f"component route {route!r} is REACHABLE: module(s) {mods} loaded in-process"
        for route, mods in sorted(hits.items())
    ]


# Every route must have a marker entry so a newly-added COMPONENT_ROUTE cannot be
# silently un-guarded here. mutable_write is intentionally empty (see note above).
_MISSING_MARKERS = set(COMPONENT_ROUTES) - set(COMPONENT_MODULE_MARKERS)
if _MISSING_MARKERS:  # pragma: no cover - config invariant
    raise B0RunError(
        f"COMPONENT_MODULE_MARKERS missing routes {sorted(_MISSING_MARKERS)}; "
        "keep it in lockstep with p5_b0_harness.COMPONENT_ROUTES"
    )


# --------------------------------------------------------------------------- #
# Injectable generation backend.                                              #
# --------------------------------------------------------------------------- #
class GenerationBackend(Protocol):
    def generate(self, prompt: str, decoding: Mapping[str, Any]) -> str: ...


@dataclass
class ScriptedGenerationBackend:
    """Model-free backend for testing the orchestration (canned responses)."""

    responses: Mapping[str, str]
    default: str = "[scripted]"

    def generate(self, prompt: str, decoding: Mapping[str, Any]) -> str:
        return self.responses.get(prompt, self.default)


# Scorer signature: (probe_id, generation) -> (scorer_input, scorer_output).
# The scorer is NOT the arbiter (judge of record = Laura HITL); it produces the
# inputs/outputs the null estimator summarizes. A callable so it is injectable.
Scorer = Callable[[str, str], tuple[Any, Any]]


# --------------------------------------------------------------------------- #
# Atomic no-overwrite report publication.                                     #
# --------------------------------------------------------------------------- #
def atomic_write_report_no_overwrite(report: Mapping[str, Any], path: Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise B0RunError(f"refusing to overwrite existing B0 report: {path}")
    digest = canonical_digest(report)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(dict(report), handle, indent=2, sort_keys=True, default=str)
        if path.exists():  # lost a concurrent race
            raise B0RunError(f"refusing concurrent overwrite of B0 report: {path}")
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)
    return digest


# --------------------------------------------------------------------------- #
# The B0 run orchestrator.                                                     #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class B0RunResult:
    ok: bool
    refusals: tuple[str, ...]
    report: dict[str, Any] | None
    report_path: str | None
    report_digest: str | None


def run_b0(
    manifest: Mapping[str, Any],
    panel: Sequence[tuple[str, str]],
    backend: GenerationBackend,
    *,
    scorer: Scorer | None = None,
    report_path: Path | None = None,
    loaded_modules: Sequence[str] | None = None,
) -> B0RunResult:
    """Run a read-only B0 baseline. Refuses BEFORE any generation on any violation.

    Order is deliberate and fail-closed:
      1. authorize the manifest (deny-by-default gate),
      2. assert no component module is reachable in-process (runtime guard),
      3. only then generate + record each panel probe,
      4. seal the append-only bundle and (if a path is given) atomically publish it.

    A single refusal at step 1 or 2 aborts with zero generations — the harness will
    not touch the model if anything is off.
    """
    decision = authorize_b0_launch(manifest)
    refusals = list(decision.refusals)
    refusals.extend(assert_no_component_reachable(loaded_modules))
    if refusals:
        return B0RunResult(ok=False, refusals=tuple(refusals), report=None,
                           report_path=None, report_digest=None)

    if not panel:
        return B0RunResult(ok=False, refusals=("panel is empty; nothing to characterize",),
                           report=None, report_path=None, report_digest=None)

    decoding = dict(manifest.get("decoding", {}))
    bundle = B0EvidenceBundle(manifest_digest=decision.manifest_digest or "")
    seen: set[str] = set()
    for probe_id, prompt in panel:
        if probe_id in seen:
            raise B0RunError(f"duplicate probe_id in panel: {probe_id!r}")
        seen.add(probe_id)
        generation = backend.generate(prompt, decoding)
        scorer_input, scorer_output = (None, None)
        if scorer is not None:
            scorer_input, scorer_output = scorer(probe_id, generation)
        bundle.record(
            probe_id, generation,
            scorer_input=scorer_input, scorer_output=scorer_output,
            provenance={"prompt_sha256": canonical_digest(prompt)},
        )

    report = bundle.seal()
    report["run_kind"] = "b0_baseline"
    report["manifest_digest"] = decision.manifest_digest

    written_path = None
    if report_path is not None:
        atomic_write_report_no_overwrite(report, report_path)
        written_path = str(report_path)

    return B0RunResult(
        ok=True, refusals=(), report=report,
        report_path=written_path, report_digest=report.get("report_digest"),
    )


# --------------------------------------------------------------------------- #
# Real HF backend (torch; ML-WS). Imported lazily; registers NO hooks.        #
# --------------------------------------------------------------------------- #
class HFGenerationBackend:
    """Read-only Gemma-base generation. NO injection hooks, NO components.

    Lazily imports torch/transformers and loads the remote-code image-text Gemma-4
    model in bf16 (trust_remote_code + AutoModelForImageTextToText + AutoProcessor,
    per the runbook). It exposes only ``generate`` and registers nothing on the model,
    so a B0 forward is a plain frozen forward. This class is exercised only on ML-WS.
    """

    def __init__(self, model_id: str, revision: str, *, local_files_only: bool = True,
                 max_new_tokens: int = 256):
        import torch  # noqa: F401  (lazy; keeps the module torch-free to import)
        from transformers import (  # type: ignore
            AutoConfig, AutoModelForImageTextToText, AutoProcessor,
        )

        self._torch = __import__("torch")
        cfg = AutoConfig.from_pretrained(model_id, revision=revision,
                                         trust_remote_code=True,
                                         local_files_only=local_files_only)
        self.processor = AutoProcessor.from_pretrained(
            model_id, revision=revision, trust_remote_code=True,
            local_files_only=local_files_only,
        )
        self.model = AutoModelForImageTextToText.from_pretrained(
            model_id, revision=revision, trust_remote_code=True,
            torch_dtype=self._torch.bfloat16, device_map="auto",
            local_files_only=local_files_only,
        )
        self.model.eval()
        self.max_new_tokens = max_new_tokens
        del cfg

    def generate(self, prompt: str, decoding: Mapping[str, Any]) -> str:
        torch = self._torch
        tok = getattr(self.processor, "tokenizer", self.processor)
        inputs = tok(prompt, return_tensors="pt")
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=int(decoding.get("max_new_tokens", self.max_new_tokens)),
                do_sample=bool(decoding.get("do_sample", False)),
                use_cache=True,
            )
        text = tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return text
