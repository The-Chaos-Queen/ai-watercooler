"""P5 B0 runner — the read-only baseline harness on top of the deny-by-default gate.

OpenCLAW #156, slice 4 (the B0 HF path). Supersedes b1190e9 + the #958 patch, hardened
against wolf-Codex review of record #954/#960 (MoCoP/reviews/p5_b0_runner_review_2026-07-12.md).
Turns ``p5_b0_harness`` (the model-free launch gate) into a runnable baseline:
authorize the manifest, assert no component module is REACHABLE in the live process
(before AND after every forward), MANDATORILY bind every executed input to the
authorized manifest with DERIVED hashes, exclusively reserve an append-only journal,
journal each attempt with a unique id + digests, generate from frozen Gemma-base through
an injectable backend, seal the append-only evidence bundle, and publish the report with
a NO-REPLACE atomic primitive whose bytes are verified after publication.

House style: orchestration + reachability guard are torch-free and model-free-testable
behind a ``GenerationBackend`` Protocol. Only ``HFGenerationBackend`` imports torch and
loads Gemma — and it registers NO hooks (B0 is read-only, no needle).

B0 is characterization, NOT birth: no injection, no bridge, no Mamba, no Qdrant, no
memory/replay/sleep, and it writes ONLY the immutable evidence bundle report + journal.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from p5_b0_harness import (
    COMPONENT_ROUTES,
    B0EvidenceBundle,
    assert_strict_json,
    authorize_b0_launch,
    canonical_digest,
    estimate_null_channel,  # noqa: F401  (re-exported for B0 null estimation)
)

# --------------------------------------------------------------------------- #
# Reviewed EXACT forbidden-module inventory (#960 HIGH-4).                     #
# --------------------------------------------------------------------------- #
# Matching is EXACT equality against a loaded module's top-level package name OR its full
# basename (last dotted segment) — NEVER a substring. Exact equality is what
# simultaneously (a) catches external component packages living in site-packages
# (``qdrant_client``, ``mamba_ssm``) that a ``__file__``-path heuristic misses, and
# (b) refuses to false-fire on framework internals like ``torch.cuda.memory`` (basename
# ``memory`` is NOT an inventoried name — the real modules are ``memory_evidence``,
# ``dense_associative_memory``, ...). Both the dotless-basename and the ``__file__``-path
# heuristics are retired. This inventory is reviewed against the repo's real component
# modules; a new component MUST be added here or B0's no-component guarantee silently
# weakens (enforced in lockstep with COMPONENT_ROUTES at import below).
FORBIDDEN_ROUTE_MODULES: dict[str, frozenset[str]] = {
    "value_injection": frozenset({
        "gemma4_value_norm_runtime", "train_gemma_value_norm_bridge_microtrain",
    }),
    "bridge": frozenset({
        "train_cheese_bridge", "cognitive_bridge", "hybrid_bridge", "bridge_dataset",
        "train_bridge", "step5d_bridge_recorder", "diagnose_bridge_pipeline",
    }),
    "mamba": frozenset({
        "mamba_ssm", "local_mamba_runner", "mamba_linear_probe", "mamba_runtime_compat",
        "collect_mamba_states", "extract_single_mamba_vector", "compare_mamba_vectors",
    }),
    "qdrant": frozenset({
        "qdrant_client", "qdrant_transport", "flush_qdrant_pending",
        "qdrant_writer_smoke",
    }),
    "memory": frozenset({
        "memory_evidence", "dense_associative_memory", "autobiographical_memory",
        "lesson_memory", "lesson_memory_cli", "d2_memory_legibility_eval",
        "exocortex_mcp_server",
    }),
    "replay": frozenset({"gate_policy_replay"}),
    "sleep": frozenset({
        "sleep_reconcile", "sleep_flush", "run_sleep_cycle", "sleep_decay_sweep",
        "sleep_ethics_gate", "sleep_nloop_guard", "sleep_threshold_sweep",
        "run_shadow_sleep_nloop_a3",
    }),
    "mutable_write": frozenset(),  # not module-detectable; the ONLY write is the sink.
    "appraisal": frozenset({"appraisal"}),
    "controller": frozenset({
        "modulatory_controller", "astrocyte_memory_controller",
        "run_memory_controller_fixture_probe",
    }),
    "world_model": frozenset({
        "friction_world_model", "world_model_baselines", "world_model_capture",
        "world_model_events", "world_model_trace",
    }),
}


class B0RunError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Reachability guard — the "reachable/observed" clause (live process).         #
# --------------------------------------------------------------------------- #
def reachable_components(loaded_modules: Mapping[str, Any]) -> dict[str, list[str]]:
    """Return {route: [matched module names]} for any component reachable in-process.

    A module is a hit if its top-level package name OR its full basename matches an
    inventoried name by EXACT equality. A ``None`` value in ``sys.modules`` (an attempted
    import) still counts by name — fail-closed: presence of the NAME is reachability.
    """
    hits: dict[str, list[str]] = {}
    for name in loaded_modules.keys():
        if not isinstance(name, str) or not name:
            continue
        top = name.split(".", 1)[0]
        base = name.rsplit(".", 1)[-1]
        for route, forbidden in FORBIDDEN_ROUTE_MODULES.items():
            if name in forbidden or top in forbidden or base in forbidden:
                bucket = hits.setdefault(route, [])
                if name not in bucket:
                    bucket.append(name)
    for v in hits.values():
        v.sort()
    return hits


def assert_no_component_reachable(loaded_modules: Mapping[str, Any] | None = None) -> list[str]:
    """Refusal reasons if any component module is loaded (empty = clean).

    ``loaded_modules`` is a TEST/helper seam only. The safety-critical orchestrator
    (``run_b0``) never passes it — it inspects the live ``sys.modules`` unconditionally,
    before AND after every governed forward.
    """
    modules = loaded_modules if loaded_modules is not None else sys.modules
    hits = reachable_components(modules)
    return [
        f"component route {route!r} is REACHABLE: module(s) {mods} loaded in-process"
        for route, mods in sorted(hits.items())
    ]


_MISSING_ROUTES = set(COMPONENT_ROUTES) - set(FORBIDDEN_ROUTE_MODULES)
if _MISSING_ROUTES:  # pragma: no cover - config invariant
    raise B0RunError(
        f"FORBIDDEN_ROUTE_MODULES missing routes {sorted(_MISSING_ROUTES)}; "
        "keep it in lockstep with p5_b0_harness.COMPONENT_ROUTES"
    )


# --------------------------------------------------------------------------- #
# Injectable generation backend (must be bindable to the manifest).           #
# --------------------------------------------------------------------------- #
class GenerationBackend(Protocol):
    def descriptor(self) -> Mapping[str, Any]: ...
    def generate(self, prompt: str, decoding: Mapping[str, Any]) -> str: ...
    # Optional: assert_sterile() -> None  (raise if any hook/impurity is present).


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

    def assert_sterile(self) -> None:  # scripted backend has no model/hooks
        return None


# Scorer signature: (probe_id, generation) -> (scorer_input, scorer_output).
# NOT the arbiter (judge of record = Laura HITL); it feeds the null estimator.
Scorer = Callable[[str, str], tuple[Any, Any]]


# --------------------------------------------------------------------------- #
# Digest helpers.                                                             #
# --------------------------------------------------------------------------- #
def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _callable_digest(fn: Callable[..., Any]) -> str:
    """Derive a stable identity for a callable from its SOURCE where available.

    #960 BLOCKER-2: the scorer binding must be a derived code identity, not a caller
    string. Falls back to module+qualname when source is unavailable (C-callable / repl).
    """
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError):
        src = f"{getattr(fn, '__module__', '?')}.{getattr(fn, '__qualname__', repr(fn))}"
    return canonical_digest(src)


def _runner_digest() -> str:
    try:
        return canonical_digest(Path(__file__).read_text(encoding="utf-8"))
    except OSError:  # pragma: no cover - source always present in practice
        return "unknown"


# --------------------------------------------------------------------------- #
# Manifest binding of executed inputs (mandatory + derived).                   #
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


def derive_effective_decoding(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """The EXACT decoding kwargs the runner will pass to ``generate`` — nothing more.

    Only ``do_sample`` and ``max_new_tokens`` are consumed by the backend; anything else
    in the manifest decoding block (e.g. an ignored ``temperature``) is a binding error
    surfaced by ``_bind_execution_to_manifest``.
    """
    dec = manifest.get("decoding", {})
    return {
        "do_sample": bool(dec.get("do_sample", False)),
        "max_new_tokens": int(dec.get("max_new_tokens", 0)),
    }


def _bind_execution_to_manifest(
    manifest: Mapping[str, Any], panel: Sequence[tuple[str, str]],
    backend: GenerationBackend, scorer: Scorer | None, scorer_version: str | None,
    rubric_version: str | None, processor_revision: str | None,
    decoding_hash: str | None, runtime_hash: str | None,
    effective_decoding: Mapping[str, Any], scorer_digest: str | None,
) -> list[str]:
    """Refuse unless EVERY executed input is present and matches the authorized manifest.

    Every binding below is MANDATORY (#960 BLOCKER-2): omitting rubric/processor/decoding/
    runtime no longer returns ok=True. The decoding hash is DERIVED from the exact kwargs
    the backend will consume, and the scorer is bound by a derived code digest.
    """
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
    for key in ("id", "revision", "dtype"):
        if model.get(key) != desc.get(key):
            refusals.append(
                f"backend.{key} {desc.get(key)!r} != manifest model.{key} {model.get(key)!r}"
            )

    # Scorer: mandatory, version-bound, and code-digest-bound (derived).
    scorer_block = manifest.get("scorer", {})
    declared_scorer_version = scorer_block.get("version")
    declared_scorer_code = scorer_block.get("code_digest")
    if scorer is None:
        refusals.append("a scorer is mandatory for a governed B0 run (none supplied)")
    else:
        if scorer_version != declared_scorer_version:
            refusals.append(
                f"scorer_version {scorer_version!r} != manifest scorer.version "
                f"{declared_scorer_version!r}"
            )
        if not declared_scorer_code:
            refusals.append("manifest scorer.code_digest is unset; scorer code is unbound")
        elif scorer_digest != declared_scorer_code:
            refusals.append(
                f"derived scorer code_digest {str(scorer_digest)[:12]}.. != manifest "
                f"scorer.code_digest {str(declared_scorer_code)[:12]}.."
            )

    # Decoding: derived hash of the exact consumed kwargs; deterministic-only; no extras.
    dec_block = manifest.get("decoding", {})
    allowed_dec_keys = {"hash", "max_new_tokens", "do_sample"}
    extra_dec = set(dec_block.keys()) - allowed_dec_keys
    if extra_dec:
        refusals.append(
            f"unsupported decoding fields in manifest (not consumed by generate): "
            f"{sorted(extra_dec)}"
        )
    if effective_decoding["do_sample"]:
        refusals.append("B0 baseline must be deterministic (decoding.do_sample must be False)")
    derived_hash = canonical_digest(dict(effective_decoding))
    if dec_block.get("hash") != derived_hash:
        refusals.append(
            f"manifest decoding.hash {str(dec_block.get('hash'))[:12]}.. != derived hash "
            f"{derived_hash[:12]}.. of the actually-consumed decoding "
            f"{dict(effective_decoding)!r}"
        )
    if decoding_hash is None:
        refusals.append("decoding_hash binding is mandatory (none supplied)")
    elif decoding_hash != derived_hash:
        refusals.append(f"caller decoding_hash {decoding_hash!r} != derived hash {derived_hash!r}")

    # Rubric / processor / runtime: mandatory caller assertions, matched to the manifest.
    for label, value, block, subkey in (
        ("rubric_version", rubric_version, "rubric", "version"),
        ("processor_revision", processor_revision, "processor", "revision"),
        ("runtime_hash", runtime_hash, "runtime", "hash"),
    ):
        declared = manifest.get(block, {}).get(subkey)
        if value is None:
            refusals.append(f"{label} binding is mandatory (none supplied)")
        elif value != declared:
            refusals.append(f"{label} {value!r} != manifest {block}.{subkey} {declared!r}")

    return refusals


# --------------------------------------------------------------------------- #
# Journal reservation (exclusive claim) + no-replace atomic publication.       #
# --------------------------------------------------------------------------- #
def _fsync_parent(directory: Path) -> None:
    if hasattr(os, "O_DIRECTORY"):
        try:
            dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass


def _safe_unlink(path: Path) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def reserve_report_slot(report_path: Path) -> tuple[int, Path]:
    """Exclusively claim a run by O_EXCL-creating its append-only journal.

    Refuses (no-replace) if the report path already exists or is a symlink, and refuses a
    pre-existing/symlinked journal — the journal is BOTH the exclusive claim and the
    append-only custody log (#960 BLOCKER-1/HIGH-3). Returns (journal_fd, journal_path);
    the caller owns the fd and MUST close it.
    """
    report_path = Path(report_path)
    if report_path.exists() or report_path.is_symlink():
        raise B0RunError(
            f"report path already exists (refusing no-replace clobber): {report_path}"
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path = Path(str(report_path) + ".journal")
    if journal_path.is_symlink():
        raise B0RunError(f"journal path is a symlink (refused): {journal_path}")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(journal_path, flags, 0o600)
    except FileExistsError as exc:
        raise B0RunError(f"journal already reserved (prior/colliding run): {journal_path}") from exc
    _fsync_parent(report_path.parent)
    return fd, journal_path


def publish_report_atomic(report: Mapping[str, Any], report_path: Path) -> bytes:
    """Publish the report with a NO-REPLACE atomic primitive and verify the bytes.

    Strict-encode → same-dir O_EXCL temp → flush/fsync → ``os.link`` (atomic, raises if
    the target exists) → fsync parent → re-read and verify identity. Every failure
    propagates; descriptors close in ``finally`` (#960 BLOCKER-1).
    """
    report_path = Path(report_path)
    assert_strict_json(dict(report))
    data = json.dumps(dict(report), indent=2, sort_keys=True, allow_nan=False,
                      ensure_ascii=True).encode("utf-8")
    tmp_path = Path(str(report_path) + f".tmp.{os.getpid()}.{uuid.uuid4().hex}")

    fd = os.open(tmp_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        _safe_unlink(tmp_path)
        raise

    try:
        try:
            os.link(tmp_path, report_path)  # no-replace, atomic on POSIX/NTFS
        except FileExistsError as exc:
            raise B0RunError(
                f"report path appeared before publish (no-replace refused): {report_path}"
            ) from exc
        except (OSError, AttributeError):
            # Platform without cross-file hardlink support: O_EXCL create-and-write.
            wfd = os.open(report_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            try:
                with os.fdopen(wfd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError as exc:
                raise B0RunError(
                    f"report path appeared before publish (no-replace refused): {report_path}"
                ) from exc
    finally:
        _safe_unlink(tmp_path)

    _fsync_parent(report_path.parent)

    published = report_path.read_bytes()
    if published != data:
        raise B0RunError(
            f"published report bytes differ from intended report (third-party swap?): {report_path}"
        )
    return published


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


def _write_journal_event(fd: int, event: Mapping[str, Any]) -> None:
    line = (json.dumps(dict(event), sort_keys=True, allow_nan=False,
                       ensure_ascii=True) + "\n").encode("utf-8")
    os.write(fd, line)
    os.fsync(fd)


def _append_terminal_failure(journal_path: Path, run_id: str, exc: BaseException) -> None:
    """Best-effort durable terminal-failure record; never masks the original error."""
    try:
        with open(journal_path, "a", encoding="utf-8") as journal:
            journal.write(json.dumps({
                "event": "failed", "run_id": run_id,
                "error_type": type(exc).__name__, "error": str(exc)[:500],
                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, sort_keys=True) + "\n")
            journal.flush()
            os.fsync(journal.fileno())
    except OSError:
        pass


def run_b0(
    manifest: Mapping[str, Any],
    panel: Sequence[tuple[str, str]],
    backend: GenerationBackend,
    *,
    scorer: Scorer | None = None,
    scorer_version: str | None = None,
    rubric_version: str | None = None,
    processor_revision: str | None = None,
    decoding_hash: str | None = None,
    runtime_hash: str | None = None,
    report_path: Path | None = None,
) -> B0RunResult:
    """Run a read-only B0 baseline. Refuses (zero forwards) on ANY gate violation.

    Fail-closed order:
      1. authorize the manifest (deny-by-default gate),
      2. assert no component module reachable in the LIVE process,
      3. whole-panel pre-validation,
      4. MANDATORILY bind every executed input (panel/backend/scorer/decoding/rubric/
         processor/runtime) to the authorized manifest, with derived hashes,
      5. resolve + exclusively RESERVE the append-only journal (no-replace) before forward,
      6. per probe: journal a uniquely-identified attempt, assert the backend is sterile,
         generate, RE-assert no component became reachable during the forward, record,
      7. seal, finalize ALL report fields, compute the published digest over the exact
         report, publish with a no-replace atomic primitive, verify the bytes, and write a
         durable terminal event. Any post-reservation failure writes a terminal failure
         event and propagates (no partial sealed report).
    """
    decision = authorize_b0_launch(manifest)
    refusals = list(decision.refusals)
    refusals.extend(assert_no_component_reachable())               # live sys.modules
    refusals.extend(_validate_panel(panel))

    effective_decoding = derive_effective_decoding(manifest)
    scorer_digest = _callable_digest(scorer) if scorer is not None else None
    if not refusals:
        refusals.extend(
            _bind_execution_to_manifest(
                manifest, panel, backend, scorer, scorer_version,
                rubric_version, processor_revision, decoding_hash, runtime_hash,
                effective_decoding, scorer_digest,
            )
        )

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
    journal_fd, journal_path = reserve_report_slot(resolved_path)   # O_EXCL, pre-forward
    run_id = uuid.uuid4().hex
    runner_digest = _runner_digest()
    bundle = B0EvidenceBundle(manifest_digest=decision.manifest_digest or "")

    execution_descriptor = {
        "panel_hash": canonical_panel_hash(panel),
        "model": dict(backend.descriptor()),
        "decoding": dict(effective_decoding),
        "decoding_hash": canonical_digest(dict(effective_decoding)),
        "scorer_version": scorer_version,
        "scorer_code_digest": scorer_digest,
        "rubric_version": rubric_version,
        "processor_revision": processor_revision,
        "runtime_hash": runtime_hash,
        "runner_digest": runner_digest,
        "manifest_digest": decision.manifest_digest,
    }

    try:
        _write_journal_event(journal_fd, {
            "event": "claim", "run_id": run_id, "run_kind": "b0_baseline",
            "manifest_digest": decision.manifest_digest, "runner_digest": runner_digest,
            "runtime_hash": runtime_hash, "execution_descriptor_digest":
                canonical_digest(execution_descriptor),
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        for ordinal, (probe_id, prompt) in enumerate(panel):
            attempt_id = f"{run_id}:{ordinal}"
            _write_journal_event(journal_fd, {
                "event": "attempt", "attempt_id": attempt_id, "ordinal": ordinal,
                "probe_id": probe_id, "prompt_sha256": canonical_digest(prompt),
                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            sterile = getattr(backend, "assert_sterile", None)
            if callable(sterile):
                sterile()                                          # raise on any hook
            generation = backend.generate(prompt, dict(effective_decoding))  # governed forward
            _write_journal_event(journal_fd, {
                "event": "generated", "attempt_id": attempt_id, "ordinal": ordinal,
                "probe_id": probe_id, "generation_sha256": canonical_digest(generation),
                "generation": generation,
            })
            late = assert_no_component_reachable()                 # late-import re-check
            if late:
                raise B0RunError(
                    "a component became REACHABLE during the governed forward: " + "; ".join(late)
                )
            scorer_input, scorer_output = (None, None)
            if scorer is not None:
                scorer_input, scorer_output = scorer(probe_id, generation)
            bundle.record(                                         # strict-JSON enforced here
                probe_id, generation,
                scorer_input=scorer_input, scorer_output=scorer_output,
                provenance={"prompt_sha256": canonical_digest(prompt), "attempt_id": attempt_id},
            )
            _write_journal_event(journal_fd, {
                "event": "recorded", "attempt_id": attempt_id, "ordinal": ordinal,
                "probe_id": probe_id,
            })

        report = bundle.seal()
        report["run_kind"] = "b0_baseline"
        report["manifest_digest"] = decision.manifest_digest
        report["execution_descriptor"] = execution_descriptor
        report["published_digest"] = canonical_digest(
            {k: v for k, v in report.items() if k != "published_digest"}
        )
        published = publish_report_atomic(report, resolved_path)
        _write_journal_event(journal_fd, {
            "event": "completed", "run_id": run_id,
            "published_digest": report["published_digest"],
            "report_bytes_sha256": _sha256_bytes(published),
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
    except BaseException as exc:
        os.close(journal_fd)
        _append_terminal_failure(journal_path, run_id, exc)
        raise
    else:
        os.close(journal_fd)

    return B0RunResult(
        ok=True, refusals=(), report=report,
        report_path=str(resolved_path), published_digest=report["published_digest"],
    )


# --------------------------------------------------------------------------- #
# Real HF backend (torch; ML-WS). Imported lazily; registers NO hooks.        #
# --------------------------------------------------------------------------- #
_DTYPE_ALIASES = {
    "bfloat16": "bf16", "bf16": "bf16",
    "float16": "fp16", "fp16": "fp16", "half": "fp16",
    "float32": "fp32", "fp32": "fp32", "float": "fp32",
}


def _normalize_dtype(raw: Any) -> str:
    key = str(raw).replace("torch.", "").strip().lower()
    return _DTYPE_ALIASES.get(key, key)


class HFGenerationBackend:
    """Read-only Gemma-base generation. NO injection hooks, NO components.

    Exposes ``descriptor`` (bound to the manifest by run_b0), ``generate``, and
    ``assert_sterile`` (refuses if any forward/pre/backward hook is registered anywhere on
    the model). Registers nothing itself, so a B0 forward is a plain frozen forward. Only
    exercised on ML-WS. dtype is normalized to the manifest spelling (bf16/fp16/fp32) and
    the ACTUAL loaded dtype is what ``descriptor`` reports — no self-refusing mismatch.
    """

    def __init__(self, model_id: str, revision: str, *, dtype: str = "bf16",
                 local_files_only: bool = True, max_new_tokens: int = 256):
        from transformers import (  # type: ignore
            AutoModelForImageTextToText, AutoProcessor,
        )

        self._torch = __import__("torch")
        self._model_id = model_id
        self._revision = revision
        self._requested_dtype = _normalize_dtype(dtype)
        torch_dtype = {
            "bf16": self._torch.bfloat16,
            "fp16": self._torch.float16,
            "fp32": self._torch.float32,
        }.get(self._requested_dtype)
        if torch_dtype is None:
            raise B0RunError(f"unsupported dtype for B0: {dtype!r}")
        self.processor = AutoProcessor.from_pretrained(
            model_id, revision=revision, trust_remote_code=True,
            local_files_only=local_files_only,
        )
        self.model = AutoModelForImageTextToText.from_pretrained(
            model_id, revision=revision, trust_remote_code=True,
            torch_dtype=torch_dtype, device_map="auto",
            local_files_only=local_files_only,
        )
        self.model.eval()
        self.max_new_tokens = max_new_tokens

    def descriptor(self) -> Mapping[str, Any]:
        return {
            "id": self._model_id,
            "revision": self._revision,
            "dtype": _normalize_dtype(self.model.dtype),  # the ACTUAL loaded dtype
        }

    def assert_sterile(self) -> None:
        """Refuse if any hook is registered anywhere on the model (B0 = no needle)."""
        for module in self.model.modules():
            for attr in ("_forward_hooks", "_forward_pre_hooks", "_backward_hooks"):
                hooks = getattr(module, attr, None)
                if hooks:
                    raise B0RunError(
                        f"non-sterile model: {attr} present on {type(module).__name__}"
                    )

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
