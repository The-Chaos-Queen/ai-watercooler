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
    _is_unset,  # the placeholder-aware unset check (rejects "tbd"/"none"/"[tbd:"/...)
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


def _ensure_import_audit() -> bool:
    """Install the transient-import sentinel. Returns False if it could NOT be armed, so the
    caller can fail CLOSED (#966 HIGH-4) rather than run with a silently-disabled sentinel.
    """
    global _audit_installed
    if not _audit_installed:
        try:
            sys.addaudithook(_import_audit_hook)
        except Exception:  # pragma: no cover - audit hooks unavailable
            return False
        _audit_installed = True
    return _audit_installed


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


# A B0 scorer may capture/reference only DEEPLY IMMUTABLE values (#980 scorer BLOCKER).
# repr() is NOT identity: a mutable object with the default address-based repr (or a mutable
# container holding such an object) keeps a stable repr while its state changes, so binding by
# repr is blind to the mutation. Immutable values have no such gap — their repr IS their value.
_IMMUTABLE_ATOMS = (bool, int, float, str, bytes, type(None))


def _is_deeply_immutable(value: Any) -> bool:
    if isinstance(value, _IMMUTABLE_ATOMS):
        return True
    if isinstance(value, (frozenset, tuple)):
        return all(_is_deeply_immutable(v) for v in value)
    return False                                            # list/dict/set/instance/module/etc


def _callable_digest(fn: Callable[..., Any]) -> str:
    """Derive a scorer identity from source + closure + defaults + referenced DATA globals.

    Two callables that differ in source, captured closure state, default args, OR the
    current value of any module-level DATA global they read get different digests (#966
    BLOCKER-3). Code globals (modules/functions/classes/builtins) are excluded — they are
    identity already captured by source, and their ``repr`` is not process-stable. This does
    not make behavior fully decidable (a function can reach state transitively), which is
    why the scorer is ALSO constrained to a plain reviewed function; but it closes the named
    mutable-global / data-dependency collision so a mutated global re-derives a new digest
    that no longer matches the manifest's pinned ``scorer.code_digest``.
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
    code = getattr(fn, "__code__", None)
    g = getattr(fn, "__globals__", {})
    if code is not None:
        referenced: dict[str, str] = {}
        for name in getattr(code, "co_names", ()):
            if name in g and _is_deeply_immutable(g[name]):     # repr of an immutable IS its value
                referenced[name] = repr(g[name])
        if referenced:
            parts["referenced_globals"] = referenced
    return canonical_digest(parts)


def _runner_digest() -> str:
    try:
        return canonical_digest(Path(__file__).read_text(encoding="utf-8"))
    except OSError:  # pragma: no cover - source always present in practice
        return "unknown"


def _scorer_selfcontained_refusals(fn: Callable[..., Any]) -> list[str]:
    """Refuse a scorer that captures/reaches state the digest cannot soundly bind (#980).

    A B0 scorer must be SELF-CONTAINED over DEEPLY IMMUTABLE state: every module-level name it
    references, every closure cell it captures, and every default argument must be deeply
    immutable. Mutable containers, class/module/instance references, and helpers are refused —
    they carry state a ``repr`` digest cannot detect a change in (repr is not identity). With
    only immutable captured state there is nothing to mutate mid-run, so the digest binding is
    sound. Builtins (``len``) live in ``builtins``, not the module ``__globals__``, so they are
    unaffected. Pre-attested pure helpers would need an explicit allowlist.
    """
    code = getattr(fn, "__code__", None)
    g = getattr(fn, "__globals__", {})
    if code is None:
        return ["scorer has no __code__ (cannot bind its behavior)"]
    refusals: list[str] = []

    bad_globals = sorted({name for name in code.co_names
                          if name in g and not _is_deeply_immutable(g[name])})
    if bad_globals:
        refusals.append(
            f"scorer references module-level name(s) {bad_globals} whose value is not deeply "
            "immutable; a B0 scorer may reference only builtins and immutable own data "
            "(mutable containers / helpers / classes / modules / instances carry unbindable "
            "state — repr is not identity).")

    bad_cells = [i for i, cell in enumerate(getattr(fn, "__closure__", None) or ())
                 if _cell_is_mutable(cell)]
    if bad_cells:
        refusals.append(
            f"scorer closure captures mutable/unbindable state at cell(s) {bad_cells}; a B0 "
            "scorer may close over only deeply-immutable values.")

    defaults = list(getattr(fn, "__defaults__", None) or ())
    defaults += list((getattr(fn, "__kwdefaults__", None) or {}).values())
    if any(not _is_deeply_immutable(d) for d in defaults):
        refusals.append(
            "scorer has a non-immutable default argument; use only immutable defaults so "
            "captured state cannot mutate mid-run.")

    return refusals


def _cell_is_mutable(cell: Any) -> bool:
    try:
        return not _is_deeply_immutable(cell.cell_contents)
    except ValueError:                                          # empty cell: nothing captured
        return False


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


def check_protected_sink_attestation(manifest: Mapping[str, Any]) -> list[str]:
    """Refuse pre-run unless the protected-sink OS contract is ATTESTED in the manifest.

    Codex boundary ruling (#971): the runner may rely on an OS protected-sink contract
    (append-only/immutable file + locked-down dir) to PREVENT hostile same-UID mutation,
    but its absence must be a pre-run refusal, not a silent assumption. The manifest must
    carry a signed, reviewed attestation that the contract is provisioned. Placeholder tokens
    ("TBD"/"none"/"[tbd: ...]") are rejected via the harness's ``_is_unset`` (#966 round-6).

    NOTE (trust boundary): this binds PRESENCE of a non-placeholder signer/review_ref, not
    the identity of the sink path / ACL / immutability. Cross-checking the attestation
    against the real filesystem ACL/inode is the deployment contract, not model-free-closable.
    """
    sink = manifest.get("evidence_sink", {})
    if not isinstance(sink, Mapping):
        return ["evidence_sink missing or not a mapping"]
    att = sink.get("protected_sink_attestation")
    if not isinstance(att, Mapping):
        return ["evidence_sink.protected_sink_attestation missing; the protected-sink OS contract "
                "must be attested before a governed B0 run"]
    refusals: list[str] = []
    if _is_unset(att.get("signer")):
        refusals.append("protected_sink_attestation.signer missing/placeholder")
    if _is_unset(att.get("review_ref")):
        refusals.append("protected_sink_attestation.review_ref missing/placeholder")
    if not _is_sha256(att.get("digest")):
        # #980: an arbitrary non-placeholder string ('x') is not an attestation. Require at least
        # a sha256-format content digest and a binding to the actual sink path — a structural bar
        # only. Whether the signer/digest is genuinely RESOLVABLE (a real reviewer, a verifiable
        # signature) is a THIRD launch hold owned by a separate reviewed attestation contract,
        # alongside #149 and the HF audit; it does not fold behind them.
        refusals.append("protected_sink_attestation.digest missing or not a sha256 (a resolvable "
                        "signed/digested attestation is required, not an arbitrary string)")
    if att.get("bound_path") != sink.get("path"):
        refusals.append("protected_sink_attestation.bound_path does not bind evidence_sink.path")
    return refusals


def _is_sha256(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value.lower()))


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
            continue
        dval = descriptor.get(key)
        if dval is None or (isinstance(dval, str) and not dval.strip()):
            refusals.append(f"backend descriptor field {key!r} is null/empty (must be pinned)")
            continue
        mval = model.get(key)
        if mval is None or (isinstance(mval, str) and not mval.strip()):
            refusals.append(f"manifest model.{key} is null/empty (must be pinned)")
        elif mval != dval:
            refusals.append(f"backend.{key} {dval!r} != manifest model.{key} {mval!r}")

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
    elif not inspect.isfunction(scorer):
        # #966 BLOCKER-3: a code digest cannot bind arbitrary callable behavior. Constrain
        # the scorer to a plain function so source + closure + defaults + referenced data
        # globals bind its behavior; callable instances / functools.partial / bound methods
        # carry unbindable runtime state.
        refusals.append(
            "scorer must be a plain function (callable instances / functools.partial / "
            "bound methods carry runtime state a code digest cannot bind)"
        )
    else:
        refusals.extend(_scorer_selfcontained_refusals(scorer))   # no transitive-state helpers
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


def _try_unlink(path: Path) -> bool:
    """Unlink and REPORT whether the name is gone (unlike _safe_unlink, which swallows).

    Used where a surviving name is a custody problem (a post-commit staging alias, a failed
    reservation-collision cleanup) and must be surfaced, not silently ignored (#966 round-5).
    """
    try:
        os.unlink(path)
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def _drain_and_check(context: str) -> None:
    """Drain the import sentinel and REFUSE if a forbidden module was imported since the last
    checkpoint (#966 round-6 D). Replaces every bare ``_clear``: a window boundary must ACCOUNT
    for imports (drain + raise on non-empty), never erase them unexamined. ``context`` names
    the window whose code just ran.
    """
    imported = _drain_import_sentinel()
    if imported:
        raise B0RunError(f"component IMPORTED during {context}: " + "; ".join(imported))


def _assert_sterile_guarded(backend: GenerationBackend, *, preceding: str) -> None:
    """Account for the PRECEDING window, run the sterility contract, then account for the
    imports IT produced — never clearing either unexamined (#966 round-5 H5 + round-6 D).
    """
    _drain_and_check(preceding)
    backend.assert_sterile()
    _drain_and_check("assert_sterile()")
    reach = assert_no_component_reachable()
    if reach:
        raise B0RunError("component REACHABLE around assert_sterile(): " + "; ".join(reach))


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

    def write_terminal_frame(self, obj: Mapping[str, Any]) -> str:
        """Append a terminal frame, distinguishing 'written' from 'durable' (#966 round-6 A).

        Returns 'synced' if fsync succeeded, 'written_unsynced' if the bytes landed but fsync
        raised. Raises only if the os.write itself failed (the frame is NOT on disk). This lets
        the caller keep the RESULT consistent with what an auditor reading the on-disk journal
        would see: a written frame is recorded (fsync failure is a durability warning), while a
        failed write means the journal has no terminal frame and the run is indeterminate.
        """
        line = (json.dumps(dict(obj), sort_keys=True, allow_nan=False,
                           ensure_ascii=True) + "\n").encode("utf-8")
        _write_all(self._fd, line)                          # raises -> frame not on disk
        try:
            os.fsync(self._fd)
            return "synced"
        except OSError:
            return "written_unsynced"

    def verify_identity(self) -> None:
        """Refuse if the pathname no longer refers to our owned inode (swap detected).

        NOTE (trust boundary): inode equality proves pathname aliasing, not content
        custody. Preventing a hostile co-process from mutating the SAME inode (or the
        check-to-publication race) is the protected-sink OS contract (append-only/immutable
        file + locked-down dir), not something this in-process check can guarantee.
        """
        st_fd = os.fstat(self._fd)
        try:
            st_path = os.stat(self._path)
        except OSError as exc:
            raise B0RunError(f"journal pathname vanished mid-run: {exc}") from exc
        if (st_fd.st_ino, st_fd.st_dev) != (st_path.st_ino, st_path.st_dev):
            raise B0RunError(
                "journal pathname no longer refers to the owned descriptor (swap detected)"
            )

    def actual_prefix_digest(self) -> str:
        """SHA-256 of the ACTUAL journal bytes, read back from the OWNED inode (#966 B2).

        Reads through our own fd (not the pathname), so it reflects real on-disk bytes —
        including a same-inode mutation by another descriptor — and resists a pathname
        swap. This is what the report binds, not the in-memory hash of intended writes.
        """
        os.fsync(self._fd)
        size = os.fstat(self._fd).st_size
        if not size:
            return hashlib.sha256(b"").hexdigest()
        buf = bytearray()
        off = 0
        while off < size:                                   # loop full reads (#966 round-5 H6)
            if hasattr(os, "pread"):
                chunk = os.pread(self._fd, size - off, off)
            else:  # Windows: O_APPEND keeps writes at EOF, so a read seek is safe.
                os.lseek(self._fd, off, os.SEEK_SET)
                chunk = os.read(self._fd, size - off)
            if not chunk:
                raise B0RunError("journal short read: file shrank during digest")
            buf += chunk
            off += len(chunk)
        if os.fstat(self._fd).st_size != size:
            raise B0RunError("journal size changed during digest read")
        return hashlib.sha256(bytes(buf)).hexdigest()

    def prefix_digest_at_seal(self) -> str | None:
        """SHA-256 of the ACTUAL on-disk journal bytes BEFORE the first ``sealing`` frame, read
        through the owned fd (#966 round-7). Reconciled post-commit against the report's bound
        ``journal_digest`` to detect a same-inode co-writer that injected a pre-sealing frame
        between the digest binding and the sealing append — the one evidence artifact that
        otherwise gets no post-commit check. Returns None if no sealing frame is present.
        """
        os.fsync(self._fd)
        size = os.fstat(self._fd).st_size
        if not size:
            return None
        off, buf = 0, bytearray()
        while off < size:
            if hasattr(os, "pread"):
                chunk = os.pread(self._fd, size - off, off)
            else:
                os.lseek(self._fd, off, os.SEEK_SET)
                chunk = os.read(self._fd, size - off)
            if not chunk:
                raise B0RunError("journal short read during prefix reconciliation")
            buf += chunk
            off += len(chunk)
        data = bytes(buf)
        cursor = 0
        for line in data.split(b"\n"):
            try:
                if json.loads(line).get("event") == "sealing":
                    return hashlib.sha256(data[:cursor]).hexdigest()
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
            cursor += len(line) + 1                          # + the split '\n'
        return None

    def digest(self) -> str:
        return self._hash.hexdigest()

    @property
    def fd_open(self) -> bool:
        return not self._closed

    @property
    def path(self) -> Path:
        return self._path

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
    if parent.is_symlink():
        raise B0RunError(f"protected evidence-sink parent is a symlink (refused): {parent}")
    if not parent.is_dir():
        raise B0RunError(
            f"protected evidence-sink parent does not exist (must be predeclared, not "
            f"runner-created): {parent}"
        )
    journal_path = Path(str(report_path) + ".journal")
    if journal_path.is_symlink():
        raise B0RunError(f"journal path is a symlink (refused): {journal_path}")
    # O_RDWR (not WRONLY) so the report can bind the ACTUAL journal bytes via the owned fd.
    # O_BINARY on Windows: raw os.write/os.read must NOT do CRT \n<->\r\n translation, or the
    # digest of the read-back bytes would differ from the on-disk bytes.
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        fd = os.open(journal_path, flags, 0o600)
    except FileExistsError as exc:
        raise B0RunError(f"journal already reserved (prior/colliding run): {journal_path}") from exc
    try:
        _fsync_parent(parent)                # propagates; must not leak the fd (#966 HIGH-5)
    except OSError as exc:
        os.close(fd)
        removed = _try_unlink(journal_path)  # truthful cleanup report (#966 round-5 MED-7)
        if removed:
            try:
                _fsync_parent(parent)
            except OSError:
                pass
            detail = "journal removed"
        else:
            detail = f"JOURNAL NOT REMOVED — collision remains at {journal_path}"
        raise B0RunError(f"reservation parent fsync failed; {detail}: {exc}") from exc
    return _Journal(fd, journal_path)


# Terminal dispositions (#966 round-5 BLOCKER-1). A run that reaches the commit point is
# published; only INTEGRITY_VERIFIED is a normal ok=True success. A detected custody
# violation is committed-but-integrity-failed; an unverifiable check is indeterminate.
INTEGRITY_VERIFIED = "integrity_verified"
COMMITTED_INTEGRITY_FAILED = "committed_integrity_failed"
COMMITTED_INDETERMINATE = "committed_indeterminate"


def publish_report_atomic(report: Mapping[str, Any], report_path: Path) -> tuple[bytes, Path]:
    """Atomically COMMIT the report with a no-replace primitive.

    Strict-encode → same-dir O_EXCL temp → flush/fsync → verify the TEMP bytes → ``os.link``
    (atomic, raises if the target exists). NO in-place fallback. Raises ONLY on PRE-COMMIT
    failure; a successful return marks the point of no return. Returns ``(committed_bytes,
    staging_alias_path)`` — the staging temp is a hard-link ALIAS to the committed inode, so
    the caller MUST remove it via ``finalize_publication`` and treat a failure to do so as a
    custody violation (#966 round-5 BLOCKER-2), not a swallowed cleanup.
    """
    report_path = Path(report_path)
    assert_strict_json(dict(report))
    data = json.dumps(dict(report), indent=2, sort_keys=True, allow_nan=False,
                      ensure_ascii=True).encode("utf-8")
    tmp_path = Path(str(report_path) + f".tmp.{os.getpid()}.{uuid.uuid4().hex}")

    fd = os.open(tmp_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    committed = False
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if tmp_path.read_bytes() != data:                        # verify staged bytes PRE-commit
            raise B0RunError("staged report bytes differ from intended report before publish")
        try:
            os.link(tmp_path, report_path)                       # atomic no-replace COMMIT
        except FileExistsError as exc:
            raise B0RunError(
                f"report path appeared before publish (no-replace refused): {report_path}"
            ) from exc
        except OSError as exc:
            raise B0RunError(
                f"atomic no-replace publication unavailable, refusing in-place downgrade: {exc}"
            ) from exc
        committed = True
    finally:
        if not committed:
            _safe_unlink(tmp_path)                               # pre-commit: nothing published
    return data, tmp_path


def finalize_publication(report_path: Path, committed: bytes, staging_alias: Path,
                         journal: "_Journal", report_journal_digest: str | None = None
                         ) -> tuple[str, list[str]]:
    """Post-COMMIT verification -> (disposition, warnings). The report is already visible, so
    a detected violation is NEVER ``failed``; it is committed-but-integrity-failed/
    indeterminate (#966 round-5 BLOCKER-1). Removes the runner's staging alias and treats a
    surviving writable alias as a custody violation (BLOCKER-2). Reconciles the bound journal
    prefix digest against the actual on-disk pre-sealing bytes (round-7).
    """
    warnings: list[str] = []
    integrity_failed = False
    indeterminate = False

    try:
        if Path(report_path).read_bytes() != committed:          # integrity: report bytes
            warnings.append("post-commit readback mismatch: advertised report bytes corrupted")
            integrity_failed = True
    except OSError as exc:
        warnings.append(f"post-commit readback failed: {exc}")
        indeterminate = True

    # Integrity: the report's bound journal-prefix digest vs the ACTUAL on-disk pre-sealing
    # bytes. A same-inode co-writer that injected a frame BEFORE the sealing frame (between the
    # digest binding and the sealing append) is invisible to every other check (round-7).
    if report_journal_digest is not None:
        try:
            on_disk_prefix = journal.prefix_digest_at_seal()
        except (OSError, B0RunError) as exc:
            warnings.append(f"journal prefix reconciliation read failed: {exc}")
            indeterminate = True
        else:
            if on_disk_prefix != report_journal_digest:
                warnings.append(
                    f"journal prefix digest mismatch (bound {str(report_journal_digest)[:12]}.. "
                    f"vs on-disk {str(on_disk_prefix)[:12]}..): pre-sealing journal mutated")
                integrity_failed = True

    if not _try_unlink(staging_alias):                           # integrity: staging alias
        if Path(staging_alias).exists():
            warnings.append("staging alias could not be removed: a writable second name to "
                            "the committed report inode survives")
            integrity_failed = True

    # Durability LAST — the parent fsync must follow the alias unlink so that BOTH the report
    # hard-link creation AND the alias removal are persisted, not just the link (#966 round-6 C2).
    try:
        _fsync_parent(Path(report_path).parent)
    except OSError as exc:
        warnings.append(f"parent fsync failed post-commit: {exc}")
        indeterminate = True

    try:
        journal.verify_identity()                                # integrity: journal custody
    except B0RunError as exc:
        warnings.append(str(exc))
        integrity_failed = True

    disposition = (COMMITTED_INTEGRITY_FAILED if integrity_failed
                   else COMMITTED_INDETERMINATE if indeterminate
                   else INTEGRITY_VERIFIED)
    return disposition, warnings


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
    warnings: tuple[str, ...] = ()          # post-commit durability/integrity notes
    terminal_state: str = "refused"         # refused | integrity_verified | committed_* (#966 r5)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


_TERMINAL_EVENTS = frozenset({
    "completed", COMMITTED_INTEGRITY_FAILED, COMMITTED_INDETERMINATE, "failed",
})
# The ONLY valid (terminal event -> disposition) pairs. 'failed' is a PRE-commit terminal
# (carries error_type/error, never a committed disposition); a 'failed' frame with a committed
# disposition — or any committed terminal whose disposition field disagrees — is malformed or
# tampered and must fail closed (#975: 'failed'+integrity_verified was accepted with ok=True).
_TERMINAL_DISPOSITION = {
    "completed": INTEGRITY_VERIFIED,
    COMMITTED_INTEGRITY_FAILED: COMMITTED_INTEGRITY_FAILED,
    COMMITTED_INDETERMINATE: COMMITTED_INDETERMINATE,
}
# The ONLY event names a governed B0 journal may contain — reject arbitrary/injected names (#980).
_KNOWN_EVENTS = frozenset({"claim", "attempt", "generated", "recorded", "sealing"}) | _TERMINAL_EVENTS


def verify_terminal_frames(journal_path: Path, *,
                           report_published_digest: str | None = None) -> dict[str, Any]:
    """Executable terminal-PROTOCOL verifier (#966 round-5 HIGH-4) — not JSON syntax alone.

    Requires: non-empty; first event is ``claim``; a single ``run_id`` throughout; at most
    one terminal event and it must be LAST (rejects failed-then-completed and events after a
    terminal); ``completed`` needs a preceding ``sealing``; a non-truncated journal MUST end
    in a terminal; a truncated FINAL line is tolerated ONLY when the last complete event is
    ``sealing`` or a terminal; and (when given) the sealing frame's ``published_digest``
    cross-binds the report. Returns {ok, reason?, terminal, disposition, truncated_tail}.
    """
    raw_text = Path(journal_path).read_text(encoding="utf-8")
    has_final_newline = raw_text == "" or raw_text.endswith("\n")
    lines = raw_text.splitlines()
    events: list[dict[str, Any]] = []
    truncated_tail = False
    for i, line in enumerate(lines):
        is_last = i == len(lines) - 1
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            if is_last:
                truncated_tail = True
                continue
            return {"ok": False, "reason": "corruption", "corruption_at": i}
        if not isinstance(obj, dict):                        # a frame MUST be a JSON object (#980)
            return {"ok": False, "reason": f"non-object journal frame at line {i}"}
        if is_last and not has_final_newline:                # torn write: valid JSON, no newline
            truncated_tail = True
            continue
        events.append(obj)

    if not events:
        return {"ok": False, "reason": "empty journal"}
    if events[0].get("event") != "claim":
        return {"ok": False, "reason": "first event is not 'claim'"}
    unknown = next((e.get("event") for e in events if e.get("event") not in _KNOWN_EVENTS), None)
    if unknown is not None:                                   # no arbitrary/injected events (#980)
        return {"ok": False, "reason": f"unknown journal event {unknown!r}"}
    run_id = events[0].get("run_id")
    if not run_id:                                           # claim MUST carry a run_id (#975)
        return {"ok": False, "reason": "claim frame missing run_id"}
    # attempt/generated/recorded frames carry attempt_id, not run_id; claim/sealing/terminal MUST.
    if any(e.get("run_id", run_id) != run_id for e in events):
        return {"ok": False, "reason": "run_id inconsistent across frames"}

    terminal_idxs = [i for i, e in enumerate(events) if e.get("event") in _TERMINAL_EVENTS]
    if len(terminal_idxs) > 1:
        return {"ok": False, "reason": "more than one terminal event"}
    if terminal_idxs and terminal_idxs[0] != len(events) - 1:
        return {"ok": False, "reason": "events recorded after the terminal event"}

    sealing_idx = next((i for i, e in enumerate(events) if e.get("event") == "sealing"), None)
    if sealing_idx is not None:
        if not events[sealing_idx].get("run_id"):            # sealing MUST carry a run_id (#975)
            return {"ok": False, "reason": "sealing frame missing run_id"}
        for i in range(sealing_idx + 1, len(events)):        # only the terminal may follow sealing
            if events[i].get("event") not in _TERMINAL_EVENTS:
                return {"ok": False, "reason": "non-terminal event recorded after the sealing frame"}

    if terminal_idxs:
        term = events[terminal_idxs[0]]
        tevent, tdisp = term.get("event"), term.get("disposition")
        if not term.get("run_id"):
            return {"ok": False, "reason": "terminal frame missing run_id"}
        if tevent == "failed":
            if tdisp in _TERMINAL_DISPOSITION.values():
                return {"ok": False, "reason": "'failed' terminal must not carry a committed disposition"}
        elif tdisp != _TERMINAL_DISPOSITION.get(tevent):
            return {"ok": False,
                    "reason": f"terminal {tevent!r} disposition must be "
                              f"{_TERMINAL_DISPOSITION.get(tevent)!r}, got {tdisp!r}"}
        # EVERY committed terminal (not just 'completed') requires a preceding sealing (#980).
        if tevent in _TERMINAL_DISPOSITION and (sealing_idx is None or sealing_idx > terminal_idxs[0]):
            return {"ok": False, "reason": f"committed terminal {tevent!r} without a preceding 'sealing'"}

    last_event = events[-1].get("event")
    if truncated_tail:
        if last_event not in (_TERMINAL_EVENTS | {"sealing"}):
            return {"ok": False, "reason": "truncated tail not preceded by sealing/terminal"}
    elif last_event not in _TERMINAL_EVENTS:
        return {"ok": False, "reason": f"journal ends without a terminal event (last={last_event})"}

    if report_published_digest is not None:
        if sealing_idx is not None and events[sealing_idx].get("published_digest") != report_published_digest:
            return {"ok": False, "reason": "sealing published_digest does not match report"}
        if terminal_idxs:                                    # a committed terminal binds it too (#980)
            te = events[terminal_idxs[0]]
            if te.get("event") in _TERMINAL_DISPOSITION and te.get("published_digest") != report_published_digest:
                return {"ok": False, "reason": "terminal published_digest does not match report"}

    terminal = events[terminal_idxs[0]].get("event") if terminal_idxs else last_event
    disposition = events[terminal_idxs[0]].get("disposition") if terminal_idxs else None
    return {"ok": True, "events": events, "terminal": terminal, "disposition": disposition,
            "truncated_tail": truncated_tail, "run_id": run_id}


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
    decision = authorize_b0_launch(manifest)
    refusals = list(decision.refusals)
    refusals.extend(assert_no_component_reachable())               # live sys.modules
    refusals.extend(_validate_panel(panel))
    refusals.extend(check_protected_sink_attestation(manifest))    # OS-contract prereq (#966 r5)
    if not _ensure_import_audit():                                 # fail-CLOSED sentinel (#966)
        refusals.append("transient-import audit sentinel could not be armed (fail-closed)")
    else:
        entry_residue = _drain_import_sentinel()                   # run-entry invariant (round-6 D)
        if entry_residue:
            refusals.append("import-audit sentinel dirty at run entry (a prior run leaked "
                            f"forbidden import(s) {entry_residue}); refusing fail-closed")

    effective_decoding = derive_effective_decoding(manifest)

    # Touch ANY backend code (even the assert_sterile lookup, whose __getattribute__ can import)
    # ONLY after the cheap gates pass (#966 HIGH-4), and ACCOUNT for every import it triggers
    # rather than erasing it with a bare baseline drain (#980 import-audit BLOCKER).
    descriptor: dict[str, Any] = {}
    scorer_digest: str | None = None
    sterile_bound = False
    if not refusals:
        sterile_bound = callable(getattr(backend, "assert_sterile", None))
        lookup_imports = _drain_import_sentinel()
        if lookup_imports:
            refusals.append("component IMPORTED during backend.assert_sterile lookup: "
                            + "; ".join(lookup_imports))
    if not refusals:
        scorer_digest = _callable_digest(scorer) if scorer is not None else None
        digest_imports = _drain_import_sentinel()
        if digest_imports:
            refusals.append("component IMPORTED during scorer digest: " + "; ".join(digest_imports))
        descriptor = dict(backend.descriptor())
        desc_imports = _drain_import_sentinel()
        if desc_imports:
            refusals.append("component IMPORTED during backend.descriptor(): "
                            + "; ".join(desc_imports))
        refusals.extend(assert_no_component_reachable())
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
    published_ok = False
    report: dict[str, Any] | None = None
    warnings: list[str] = []
    run_id = ""
    try:
        run_id = uuid.uuid4().hex                                  # inside try: no fd leak (#966 H5)
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
            _assert_sterile_guarded(backend, preceding="attempt setup")
            _drain_and_check("pre-forward baseline")               # was bare _clear (round-6 D)

            generation = backend.generate(prompt, dict(effective_decoding))  # governed forward

            _drain_and_check("governed forward")                   # transient-import accounting
            post = assert_no_component_reachable()
            if post:
                raise B0RunError("component REACHABLE after governed forward: " + "; ".join(post))
            _assert_sterile_guarded(backend, preceding="post-forward reachability")
            journal.event({
                "event": "generated", "attempt_id": attempt_id, "ordinal": ordinal,
                "probe_id": probe_id, "generation_sha256": canonical_digest(generation),
                "generation": generation,
            })

            scorer_input, scorer_output = (None, None)
            if scorer is not None:
                # Re-verify scorer identity BEFORE and AFTER the call, accounting for imports
                # triggered by the digest recompute itself (attacker-influenceable __repr__,
                # round-6 D) as well as the forward possibly mutating a bound global (round-5 H3).
                _drain_and_check("pre-scorer-digest baseline")
                if _callable_digest(scorer) != scorer_digest:
                    raise B0RunError("scorer identity changed before invocation (state mutated mid-run)")
                _drain_and_check("scorer-identity recompute (pre)")
                scorer_input, scorer_output = scorer(probe_id, generation)
                _drain_and_check("scorer call")
                if _callable_digest(scorer) != scorer_digest:
                    raise B0RunError("scorer identity changed across invocation (state mutated mid-run)")
                _drain_and_check("scorer-identity recompute (post)")
            scorer_post = assert_no_component_reachable()
            if scorer_post:
                raise B0RunError("component reachable via scorer: " + "; ".join(scorer_post))
            _assert_sterile_guarded(backend, preceding="post-scorer reachability")
            bundle.record(                                         # strict-JSON enforced here
                probe_id, generation,
                scorer_input=scorer_input, scorer_output=scorer_output,
                provenance={"prompt_sha256": canonical_digest(prompt), "attempt_id": attempt_id},
            )
            journal.event({
                "event": "recorded", "attempt_id": attempt_id, "ordinal": ordinal,
                "probe_id": probe_id,
            })

        # ---- Terminal transaction: the report binds ACTUAL journal bytes; the journal
        # terminal event + result carry the VERIFIED post-commit disposition (#966 r5 B1). ----
        report = bundle.seal()
        report["run_kind"] = "b0_baseline"
        report["manifest_digest"] = decision.manifest_digest
        report["execution_descriptor"] = execution_descriptor
        report["terminal_state"] = "committed"                     # authority = journal terminal
        report["journal_digest"] = journal.actual_prefix_digest()  # ACTUAL bytes, owned inode
        report["published_digest"] = canonical_digest(
            {k: v for k, v in report.items() if k != "published_digest"}
        )
        journal.verify_identity()                                  # inode still ours pre-publish?
        journal.event({
            "event": "sealing", "run_id": run_id,
            "published_digest": report["published_digest"],
            "journal_digest_prefix": report["journal_digest"], "utc": _now(),
        })
        committed, staging_alias = publish_report_atomic(report, resolved_path)  # PRE-commit raises
        published_ok = True                                        # os.link COMMITTED

        # A DETECTED post-commit violation is committed-integrity-failed/indeterminate, never
        # a normal ok=True (#966 round-5 B1); it is also never `failed` (report is visible).
        disposition, warnings = finalize_publication(resolved_path, committed, staging_alias,
                                                      journal, report["journal_digest"])
        terminal_event = "completed" if disposition == INTEGRITY_VERIFIED else disposition
        frame = {
            "event": terminal_event, "run_id": run_id, "disposition": disposition,
            "published_digest": report["published_digest"],
            "report_bytes_sha256": _sha256_bytes(committed),
            "durability_warnings": warnings, "utc": _now(),
        }
        try:
            sync_state = journal.write_terminal_frame(frame)       # written vs fsync-durable
        except (OSError, B0RunError):
            # The frame is NOT on disk -> the journal has no terminal frame, so the finalize
            # verdict could not be durably recorded. The result must match what an auditor
            # reading the journal would conclude: indeterminate — REGARDLESS of the finalize
            # disposition, whose detail is preserved in warnings (round-6 A2).
            warnings.append(f"terminal frame write failed post-commit; recorded disposition was "
                            f"{disposition} but could not be journaled -> committed-indeterminate")
            disposition = COMMITTED_INDETERMINATE
        else:
            if sync_state == "written_unsynced":
                # fsync FAILED after the bytes were written: durable custody is NOT established.
                # "integrity_verified" must mean durable commit, not page-cache visibility
                # (Codex #973), so the run is indeterminate. The unsynced terminal frame is a
                # non-authoritative tail (standard append-log semantics: a frame whose fsync
                # failed may not survive a crash); the result reports the durable truth.
                warnings.append(f"terminal frame written but NOT fsync-durable; {disposition} is "
                                "not durably committed -> committed-indeterminate")
                disposition = COMMITTED_INDETERMINATE

        # Reconcile the RESULT with the ACTUAL on-disk journal, the source of truth (round-6 A).
        # Catch ValueError too: read_text raises UnicodeDecodeError on a mutated (non-UTF-8)
        # inode, which must not escape as an uncaught raise on a committed run (round-6 A2b).
        try:
            tv = verify_terminal_frames(journal.path,
                                        report_published_digest=report["published_digest"])
        except Exception as exc:                               # noqa: BLE001 - post-commit MUST NOT escape
            # ANY verifier fault post-commit (UnicodeDecodeError, a malformed frame that slips a
            # raise, ...) becomes indeterminate — it can never propagate on a committed run (#980).
            warnings.append(f"terminal-frame verification read failed post-commit: {exc!r}")
            disposition = COMMITTED_INDETERMINATE
        else:
            # The on-disk journal is authoritative: if it does not form a valid terminal, or its
            # terminal disposition disagrees with ours, the result becomes indeterminate so the
            # two can never silently diverge (round-6 A1/A2), for ANY starting disposition.
            if not tv.get("ok"):
                warnings.append(f"terminal-frame verification failed: {tv.get('reason')}")
                disposition = COMMITTED_INDETERMINATE
            elif tv.get("disposition") != disposition:
                warnings.append(f"result/journal disposition disagree (journal={tv.get('disposition')}, "
                                f"result={disposition}); forcing indeterminate")
                disposition = COMMITTED_INDETERMINATE
    except BaseException as exc:
        if not published_ok and journal.fd_open:
            try:                                                   # via the OWNED fd (no reopen)
                journal.event({
                    "event": "failed", "run_id": run_id,
                    "error_type": type(exc).__name__, "error": str(exc)[:500], "utc": _now(),
                })
            except (OSError, B0RunError):
                # A zero-progress write of the failed-event must NOT mask the original backend
                # exception (#980 HIGH): swallow it and re-raise the real cause below.
                pass
        raise
    finally:
        _clear_import_sentinel()                                   # no cross-run residue (round-6 D)
        journal.close()

    assert report is not None
    return B0RunResult(
        ok=(disposition == INTEGRITY_VERIFIED), refusals=(), report=report,
        report_path=str(resolved_path), published_digest=report["published_digest"],
        warnings=tuple(warnings), terminal_state=disposition,
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
        # Bind use_cache ONCE so descriptor and generate cannot disagree (#966 BLOCKER-3).
        cfg = getattr(self.model, "config", None)
        self._use_cache = bool(getattr(cfg, "use_cache", True))

    def descriptor(self) -> Mapping[str, Any]:
        cfg = getattr(self.model, "config", None)
        return {
            "id": self._model_id,
            "revision": self._revision,
            "dtype": _normalize_dtype(self.model.dtype),
            "backend": type(self.model).__name__,
            "device": str(next(self.model.parameters()).device),
            "attention": getattr(cfg, "_attn_implementation", "unknown"),
            "use_cache": self._use_cache,
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
                use_cache=self._use_cache,          # the SAME value descriptor reports (#966 B3)
            )
        return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
