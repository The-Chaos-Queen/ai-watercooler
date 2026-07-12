"""P5 B0 runner — the read-only baseline harness on top of the deny-by-default gate.

OpenCLAW #156, slice 4 (the B0 HF path). Supersedes e2a79e6, hardened against wolf-Codex
review of record #966 (MoCoP/reviews/p5_b0_runner_review_2026-07-12.md). Turns
``p5_b0_harness`` (the model-free launch gate) into a runnable baseline:

  * authorize the manifest (deny-by-default),
  * assert no component module is REACHABLE in the live process — before AND after every
    forward AND scorer, plus a process-wide import-audit sentinel that catches a component
    imported-and-removed transiently inside a single forward,
  * MANDATORILY bind every executed input with DERIVED hashes: panel, backend descriptor
    (incl. backend/device/attention/use_cache), a closure-aware scorer digest, the derived
    decoding hash, rubric/processor/runtime, and the runner's OWN source digest against an
    authorized manifest value,
  * require a bound sterility contract on the backend (no optional bypass),
  * publish via a two-phase terminal transaction: an O_EXCL append-only journal whose
    pathname identity is inode-verified, a no-replace atomic report publication with byte
    verification, and a report that binds the journal digest + terminal state so report
    existence and journal state cannot disagree.

House style: orchestration + reachability guard are torch-free and model-free-testable
behind a ``GenerationBackend`` Protocol. Only ``HFGenerationBackend`` imports torch/loads
Gemma, and it registers NO hooks (B0 is read-only, no needle).

HONEST SCOPE (told Codex, still open, NOT closed here): a self-reporting backend can lie
about the artifacts it loaded — real cryptographic verification of the resolved model /
processor / device map / attention artifacts is the SEPARATE read-only HF audit. And the
#149 stage-neutral base-manifest / per-attempt schema reconciliation is a separate launch
block. Runner GREEN alone never authorizes #155.
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
# Reviewed EXACT forbidden-module inventory (#960 HIGH-4 / #966 HIGH-4).        #
# --------------------------------------------------------------------------- #
# Matching is EXACT equality against a loaded/importing module's top-level package name OR
# its full basename (last dotted segment) — NEVER a substring. Exact equality
# simultaneously (a) catches external component packages in site-packages
# (``qdrant_client``, ``mamba_ssm``) that a ``__file__``-path heuristic misses, and
# (b) refuses to false-fire on framework internals like ``torch.cuda.memory`` (basename
# ``memory`` is NOT inventoried; the real module is ``memory_engine`` /
# ``dense_associative_memory`` / ...). Reviewed against the repo's real component modules
# AND the named ``Projects.Project_Prosthetic.memory_engine`` route (#966). A new component
# MUST be added here or B0's no-component guarantee silently weakens (lockstep enforced).
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
        "memory_engine", "memory_evidence", "dense_associative_memory",
        "autobiographical_memory", "lesson_memory", "lesson_memory_cli",
        "d2_memory_legibility_eval", "exocortex_mcp_server", "Project_Prosthetic",
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


def _forbidden_route_for(name: str) -> str | None:
    """Return the route a module NAME falls under, by exact top-level/basename equality."""
    if not isinstance(name, str) or not name:
        return None
    top = name.split(".", 1)[0]
    base = name.rsplit(".", 1)[-1]
    for route, forbidden in FORBIDDEN_ROUTE_MODULES.items():
        if name in forbidden or top in forbidden or base in forbidden:
            return route
    return None


# --------------------------------------------------------------------------- #
# Reachability guard — snapshot (sys.modules) + audit sentinel (transient).     #
# --------------------------------------------------------------------------- #
def reachable_components(loaded_modules: Mapping[str, Any]) -> dict[str, list[str]]:
    """Return {route: [matched module names]} for any component reachable in-process.

    Matches by NAME (a ``None`` value in ``sys.modules`` — an attempted import — still
    counts; presence of the NAME is reachability, fail-closed).
    """
    hits: dict[str, list[str]] = {}
    for name in loaded_modules.keys():
        route = _forbidden_route_for(name)
        if route:
            bucket = hits.setdefault(route, [])
            if name not in bucket:
                bucket.append(name)
    for v in hits.values():
        v.sort()
    return hits


def assert_no_component_reachable(loaded_modules: Mapping[str, Any] | None = None) -> list[str]:
    """Refusal reasons if any component module is loaded (empty = clean).

    ``loaded_modules`` is a TEST/helper seam only; ``run_b0`` inspects live ``sys.modules``.
    """
    modules = loaded_modules if loaded_modules is not None else sys.modules
    hits = reachable_components(modules)
    return [
        f"component route {route!r} is REACHABLE: module(s) {mods} loaded in-process"
        for route, mods in sorted(hits.items())
    ]


# Process-wide import-audit sentinel: catches a forbidden module imported AND removed
# transiently inside one forward, which a before/after sys.modules snapshot misses (#966).
_forbidden_imports: list[str] = []
_audit_installed = False


def _import_audit_hook(event: str, args: tuple) -> None:
    if event == "import" and args:
        route = _forbidden_route_for(args[0]) if isinstance(args[0], str) else None
        if route:
            _forbidden_imports.append(args[0])


def _ensure_import_audit() -> None:
    global _audit_installed
    if not _audit_installed:
        try:
            sys.addaudithook(_import_audit_hook)
        except Exception:  # pragma: no cover - audit hooks unavailable
            pass
        _audit_installed = True


def _clear_import_sentinel() -> None:
    _forbidden_imports.clear()


def _drain_import_sentinel() -> list[str]:
    seen = sorted(set(_forbidden_imports))
    _forbidden_imports.clear()
    return seen


_MISSING_ROUTES = set(COMPONENT_ROUTES) - set(FORBIDDEN_ROUTE_MODULES)
if _MISSING_ROUTES:  # pragma: no cover - config invariant
    raise B0RunError(
        f"FORBIDDEN_ROUTE_MODULES missing routes {sorted(_MISSING_ROUTES)}; "
        "keep it in lockstep with p5_b0_harness.COMPONENT_ROUTES"
    )


# --------------------------------------------------------------------------- #
# Injectable generation backend (must be bindable + prove sterility).          #
# --------------------------------------------------------------------------- #
class GenerationBackend(Protocol):
    def descriptor(self) -> Mapping[str, Any]: ...
    def generate(self, prompt: str, decoding: Mapping[str, Any]) -> str: ...
    def assert_sterile(self) -> None: ...  # MANDATORY: raise if any hook/impurity present.


# Descriptor fields the runner binds against the manifest model block.
DESCRIPTOR_KEYS = ("id", "revision", "dtype", "backend", "device", "attention", "use_cache")


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
Scorer = Callable[[str, str], tuple[Any, Any]]


# --------------------------------------------------------------------------- #
# Digest helpers.                                                             #
# --------------------------------------------------------------------------- #
def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _callable_digest(fn: Callable[..., Any]) -> str:
    """Derive a scorer identity from SOURCE + closure state + defaults + qualname (#966).

    Two callables with identical source but different captured closure state MUST get
    different digests, or the scorer binding is behaviorally blind.
    """
    parts: dict[str, Any] = {
        "module": getattr(fn, "__module__", None),
        "qualname": getattr(fn, "__qualname__", None),
        "defaults": repr(getattr(fn, "__defaults__", None)),
        "kwdefaults": repr(getattr(fn, "__kwdefaults__", None)),
    }
    try:
        parts["source"] = inspect.getsource(fn)
    except (OSError, TypeError):
        parts["source"] = None
    closure = getattr(fn, "__closure__", None)
    if closure:
        cells = []
        for cell in closure:
            try:
                cells.append(repr(cell.cell_contents))
            except ValueError:
                cells.append("<empty-cell>")
        parts["closure"] = cells
    return canonical_digest(parts)


def _runner_digest() -> str:
    try:
        return canonical_digest(Path(__file__).read_text(encoding="utf-8"))
    except OSError:  # pragma: no cover - source always present in practice
        return "unknown"


# --------------------------------------------------------------------------- #
# Manifest binding of executed inputs (mandatory + derived).                    #
# --------------------------------------------------------------------------- #
def _validate_panel(panel: Sequence[Any]) -> list[str]:
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
    """The EXACT decoding kwargs the runner passes to ``generate`` — nothing more."""
    dec = manifest.get("decoding", {})
    return {
        "do_sample": bool(dec.get("do_sample", False)),
        "max_new_tokens": int(dec.get("max_new_tokens", 0)),
    }


def _bind_execution_to_manifest(
    manifest: Mapping[str, Any], panel: Sequence[tuple[str, str]],
    descriptor: Mapping[str, Any], scorer: Scorer | None, scorer_version: str | None,
    rubric_version: str | None, processor_revision: str | None,
    decoding_hash: str | None, runtime_hash: str | None,
    effective_decoding: Mapping[str, Any], scorer_digest: str | None,
    sterile_bound: bool,
) -> list[str]:
    """Refuse unless EVERY executed input is present and matches the authorized manifest."""
    refusals: list[str] = []

    declared_panel = manifest.get("panel", {}).get("hash")
    actual_panel = canonical_panel_hash(panel)
    if declared_panel != actual_panel:
        refusals.append(
            f"executed panel hash {actual_panel[:12]}.. != manifest panel.hash "
            f"{str(declared_panel)[:12]}.. (unbound panel)"
        )

    model = manifest.get("model", {})
    for key in DESCRIPTOR_KEYS:
        if key not in descriptor:
            refusals.append(f"backend descriptor omits required field {key!r}")
        elif model.get(key) != descriptor.get(key):
            refusals.append(
                f"backend.{key} {descriptor.get(key)!r} != manifest model.{key} {model.get(key)!r}"
            )

    # Sterility contract is MANDATORY (no optional bypass).
    if not sterile_bound:
        refusals.append("backend does not expose a sterility contract (assert_sterile required)")

    # Runner authorization: this runner's own source digest must match the manifest.
    declared_runner = manifest.get("runtime", {}).get("runner_digest")
    actual_runner = _runner_digest()
    if not declared_runner:
        refusals.append("manifest runtime.runner_digest is unset; runner is unauthorized")
    elif actual_runner != declared_runner:
        refusals.append("runner_digest mismatch: this runner is not the authorized one")

    # Scorer: mandatory, version-bound, closure-aware code-digest-bound.
    scorer_block = manifest.get("scorer", {})
    if scorer is None:
        refusals.append("a scorer is mandatory for a governed B0 run (none supplied)")
    else:
        if scorer_version != scorer_block.get("version"):
            refusals.append(
                f"scorer_version {scorer_version!r} != manifest scorer.version "
                f"{scorer_block.get('version')!r}"
            )
        declared_scorer_code = scorer_block.get("code_digest")
        if not declared_scorer_code:
            refusals.append("manifest scorer.code_digest is unset; scorer code is unbound")
        elif scorer_digest != declared_scorer_code:
            refusals.append(
                f"derived scorer code_digest {str(scorer_digest)[:12]}.. != manifest "
                f"scorer.code_digest {str(declared_scorer_code)[:12]}.."
            )

    # Decoding: derived hash of the exact consumed kwargs; deterministic-only; no extras.
    dec_block = manifest.get("decoding", {})
    extra_dec = set(dec_block.keys()) - {"hash", "max_new_tokens", "do_sample"}
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
            f"{derived_hash[:12]}.. of the actually-consumed decoding {dict(effective_decoding)!r}"
        )
    if decoding_hash is None:
        refusals.append("decoding_hash binding is mandatory (none supplied)")
    elif decoding_hash != derived_hash:
        refusals.append(f"caller decoding_hash {decoding_hash!r} != derived hash {derived_hash!r}")

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
# Durable low-level IO.                                                        #
# --------------------------------------------------------------------------- #
def _write_all(fd: int, data: bytes) -> None:
    """os.write can short-write; loop until every byte lands (#966 HIGH-3)."""
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written <= 0:  # pragma: no cover - defensive
            raise B0RunError("os.write made no progress")
        view = view[written:]


def _fsync_parent(directory: Path) -> None:
    """fsync the namespace. On POSIX this PROPAGATES failure (no swallow, #966 HIGH-3)."""
    if hasattr(os, "O_DIRECTORY"):
        dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)


def _safe_unlink(path: Path) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# The owned append-only journal (exclusive claim + inode-verified custody).     #
# --------------------------------------------------------------------------- #
class _Journal:
    """An O_EXCL-owned append-only journal whose pathname identity is verifiable."""

    def __init__(self, fd: int, path: Path):
        self._fd = fd
        self._path = path
        self._hash = hashlib.sha256()
        self._closed = False

    def event(self, obj: Mapping[str, Any]) -> None:
        line = (json.dumps(dict(obj), sort_keys=True, allow_nan=False,
                           ensure_ascii=True) + "\n").encode("utf-8")
        _write_all(self._fd, line)
        os.fsync(self._fd)
        self._hash.update(line)

    def verify_identity(self) -> None:
        """Refuse if the pathname no longer refers to our owned inode (swap detected)."""
        st_fd = os.fstat(self._fd)
        try:
            st_path = os.stat(self._path)
        except OSError as exc:
            raise B0RunError(f"journal pathname vanished mid-run: {exc}") from exc
        if (st_fd.st_ino, st_fd.st_dev) != (st_path.st_ino, st_path.st_dev):
            raise B0RunError(
                "journal pathname no longer refers to the owned descriptor (swap detected)"
            )

    def digest(self) -> str:
        return self._hash.hexdigest()

    @property
    def fd_open(self) -> bool:
        return not self._closed

    def close(self) -> None:
        if not self._closed:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._closed = True


def reserve_report_slot(report_path: Path) -> _Journal:
    """Exclusively claim a run by O_EXCL-creating its append-only journal.

    Refuses (no-replace) if the report leaf exists or is a symlink; refuses a pre-existing/
    symlinked journal; and REQUIRES the protected parent directory to already exist — the
    runner does NOT mkdir it (#966 HIGH-5: the predeclared protected sink is not a new
    mutable directory the runner creates).
    """
    report_path = Path(report_path)
    if report_path.exists() or report_path.is_symlink():
        raise B0RunError(f"report path already exists (refusing no-replace clobber): {report_path}")
    parent = report_path.parent
    if not parent.is_dir():
        raise B0RunError(
            f"protected evidence-sink parent does not exist (must be predeclared, not "
            f"runner-created): {parent}"
        )
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
    _fsync_parent(parent)
    return _Journal(fd, journal_path)


def publish_report_atomic(report: Mapping[str, Any], report_path: Path) -> bytes:
    """Publish with a NO-REPLACE atomic primitive and verify the bytes (#966 HIGH-3).

    Strict-encode → same-dir O_EXCL temp → flush/fsync → ``os.link`` (atomic, raises if the
    target exists) → fsync parent → re-read and verify identity. NO in-place fallback: if
    the atomic primitive is unavailable the run FAILS rather than downgrading to a visible
    in-place write. Every failure propagates; descriptors close in ``finally``.
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
        except OSError as exc:
            raise B0RunError(
                f"atomic no-replace publication unavailable, refusing in-place downgrade: {exc}"
            ) from exc
    finally:
        _safe_unlink(tmp_path)

    _fsync_parent(report_path.parent)  # propagates durability failure

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


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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
    """Run a read-only B0 baseline. Refuses (zero forwards) on ANY gate violation."""
    _ensure_import_audit()
    decision = authorize_b0_launch(manifest)
    refusals = list(decision.refusals)
    refusals.extend(assert_no_component_reachable())               # live sys.modules
    refusals.extend(_validate_panel(panel))

    # ONE descriptor call, captured for both binding and the sealed audit record.
    descriptor = dict(backend.descriptor())
    sterile_bound = callable(getattr(backend, "assert_sterile", None))
    effective_decoding = derive_effective_decoding(manifest)
    scorer_digest = _callable_digest(scorer) if scorer is not None else None
    if not refusals:
        refusals.extend(
            _bind_execution_to_manifest(
                manifest, panel, descriptor, scorer, scorer_version,
                rubric_version, processor_revision, decoding_hash, runtime_hash,
                effective_decoding, scorer_digest, sterile_bound,
            )
        )

    sink_path = manifest.get("evidence_sink", {}).get("path")
    resolved_path: Path | None = None
    if not refusals:
        if report_path is not None and str(report_path) != str(sink_path):
            refusals.append(f"report_path {report_path} != manifest evidence_sink.path {sink_path}")
        elif not sink_path:
            refusals.append("manifest evidence_sink.path is unset; cannot bind evidence")
        else:
            resolved_path = Path(report_path if report_path is not None else sink_path)

    if refusals:
        return B0RunResult(False, tuple(refusals), None, None, None)

    assert resolved_path is not None
    journal = reserve_report_slot(resolved_path)                   # O_EXCL, pre-forward
    run_id = uuid.uuid4().hex
    published_ok = False
    report: dict[str, Any] | None = None
    try:
        execution_descriptor = {
            "panel_hash": canonical_panel_hash(panel),
            "model": descriptor,
            "decoding": dict(effective_decoding),
            "decoding_hash": canonical_digest(dict(effective_decoding)),
            "scorer_version": scorer_version,
            "scorer_code_digest": scorer_digest,
            "rubric_version": rubric_version,
            "processor_revision": processor_revision,
            "runtime_hash": runtime_hash,
            "runner_digest": _runner_digest(),
            "manifest_digest": decision.manifest_digest,
        }
        bundle = B0EvidenceBundle(manifest_digest=decision.manifest_digest or "")
        journal.event({
            "event": "claim", "run_id": run_id, "run_kind": "b0_baseline",
            "manifest_digest": decision.manifest_digest,
            "execution_descriptor_digest": canonical_digest(execution_descriptor),
            "utc": _now(),
        })

        for ordinal, (probe_id, prompt) in enumerate(panel):
            attempt_id = f"{run_id}:{ordinal}"
            journal.event({
                "event": "attempt", "attempt_id": attempt_id, "ordinal": ordinal,
                "probe_id": probe_id, "prompt_sha256": canonical_digest(prompt), "utc": _now(),
            })
            # Reachability + sterility BEFORE the forward (catches a prior scorer's import).
            pre = assert_no_component_reachable()
            if pre:
                raise B0RunError("component REACHABLE before governed forward: " + "; ".join(pre))
            backend.assert_sterile()
            _clear_import_sentinel()

            generation = backend.generate(prompt, dict(effective_decoding))  # governed forward

            transient = _drain_import_sentinel()
            post = assert_no_component_reachable()
            if transient:
                raise B0RunError("component IMPORTED during governed forward: " + "; ".join(transient))
            if post:
                raise B0RunError("component REACHABLE after governed forward: " + "; ".join(post))
            journal.event({
                "event": "generated", "attempt_id": attempt_id, "ordinal": ordinal,
                "probe_id": probe_id, "generation_sha256": canonical_digest(generation),
                "generation": generation,
            })

            scorer_input, scorer_output = (None, None)
            if scorer is not None:
                scorer_input, scorer_output = scorer(probe_id, generation)
            # Reachability after the scorer too (a scorer must not wake a component).
            scorer_transient = _drain_import_sentinel()
            scorer_post = assert_no_component_reachable()
            if scorer_transient or scorer_post:
                raise B0RunError(
                    "component reachable via scorer: " + "; ".join(scorer_transient + scorer_post)
                )
            bundle.record(                                         # strict-JSON enforced here
                probe_id, generation,
                scorer_input=scorer_input, scorer_output=scorer_output,
                provenance={"prompt_sha256": canonical_digest(prompt), "attempt_id": attempt_id},
            )
            journal.event({
                "event": "recorded", "attempt_id": attempt_id, "ordinal": ordinal,
                "probe_id": probe_id,
            })

        # ---- Two-phase terminal transaction: report binds journal digest + state. ----
        report = bundle.seal()
        report["run_kind"] = "b0_baseline"
        report["manifest_digest"] = decision.manifest_digest
        report["execution_descriptor"] = execution_descriptor
        report["terminal_state"] = "completed"
        report["journal_digest"] = journal.digest()                # over all events so far
        report["published_digest"] = canonical_digest(
            {k: v for k, v in report.items() if k != "published_digest"}
        )
        journal.verify_identity()                                  # inode still ours?
        journal.event({
            "event": "sealing", "run_id": run_id,
            "published_digest": report["published_digest"],
            "journal_digest_prefix": report["journal_digest"], "utc": _now(),
        })
        published = publish_report_atomic(report, resolved_path)   # raises on ANY failure
        published_ok = True
        # Publication succeeded => the run is COMPLETE. A failure to durably append the
        # completed marker is a best-effort durability note, NOT a run failure — the report
        # is valid and binds terminal_state=completed, so state cannot say 'failed'.
        try:
            journal.event({
                "event": "completed", "run_id": run_id,
                "published_digest": report["published_digest"],
                "report_bytes_sha256": _sha256_bytes(published), "utc": _now(),
            })
        except OSError:
            pass
    except BaseException as exc:
        if not published_ok and journal.fd_open:
            try:                                                   # via the OWNED fd (no reopen)
                journal.event({
                    "event": "failed", "run_id": run_id,
                    "error_type": type(exc).__name__, "error": str(exc)[:500], "utc": _now(),
                })
            except OSError:
                pass
        raise
    finally:
        journal.close()

    assert report is not None
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

    NOTE (honest scope): ``descriptor`` self-reports from the loaded objects; it does NOT
    cryptographically verify the resolved artifact/processor/device against a trusted
    registry — that is the SEPARATE read-only HF audit. ``assert_sterile`` refuses if any
    per-module OR torch GLOBAL hook registry is non-empty (#966).
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
        cfg = getattr(self.model, "config", None)
        return {
            "id": self._model_id,
            "revision": self._revision,
            "dtype": _normalize_dtype(self.model.dtype),
            "backend": type(self.model).__name__,
            "device": str(next(self.model.parameters()).device),
            "attention": getattr(cfg, "_attn_implementation", "unknown"),
            "use_cache": bool(getattr(cfg, "use_cache", True)),
        }

    def assert_sterile(self) -> None:
        """Refuse if ANY per-module or torch GLOBAL hook registry is non-empty."""
        from torch.nn.modules import module as _m  # type: ignore
        for reg in ("_global_forward_hooks", "_global_forward_pre_hooks",
                    "_global_backward_hooks", "_global_backward_pre_hooks"):
            if getattr(_m, reg, None):
                raise B0RunError(f"non-sterile: torch global {reg} is non-empty")
        for module in self.model.modules():
            for attr in ("_forward_hooks", "_forward_pre_hooks",
                         "_backward_hooks", "_backward_pre_hooks"):
                if getattr(module, attr, None):
                    raise B0RunError(f"non-sterile: {attr} present on {type(module).__name__}")

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
