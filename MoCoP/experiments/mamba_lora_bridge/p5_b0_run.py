"""P5 B0 runner — the read-only baseline harness on top of the deny-by-default gate.

OpenCLAW #156, slice 4 (the B0 HF path), hardened per a-Codex review of 49b5a3d.
Turns ``p5_b0_harness`` (the model-free launch gate) into a runnable baseline:
authorize the manifest, assert no component module is REACHABLE in the live process,
BIND every executed input to the authorized manifest, RESERVE the evidence sink,
journal each attempt before the forward, generate from frozen Gemma-base through an
injectable backend, seal the append-only evidence bundle, and atomically publish a
no-overwrite report whose digest covers the exact published JSON.

House style: orchestration + reachability guard are torch-free and model-free-testable
behind a ``GenerationBackend`` Protocol. Only ``HFGenerationBackend`` imports torch and
loads Gemma — and it registers NO hooks (B0 is read-only, no needle).

B0 is characterization, NOT birth: no injection, no bridge, no Mamba, no Qdrant, no
memory/replay/sleep, and it writes ONLY the immutable evidence bundle report + journal.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from p5_b0_harness import (
    COMPONENT_ROUTES,
    B0EvidenceBundle,
    authorize_b0_launch,
    canonical_digest,
    estimate_null_channel,  # noqa: F401  (re-exported for B0 null estimation)
)

# Specific MoCoP component module markers, per route, matched against a loaded
# module's BASENAME (last dotted segment) to avoid transformers/torch false positives.
# Fail-closed: a false positive only blocks a safe run; a false negative would let a
# component ride along. Kept in lockstep with p5_b0_harness.COMPONENT_ROUTES (enforced
# at import below). This inventory was widened after a-Codex found real memory modules
# (dense_associative_memory / lesson_memory / astrocyte_memory_controller) uncovered.
COMPONENT_MODULE_MARKERS: dict[str, tuple[str, ...]] = {
    "value_injection": ("value_norm_runtime", "injection", "inject_"),
    "bridge": ("bridge", "cheese_bridge"),
    "mamba": ("mamba",),
    "qdrant": ("qdrant",),
    "memory": ("memory", "exocortex", "autobiographical", "astrocyte", "hippocamp",
               "engram"),
    "replay": ("replay",),
    "sleep": ("sleep", "flush_qdrant"),
    "mutable_write": (),  # not module-detectable; the ONLY write is the evidence sink.
    "appraisal": ("appraisal",),
    "controller": ("controller", "endocrine"),
    "world_model": ("world_model", "friction_world"),
}


class B0RunError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Reachability guard — the "reachable/observed" clause (live process).         #
# --------------------------------------------------------------------------- #
def reachable_components(loaded_modules: Sequence[str]) -> dict[str, list[str]]:
    """Return {route: [matched module names]} for any component reachable in-process.

    Only TOP-LEVEL (dotless) module names are inspected. Every MoCoP component in this
    repo is a top-level script (``import dense_associative_memory``), so a dotless
    filter catches them all via the family markers while excluding dotted framework
    internals (e.g. ``torch.cuda.memory``, ``transformers.models...``) that would
    otherwise false-positive on generic substrings like "memory"/"controller".
    """
    top_level = [m for m in loaded_modules if "." not in m]
    hits: dict[str, list[str]] = {}
    for route, markers in COMPONENT_MODULE_MARKERS.items():
        matched = [m for m in top_level if any(marker in m for marker in markers)]
        if matched:
            hits[route] = sorted(set(matched))
    return hits


def assert_no_component_reachable(loaded_modules: Sequence[str] | None = None) -> list[str]:
    """Refusal reasons if any component module is loaded (empty = clean).

    ``loaded_modules`` is a TEST/helper seam only. The safety-critical orchestrator
    (``run_b0``) never passes it — it inspects the live ``sys.modules`` unconditionally.
    """
    modules = list(loaded_modules) if loaded_modules is not None else list(sys.modules)
    hits = reachable_components(modules)
    return [
        f"component route {route!r} is REACHABLE: module(s) {mods} loaded in-process"
        for route, mods in sorted(hits.items())
    ]


_MISSING_MARKERS = set(COMPONENT_ROUTES) - set(COMPONENT_MODULE_MARKERS)
if _MISSING_MARKERS:  # pragma: no cover - config invariant
    raise B0RunError(
        f"COMPONENT_MODULE_MARKERS missing routes {sorted(_MISSING_MARKERS)}; "
        "keep it in lockstep with p5_b0_harness.COMPONENT_ROUTES"
    )


# --------------------------------------------------------------------------- #
# Injectable generation backend (must be bindable to the manifest).           #
# --------------------------------------------------------------------------- #
class GenerationBackend(Protocol):
    def descriptor(self) -> Mapping[str, Any]: ...
    def generate(self, prompt: str, decoding: Mapping[str, Any]) -> str: ...


@dataclass
class ScriptedGenerationBackend:
    """Model-free backend for testing (canned responses + a declared descriptor)."""

    responses: Mapping[str, str]
    model_descriptor: Mapping[str, Any] = None  # type: ignore[assignment]
    default: str = "[scripted]"

    def descriptor(self) -> Mapping[str, Any]:
        return dict(self.model_descriptor or {})

    def generate(self, prompt: str, decoding: Mapping[str, Any]) -> str:
        return self.responses.get(prompt, self.default)


# Scorer signature: (probe_id, generation) -> (scorer_input, scorer_output).
# NOT the arbiter (judge of record = Laura HITL); it feeds the null estimator.
Scorer = Callable[[str, str], tuple[Any, Any]]


# --------------------------------------------------------------------------- #
# Manifest binding of executed inputs.                                         #
# --------------------------------------------------------------------------- #
def _validate_panel(panel: Sequence[Any]) -> list[str]:
    """Whole-panel pre-validation (before ANY forward): shape, types, uniqueness."""
    refusals: list[str] = []
    if not panel:
        return ["panel is empty; nothing to characterize"]
    seen: set[str] = set()
    for i, item in enumerate(panel):
        if (not isinstance(item, (tuple, list)) or len(item) != 2
                or not isinstance(item[0], str) or not item[0]
                or not isinstance(item[1], str)):
            refusals.append(f"panel[{i}] is not a (non-empty probe_id, prompt) pair")
            continue
        pid = item[0]
        if pid in seen:
            refusals.append(f"panel has duplicate probe_id {pid!r}")
        seen.add(pid)
    return refusals


def canonical_panel_hash(panel: Sequence[tuple[str, str]]) -> str:
    return canonical_digest([[pid, prompt] for pid, prompt in panel])


def _bind_execution_to_manifest(
    manifest: Mapping[str, Any], panel: Sequence[tuple[str, str]],
    backend: GenerationBackend, scorer: Scorer | None, scorer_version: str | None,
) -> list[str]:
    """Refuse unless the ACTUAL panel/backend/scorer match the authorized manifest."""
    refusals: list[str] = []

    declared_panel = manifest.get("panel", {}).get("hash")
    actual_panel = canonical_panel_hash(panel)
    if declared_panel != actual_panel:
        refusals.append(
            f"executed panel hash {actual_panel[:12]}.. != manifest panel.hash "
            f"{str(declared_panel)[:12]}.. (unbound panel)"
        )

    desc = dict(backend.descriptor())
    model = manifest.get("model", {})
    for key in ("id", "revision"):
        if model.get(key) != desc.get(key):
            refusals.append(
                f"backend.{key} {desc.get(key)!r} != manifest model.{key} {model.get(key)!r}"
            )

    declared_scorer = manifest.get("scorer", {}).get("version")
    if declared_scorer:
        if scorer is None:
            refusals.append("manifest declares a scorer.version but no scorer was supplied")
        elif scorer_version != declared_scorer:
            refusals.append(
                f"scorer_version {scorer_version!r} != manifest scorer.version "
                f"{declared_scorer!r}"
            )
    return refusals


# --------------------------------------------------------------------------- #
# Evidence sink reservation + atomic no-overwrite publication (O_EXCL).        #
# --------------------------------------------------------------------------- #
def reserve_report_slot(path: Path) -> None:
    """Atomically claim the destination BEFORE any forward. Raises if already taken."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise B0RunError(f"evidence sink already reserved/exists: {path}") from exc
    os.close(fd)


def fill_reserved_report(report: Mapping[str, Any], path: Path) -> None:
    """Write the final report into a slot we already reserved (own it, no clobber)."""
    path = Path(path)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(dict(report), handle, indent=2, sort_keys=True, default=str)
        os.replace(temp_path, path)     # replaces OUR reserved placeholder only
    finally:
        temp_path.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# The B0 run orchestrator.                                                     #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class B0RunResult:
    ok: bool
    refusals: tuple[str, ...]
    report: dict[str, Any] | None
    report_path: str | None
    published_digest: str | None


def run_b0(
    manifest: Mapping[str, Any],
    panel: Sequence[tuple[str, str]],
    backend: GenerationBackend,
    *,
    scorer: Scorer | None = None,
    scorer_version: str | None = None,
    report_path: Path | None = None,
) -> B0RunResult:
    """Run a read-only B0 baseline. Refuses (zero forwards) on ANY gate violation.

    Fail-closed order:
      1. authorize the manifest (deny-by-default gate),
      2. assert no component module reachable in the LIVE process,
      3. whole-panel pre-validation,
      4. bind executed panel/backend/scorer to the authorized manifest,
      5. resolve + RESERVE the manifest's evidence sink (O_EXCL) before any forward,
      6. per probe: journal the attempt durably, then generate, then record,
      7. seal, finalize ALL report fields, compute the published digest over the exact
         published JSON, and fill the reserved slot.
    """
    decision = authorize_b0_launch(manifest)
    refusals = list(decision.refusals)
    refusals.extend(assert_no_component_reachable())               # live sys.modules
    refusals.extend(_validate_panel(panel))
    if not refusals:
        refusals.extend(
            _bind_execution_to_manifest(manifest, panel, backend, scorer, scorer_version)
        )

    # Resolve + bind the evidence destination to the manifest before touching the model.
    sink_path = manifest.get("evidence_sink", {}).get("path")
    resolved_path: Path | None = None
    if not refusals:
        if report_path is not None and str(report_path) != str(sink_path):
            refusals.append(
                f"report_path {report_path} != manifest evidence_sink.path {sink_path}"
            )
        elif not sink_path:
            refusals.append("manifest evidence_sink.path is unset; cannot bind evidence")
        else:
            resolved_path = Path(report_path if report_path is not None else sink_path)

    if refusals:
        return B0RunResult(False, tuple(refusals), None, None, None)

    assert resolved_path is not None
    reserve_report_slot(resolved_path)                             # O_EXCL, pre-forward
    journal_path = Path(str(resolved_path) + ".journal")

    decoding = dict(manifest.get("decoding", {}))
    bundle = B0EvidenceBundle(manifest_digest=decision.manifest_digest or "")
    try:
        with open(journal_path, "w", encoding="utf-8") as journal:
            for ordinal, (probe_id, prompt) in enumerate(panel):
                attempt = {
                    "event": "attempt", "ordinal": ordinal, "probe_id": probe_id,
                    "run_kind": "b0_baseline", "manifest_digest": decision.manifest_digest,
                    "prompt_sha256": canonical_digest(prompt),
                    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                journal.write(json.dumps(attempt, sort_keys=True) + "\n")
                journal.flush()
                os.fsync(journal.fileno())
                generation = backend.generate(prompt, decoding)    # the governed forward
                scorer_input, scorer_output = (None, None)
                if scorer is not None:
                    scorer_input, scorer_output = scorer(probe_id, generation)
                bundle.record(
                    probe_id, generation,
                    scorer_input=scorer_input, scorer_output=scorer_output,
                    provenance={"prompt_sha256": canonical_digest(prompt)},
                )
                journal.write(json.dumps({"event": "recorded", "ordinal": ordinal,
                                          "probe_id": probe_id}, sort_keys=True) + "\n")
                journal.flush()
                os.fsync(journal.fileno())
    except Exception:
        # A partial run leaves the reserved slot + journal as durable evidence of the
        # incomplete attempt; we do NOT write a sealed report for a failed run.
        raise

    report = bundle.seal()
    report["run_kind"] = "b0_baseline"
    report["manifest_digest"] = decision.manifest_digest
    # Digest covers the EXACT published JSON (all fields present, minus this digest).
    report["published_digest"] = canonical_digest(
        {k: v for k, v in report.items() if k != "published_digest"}
    )
    fill_reserved_report(report, resolved_path)

    return B0RunResult(
        ok=True, refusals=(), report=report,
        report_path=str(resolved_path), published_digest=report["published_digest"],
    )


# --------------------------------------------------------------------------- #
# Real HF backend (torch; ML-WS). Imported lazily; registers NO hooks.        #
# --------------------------------------------------------------------------- #
class HFGenerationBackend:
    """Read-only Gemma-base generation. NO injection hooks, NO components.

    Exposes ``descriptor`` (bound to the manifest by run_b0) and ``generate`` and
    registers nothing on the model, so a B0 forward is a plain frozen forward. Only
    exercised on ML-WS.
    """

    def __init__(self, model_id: str, revision: str, *, dtype: str = "bf16",
                 local_files_only: bool = True, max_new_tokens: int = 256):
        from transformers import (  # type: ignore
            AutoModelForImageTextToText, AutoProcessor,
        )

        self._torch = __import__("torch")
        self._model_id = model_id
        self._revision = revision
        self._dtype = dtype
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

    def descriptor(self) -> Mapping[str, Any]:
        return {"id": self._model_id, "revision": self._revision, "dtype": self._dtype}

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
        return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
