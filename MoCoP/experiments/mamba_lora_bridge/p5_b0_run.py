"""P5 B0 runner — the read-only baseline harness on top of the deny-by-default gate.

OpenCLAW #156, slice 4 (the B0 HF path). Supersedes e2a79e6, hardened against wolf-Codex
review of record #966 (MoCoP/reviews/p5_b0_runner_review_2026-07-12.md). Turns
``p5_b0_harness`` (the model-free launch gate) into a runnable baseline:

  * authorize the manifest (deny-by-default),
  * assert no component module is REACHABLE in the live process — before AND after every
    forward AND scorer, plus a process-wide import-audit sentinel that catches a component
    imported-and-removed transiently inside a single forward,
  * MANDATORILY bind every executed input with DERIVED hashes: panel, backend descriptor
    (incl. backend/device/attention/use_cache), the reviewed scorer loaded CONTENT-FIRST from a
    committed allowlist (spec P5_B0_SCORER_ALLOWLIST — identity is a review property, not a
    runtime one), the derived decoding hash, rubric/processor/runtime, and the runner's OWN
    source digest against an authorized manifest value,
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
import math
import os
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, NamedTuple, Protocol, Sequence

from p5_b0_harness import (
    B0_RUN_KIND,
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


def _inert_snapshot(obj: Any, _depth: int = 0) -> Any:
    """Rebuild ``obj`` from EXACT built-in types only — no caller copy hooks, no retained alias.

    Codex #1009 BLOCKER-3: the caller owns the ``manifest`` / ``panel`` objects and can mutate
    them AFTER they are authorized+hashed (a backend callback changed ``model.id`` / a prompt
    post-hash and still published success under the original receipt). Before ANY backend access
    the runner reconstructs an inert deep snapshot and authorizes/hashes/validates/journals/executes
    ONLY that. Exact-type dispatch (``type(o) is dict``) so a dict/list SUBCLASS with an overridden
    ``items``/``__iter__``/``__deepcopy__`` cannot inject or alias — such an input is refused, not
    honored. The snapshot shares no mutable object with the caller's originals.
    """
    if _depth > 64:
        raise B0RunError("manifest/panel nesting too deep to snapshot")
    t = type(obj)
    # EXACT-type leaves (Codex #1011 B2): a str/int/… SUBCLASS is refused, not returned by
    # identity — a subclass can override __eq__ to compare equal to a different published value.
    # No conversion/equality/hash/iter/copy hook is invoked on a leaf.
    if obj is None or t is bool or t is int or t is str:
        return obj
    if t is float:
        if not math.isfinite(obj):                            # finite-float check while reconstructing
            raise B0RunError("non-finite float in manifest/panel input")
        return obj
    if t is dict:
        out: dict[str, Any] = {}
        for k, v in list(obj.items()):                        # plain dict.items — not caller code
            if type(k) is not str:                            # string-key check (exact)
                raise B0RunError(f"non-string mapping key {k!r} in manifest/panel input")
            out[k] = _inert_snapshot(v, _depth + 1)
        return out
    if t is list or t is tuple:
        return [_inert_snapshot(x, _depth + 1) for x in list(obj)]
    raise B0RunError(f"non-inert {t.__name__} in manifest/panel input (only EXACT plain "
                     "dict/list/tuple/str/int/float/bool/None permitted)")


def _bind_reachability_guard():
    """Freeze the no-component guard's authority at import into closure cells (Codex #1006 class,
    one guarantee over — a-Fable review, WC follow-up).

    The reachability lookup AND the transient-import audit must not be a call-time dereference of
    an assignable/clearable module global — the same rule R4 applied to the scorer/runner origin.
    ``FORBIDDEN_ROUTE_MODULES`` stays as the reviewed, published inventory, but the GUARD reads a
    deep snapshot frozen HERE (a new dict of new frozensets), immune to a plain
    ``p5_b0_run.FORBIDDEN_ROUTE_MODULES = {}`` OR an in-place ``.clear()`` (both in-scope data
    mutations). The sentinel's recorded-imports buffer and its installed-state live in cells too,
    so a caller cannot blank the buffer or spoof "armed" by assigning ``_audit_installed``.
    Reassigning the exposed FUNCTIONS is function replacement — the documented out-of-scope residual.
    """
    real_sys = sys                       # Codex #1009 B1: capture the REAL sys module object, so a
    #                                      caller reassigning `p5_b0_run.sys = proxy` cannot feed the
    #                                      guard an empty modules map or a no-op addaudithook.
    frozen = {route: frozenset(mods) for route, mods in FORBIDDEN_ROUTE_MODULES.items()}
    #  The inventory snapshot is NEVER returned as a mutable alias (Codex #1009 B1: exporting it as
    #  `_FROZEN_FORBIDDEN` let `.clear()` on that name blank the closure's own dict).
    log: list[str] = []                  # append-only MONOTONE evidence; never cleared, no drain/
    #                                      clear op is exposed (Codex #1009 B1: an exported destructive
    #                                      op let a backend erase its own import evidence mid-window).
    state = {"installed": False}

    def forbidden_route_for(name: str) -> str | None:
        """Return the route a module NAME falls under, by exact top-level/basename equality."""
        if not isinstance(name, str) or not name:
            return None
        top = name.split(".", 1)[0]
        base = name.rsplit(".", 1)[-1]
        for route, forbidden in frozen.items():
            if name in forbidden or top in forbidden or base in forbidden:
                return route
        return None

    def import_audit_hook(event: str, args: tuple) -> None:
        if event == "import" and args:
            name = args[0]
            if isinstance(name, str) and forbidden_route_for(name):
                log.append(name)                     # monotone append; nothing is ever removed

    def ensure_import_audit() -> bool:
        """Install the transient-import sentinel; False if it could NOT be armed (fail CLOSED,
        #966). Installed-state is a CLOSURE cell — no reassignable ``_audit_installed`` to spoof."""
        if not state["installed"]:
            try:
                real_sys.addaudithook(import_audit_hook)
            except Exception:  # pragma: no cover - audit hooks unavailable
                return False
            state["installed"] = True
        return state["installed"]

    def live_modules() -> Mapping[str, Any]:
        return real_sys.modules                      # the REAL module table, not a reassignable sys

    def new_import_watch():
        """A per-run window watch with a PRIVATE local cursor into the monotone log. Non-destructive:
        it only reads the log suffix since the last checkpoint and advances its OWN cursor. The
        cursor lives in this closure cell (a run_b0 local) — code running inside a guarded window
        (a backend/scorer) has no handle to it and cannot erase or skip evidence (Codex #1009 B1)."""
        box = {"cursor": len(log)}

        def forbidden_since_last() -> tuple[str, ...]:
            cp = box["cursor"]
            box["cursor"] = len(log)
            return tuple(sorted(set(log[cp:])))

        return forbidden_since_last

    return (forbidden_route_for, import_audit_hook, ensure_import_audit,
            live_modules, new_import_watch)


(_forbidden_route_for, _import_audit_hook, _ensure_import_audit,
 _live_modules, _new_import_watch) = _bind_reachability_guard()


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

    ``loaded_modules`` is a TEST/helper seam only; ``run_b0`` inspects the REAL live module table
    captured in the guard closure — never the reassignable module-global ``sys`` (Codex #1009 B1).
    """
    modules = loaded_modules if loaded_modules is not None else _live_modules()
    hits = reachable_components(modules)
    return [
        f"component route {route!r} is REACHABLE: module(s) {mods} loaded in-process"
        for route, mods in sorted(hits.items())
    ]


# The import-audit sentinel (transient forbidden import caught inside one forward, which a
# before/after sys.modules snapshot misses, #966) is now frozen into the closure above.

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


# --------------------------------------------------------------------------- #
# The runner's ORIGIN — captured once, at import, into a closure cell.          #
# --------------------------------------------------------------------------- #
# Codex #1006 BLOCKER-1: ``__file__`` is an ORDINARY ASSIGNABLE module attribute. Deriving the
# governed allowlist path AND the runner receipt from it at CALL time let a caller select both by
# assigning ``p5_b0_run.__file__`` — the same plain data-attribute assignment that broke
# ``DEFAULT_ALLOWLIST_PATH``, just one level down (canary: mutable_dunder_file_override). The
# lesson, now learned three times: an authority must not be a call-time dereference of ANY
# assignable module attribute, dunder included.
#
# So the origin is resolved ONCE, at import, and kept in a CLOSURE CELL. There is no module-level
# path DATA attribute to reassign, and a later ``__file__`` assignment cannot move the authority:
# both the governed allowlist and the runner receipt hang off this one fixed origin.
def _bind_runner_origin():
    origin = Path(__file__).resolve()                 # evaluated at import, then frozen in a cell
    allowlist = origin.with_name("scorer_allowlist.json")

    def runner_origin() -> Path:
        return origin

    def governed_allowlist_path() -> Path:
        return allowlist

    return runner_origin, governed_allowlist_path


_runner_origin, _governed_allowlist_path = _bind_runner_origin()


def _runner_digest() -> str:
    """SHA-256 of the runner's OWN source, read from the frozen origin (never from ``__file__``)."""
    try:
        return canonical_digest(_runner_origin().read_text(encoding="utf-8"))
    except OSError:  # pragma: no cover - source always present in practice
        return "unknown"


# --------------------------------------------------------------------------- #
# Reviewed-scorer allowlist (the authority move, spec P5_B0_SCORER_ALLOWLIST).  #
# --------------------------------------------------------------------------- #
# Nine review rounds (#960->#980->#987) proved the same theorem-shaped fact: you cannot
# cryptographically bind the identity of an ARBITRARY caller-supplied Python callable
# (getsource fails on eval'd code; globals()/getattr route around a co_names scan; isinstance
# admits stateful subclasses; __class__ swaps / sys.modules shadowing / TOCTOU wait behind
# those). Identity is not a runtime property in this language — it is a REVIEW property. So B0
# stops verifying arbitrary code and only runs REVIEWED, content-hash-pinned scorers. For a
# read-only baseline the scorer is a fixed null-estimator by definition; there is no legitimate
# caller-supplied scorer. This collapses the entire scorer-binding review class.
SCORER_ALLOWLIST_SCHEMA = "b0_scorer_allowlist_v1"


def load_allowlisted_scorer(
    manifest: Mapping[str, Any], allowlist_path: Path | None = None,
) -> tuple[Callable[..., Any] | None, dict[str, Any], list[str]]:
    """Content-first load of the reviewed scorer named by ``manifest.scorer`` (spec §4).

    Returns ``(scorer_fn, binding, refusals)``. NEVER imports by name — ``sys.path``/
    ``sys.modules`` could hand back a different module than the one hashed. Instead: read the
    allowlist bytes, canonically digest the parsed object and require it to equal the manifest's
    ``scorer.allowlist_digest``; find the entry by ``scorer_id``+``version`` (NO unlisted
    fallback, no back door); read the module FILE bytes and require their sha256 to equal the
    entry ``blob_sha256``; then ``compile`` + ``exec`` those verified bytes in a FRESH isolated
    namespace and resolve the entrypoint, refusing anything but a plain function. Any failure is
    a pre-run refusal (empty fn, no forwards). The import sentinel is drained after exec: a
    reviewed scorer imports nothing, so an import during load is a review-contract violation.

    AUTHORITY (Codex #1003/#1006 BLOCKER-1): the GOVERNED path comes from the FROZEN runner origin
    (``_governed_allowlist_path()``, captured in a closure cell at import) — never from a
    module-level path global, and never from a call-time read of the assignable ``__file__``. An
    assignable path-selection attribute IS an alternate authority (a caller that supplies both the
    allowlist and its digest proves agreement, not review). ``run_b0`` never passes
    ``allowlist_path``; the parameter exists ONLY for loader unit tests, which sit BELOW the
    governed entrypoint.
    """
    SCORER_ALLOWLIST_SCHEMA = _authority().scorer_allowlist_schema   # frozen (Codex #1011 B1)
    allowlist_path = (Path(allowlist_path) if allowlist_path is not None
                      else _governed_allowlist_path())
    scorer_block = manifest.get("scorer", {})
    if not isinstance(scorer_block, Mapping):
        return None, {}, ["manifest scorer block missing or not a mapping"]
    want_id = scorer_block.get("scorer_id")
    want_version = scorer_block.get("version")
    want_allowlist_digest = scorer_block.get("allowlist_digest")

    try:
        raw = allowlist_path.read_bytes()
    except OSError as exc:
        return None, {}, [f"scorer allowlist unreadable at {allowlist_path}: {exc}"]
    try:
        allow_obj = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, {}, [f"scorer allowlist is not valid JSON: {exc}"]
    try:
        allowlist_digest = canonical_digest(allow_obj)
    except (TypeError, ValueError) as exc:
        return None, {}, [f"scorer allowlist is not canonicalizable: {exc}"]

    if not want_allowlist_digest:
        return None, {}, ["manifest scorer.allowlist_digest is unset; scorer authority is unbound"]
    if allowlist_digest != want_allowlist_digest:
        return None, {}, [
            f"scorer allowlist digest {allowlist_digest[:12]}.. != manifest "
            f"scorer.allowlist_digest {str(want_allowlist_digest)[:12]}.. (unbound allowlist)"]

    if not isinstance(allow_obj, Mapping) or allow_obj.get("schema_version") != SCORER_ALLOWLIST_SCHEMA:
        return None, {}, [f"scorer allowlist schema_version is not {SCORER_ALLOWLIST_SCHEMA!r}"]
    entries = allow_obj.get("scorers")
    if not isinstance(entries, list):
        return None, {}, ["scorer allowlist 'scorers' is missing or not a list"]
    entry = next(
        (e for e in entries if isinstance(e, Mapping)
         and e.get("scorer_id") == want_id and e.get("version") == want_version),
        None,
    )
    if entry is None:
        return None, {}, [
            f"no allowlisted scorer for id={want_id!r} version={want_version!r} "
            "(deny-by-default: no unlisted scorer, no hashed fallback)"]

    # Codex #1000 BLOCKER-3: the loader must not execute an UNRESOLVED review authority. The
    # external resolvable-attestation hold still applies, but a placeholder ref (empty/TBD/
    # PENDING) is refused locally — journaling it is not the same as clearing it.
    review_ref = entry.get("review_ref")
    if _is_unresolved_ref(review_ref):
        return None, {}, [
            f"allowlist entry review_ref {review_ref!r} is unresolved (empty/TBD/PENDING); a "
            "resolved review reference is required before the scorer may execute"]

    module_path = entry.get("module_path")
    blob_sha256 = entry.get("blob_sha256")
    entrypoint = entry.get("entrypoint")
    if not isinstance(module_path, str) or not module_path:
        return None, {}, ["allowlist entry module_path missing"]
    if not _is_sha256(blob_sha256):
        return None, {}, ["allowlist entry blob_sha256 missing or not a sha256"]
    if not isinstance(entrypoint, str) or not entrypoint:
        return None, {}, ["allowlist entry entrypoint missing"]

    # Codex #1000 BLOCKER-1: no runtime authority back door. The module path is resolved ONLY
    # relative to the committed allowlist's own directory (the single committed root) — absolute
    # paths and ``..`` traversal out of that directory are refused, so an allowlist entry cannot
    # point the loader at arbitrary caller-supplied code elsewhere on the filesystem.
    base = allowlist_path.parent.resolve()
    if Path(module_path).is_absolute():
        return None, {}, ["allowlist entry module_path must be relative to the committed "
                          "allowlist directory, not absolute"]
    resolved = (base / module_path).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        return None, {}, ["allowlist entry module_path escapes the committed allowlist directory"]
    try:
        module_bytes = resolved.read_bytes()
    except OSError as exc:
        return None, {}, [f"allowlisted scorer module unreadable at {resolved}: {exc}"]
    actual_blob = _sha256_bytes(module_bytes)
    if actual_blob != blob_sha256:
        return None, {}, [
            f"scorer module sha256 {actual_blob[:12]}.. != allowlist blob_sha256 "
            f"{str(blob_sha256)[:12]}.. (module content is not the reviewed bytes)"]

    namespace: dict[str, Any] = {}
    load_watch = _new_import_watch()                          # monotone window over the exec below
    try:
        exec(compile(module_bytes, str(resolved), "exec"), namespace)  # NEVER import — content-first
    except Exception as exc:  # noqa: BLE001 - any load fault is a pre-run refusal
        return None, {}, [f"allowlisted scorer module failed to load: {type(exc).__name__}: {exc}"]
    load_imports = load_watch()
    if load_imports:
        return None, {}, [
            "component IMPORTED during scorer module load (a reviewed scorer imports nothing): "
            + "; ".join(load_imports)]

    fn = namespace.get(entrypoint)
    if not inspect.isfunction(fn):
        return None, {}, [f"scorer entrypoint {entrypoint!r} did not resolve to a plain function"]

    binding = {
        "scorer_id": want_id, "version": want_version, "blob_sha256": blob_sha256,
        "allowlist_digest": allowlist_digest, "review_ref": entry.get("review_ref"),
    }
    return fn, binding, []


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


def _is_unresolved_ref(value: Any) -> bool:
    """True if a review reference is a placeholder rather than a resolved review of record.

    ONE predicate, used by BOTH the allowlist loader and the journal verifier (Codex #1006
    BLOCKER-2: the loader refused ``PENDING-codex`` while the standalone verifier still accepted a
    claim frame carrying it — the two must not be able to drift). Journaling an unresolved
    authority is not the same as clearing it.
    """
    if _is_unset(value):                          # empty / "tbd" / "none" / "pending" / "[tbd: ..."
        return True
    # PENDING-* placeholder as a PREFIX, not a bare substring — a bare "in" over-refuses a legit
    # ref like "REVIEW-appending-42" (a-Fable Finding 3). Our placeholders are always leading.
    return str(value).strip().lower().startswith("pending")


def _bind_execution_to_manifest(
    manifest: Mapping[str, Any], panel: Sequence[tuple[str, str]],
    descriptor: Mapping[str, Any],
    rubric_version: str | None, processor_revision: str | None,
    decoding_hash: str | None, runtime_hash: str | None,
    effective_decoding: Mapping[str, Any], sterile_bound: bool,
) -> list[str]:
    """Refuse unless EVERY executed input is present and matches the authorized manifest."""
    DESCRIPTOR_KEYS = _authority().descriptor_keys            # frozen (Codex #1009 B2)
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

    # Scorer identity is owned by the content-first allowlist loader (spec §3-§4), not this
    # binding: there is no caller-supplied scorer to introspect. The manifest scorer block
    # (scorer_id/version/allowlist_digest) is verified there, deny-by-default.

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


def _check_import_window(watch: Callable[[], tuple[str, ...]], context: str) -> None:
    """REFUSE if a forbidden module was imported since ``watch``'s last checkpoint (#966 round-6 D).

    ``watch`` is a per-run monotone window (``_new_import_watch``): non-destructive (it reads the
    append-only log suffix and advances its OWN private cursor), so unlike the retired
    ``_drain``/``_clear`` it cannot be called by in-window code to erase evidence (Codex #1009 B1).
    """
    imported = watch()
    if imported:
        raise B0RunError(f"component IMPORTED during {context}: " + "; ".join(imported))


def _assert_sterile_guarded(backend: GenerationBackend,
                            watch: Callable[[], tuple[str, ...]], *, preceding: str) -> None:
    """Account for the PRECEDING window, run the sterility contract, then account for the
    imports IT produced — via the non-destructive monotone watch (#966 round-5 H5 + round-6 D).
    """
    _check_import_window(watch, preceding)
    backend.assert_sterile()
    _check_import_window(watch, "assert_sterile()")
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
    _A = _authority()                                             # frozen dispositions (#1009 B2)
    INTEGRITY_VERIFIED = _A.integrity_verified
    COMMITTED_INTEGRITY_FAILED = _A.committed_integrity_failed
    COMMITTED_INDETERMINATE = _A.committed_indeterminate
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
# The vocabulary a governed B0 journal draws from — the ORDER is enforced by the sequence
# grammar below; membership here only gives a clear "unknown event" reason (#980 + GPT-5.5 #1).
_KNOWN_EVENTS = frozenset({"claim", "attempt", "generated", "recorded", "sealing"}) | _TERMINAL_EVENTS
# The per-probe cycle the grammar expects between the claim and the sealing/terminal.
_PROBE_CYCLE = ("attempt", "generated", "recorded")


# --------------------------------------------------------------------------- #
# EXACT per-frame schemas (Codex #1000/#1003 BLOCKER-2).                        #
# --------------------------------------------------------------------------- #
# Order is not a contract on its own, and neither is a partial field check. Every governed frame
# has an EXACT field set: each required field must be present and well-TYPED, and NO extra field
# may appear (arbitrary extra keys are how a co-writer smuggles state past a name-only checker).
# The digest fields the verdict depends on are required UNCONDITIONALLY and must be sha256-shaped
# — an empty or absent digest is not a passing digest (#1003: a digest-free sealing/terminal and an
# empty generation digest both passed the round-2 verifier).
_SHA = "sha256"          # 64-hex digest
_STR = "str"             # non-empty string
_TEXT = "text"           # string, may be empty (raw generation / error text)
_ORD = "ordinal"         # int, not bool, >= 0
_WARN = "warnings"       # list of strings
_BINDING = "binding"     # the claim's scorer_binding object
_REF = "review_ref"      # a RESOLVED review reference (not empty/TBD/PENDING) — same rule as loader

_FRAME_SCHEMAS: dict[str, dict[str, str]] = {
    "claim": {"run_id": _STR, "run_kind": _STR, "manifest_digest": _SHA,
              "execution_descriptor_digest": _SHA, "scorer_binding": _BINDING, "utc": _STR},
    "attempt": {"attempt_id": _STR, "ordinal": _ORD, "probe_id": _STR,
                "prompt_sha256": _SHA, "utc": _STR},
    "generated": {"attempt_id": _STR, "ordinal": _ORD, "probe_id": _STR,
                  "generation_sha256": _SHA, "generation": _TEXT},
    "recorded": {"attempt_id": _STR, "ordinal": _ORD, "probe_id": _STR},
    "sealing": {"run_id": _STR, "published_digest": _SHA, "journal_digest_prefix": _SHA,
                "utc": _STR},
    "failed": {"run_id": _STR, "error_type": _STR, "error": _TEXT, "utc": _STR},
}
# Every COMMITTED terminal (completed / committed_integrity_failed / committed_indeterminate)
# shares one schema: the published digest AND the report-bytes digest are unconditional.
_COMMITTED_TERMINAL_SCHEMA = {
    "run_id": _STR, "disposition": _STR, "published_digest": _SHA,
    "report_bytes_sha256": _SHA, "durability_warnings": _WARN, "utc": _STR,
}
# The claim's scorer_binding must itself be fully bound (spec §6) — a claim that names no
# reviewed scorer, or names one with an unresolved review_ref, is not a governed claim.
_SCORER_BINDING_SCHEMA = {"scorer_id": _STR, "version": _STR, "blob_sha256": _SHA,
                          "allowlist_digest": _SHA, "review_ref": _REF}


def _prefix_digest_before_sealing(raw: bytes) -> str | None:
    """SHA-256 of the exact raw journal bytes BEFORE the first ``sealing`` frame (BLOCKER-4).

    Mirrors ``_Journal.prefix_digest_at_seal`` but over a file the standalone auditor was handed.
    Codex #1009: the verifier must HASH the actual prefix, not merely accept a sha256-SHAPED
    ``journal_digest_prefix`` — shape is not a binding. Returns None if no sealing frame is present.
    """
    cursor = 0
    for line in raw.split(b"\n"):
        try:
            if json.loads(line).get("event") == "sealing":
                return hashlib.sha256(raw[:cursor]).hexdigest()
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            pass
        cursor += len(line) + 1                               # + the split '\n'
    return None


def _typed_field_error(kind: str, key: str, value: Any) -> str | None:
    """None if ``value`` satisfies the declared field ``kind``, else a reason fragment."""
    _A = _authority()                                          # frozen tags (Codex #1009 B2)
    _SHA, _STR, _TEXT, _ORD = _A.sha_tag, _A.str_tag, _A.text_tag, _A.ord_tag
    _WARN, _BINDING, _REF = _A.warn_tag, _A.binding_tag, _A.ref_tag
    _SCORER_BINDING_SCHEMA = _A.scorer_binding_schema
    if kind == _SHA:
        return None if _is_sha256(value) else f"{key} is not a sha256 digest"
    if kind == _STR:
        return None if isinstance(value, str) and value.strip() else f"{key} is not a non-empty string"
    if kind == _REF:
        if not isinstance(value, str) or not value.strip():
            return f"{key} is not a non-empty string"
        # #1006 B2: a journalled claim may not restore an authority the loader would refuse.
        return None if not _is_unresolved_ref(value) else f"{key} is unresolved (empty/TBD/PENDING)"
    if kind == _TEXT:
        return None if isinstance(value, str) else f"{key} is not a string"
    if kind == _ORD:
        ok = isinstance(value, int) and not isinstance(value, bool) and value >= 0
        return None if ok else f"{key} is not a non-negative int"
    if kind == _WARN:
        ok = isinstance(value, list) and all(isinstance(w, str) for w in value)
        return None if ok else f"{key} is not a list of strings"
    if kind == _BINDING:
        if not isinstance(value, dict):
            return f"{key} is not an object"
        return _exact_schema_error(key, value, _SCORER_BINDING_SCHEMA,
                                   event_key=False, nested=True)
    return None  # pragma: no cover - unreachable kind


def _exact_schema_error(label: str, frame: Mapping[str, Any], schema: Mapping[str, str],
                        *, event_key: bool = True, nested: bool = False) -> str | None:
    """None if ``frame`` matches ``schema`` EXACTLY (no missing, no extra, all typed).

    ``nested`` phrases errors as ``parent.field`` (for the claim's ``scorer_binding`` object),
    which the caller then wraps once — so the exactness rule has a single implementation.
    """
    allowed = set(schema) | ({"event"} if event_key else set())
    for key in schema:
        if key not in frame:
            return f"{label}.{key} is missing" if nested else f"{label} frame missing {key}"
    extra = sorted(set(frame) - allowed)
    if extra:
        noun = f"{label}" if nested else f"{label} frame"
        return f"{noun} has unexpected field(s) {extra}"
    for key, kind in schema.items():
        err = _typed_field_error(kind, key, frame[key])
        if err:
            return f"{label}.{err}" if nested else f"{label} frame {err}"
    return None


def _descriptor_schema_error(descriptor: Any) -> str | None:
    """Codex #1013 B1: the backend descriptor must be an EXACT dict with EXACTLY the frozen key
    set and EXACT field types — a list root would raise later, and extra fields would publish
    unbound under integrity_verified. ``use_cache`` is a bool; every other field is a plain str."""
    keys = _authority().descriptor_keys
    if type(descriptor) is not dict:
        return f"backend descriptor root is not a dict (got {type(descriptor).__name__})"
    have = set(descriptor)
    if have != set(keys):
        return (f"backend descriptor keys mismatch (extra={sorted(have - set(keys))}, "
                f"missing={sorted(set(keys) - have)})")
    for k in keys:
        v = descriptor[k]
        want_bool = k == "use_cache"
        if want_bool and type(v) is not bool:
            return f"backend descriptor field {k!r} must be a bool"
        if not want_bool and type(v) is not str:
            return f"backend descriptor field {k!r} must be a str"
    return None


def _frame_schema_error(event: str, frame: Mapping[str, Any]) -> str | None:
    """Exact-schema check for one governed frame (dispatches committed terminals)."""
    _A = _authority()                                          # frozen schemas (Codex #1009 B2)
    if event == "failed" and "disposition" in frame:
        # #975 invariant, kept as its own reason: 'failed' is a PRE-commit terminal.
        return "'failed' terminal must not carry a committed disposition"
    schema = _A.frame_schemas.get(event)
    if schema is None:                                   # a committed terminal
        schema = _A.committed_terminal_schema
    return _exact_schema_error(event, frame, schema)


def verify_terminal_frames(journal_path: Path, *,
                           report_published_digest: str | None = None,
                           committed_report_bytes: bytes | None = None) -> dict[str, Any]:
    """Executable terminal-PROTOCOL verifier (#966 round-5 HIGH-4) — not JSON syntax alone.

    Requires: non-empty; first event is ``claim``; a single ``run_id`` throughout; at most
    one terminal event and it must be LAST (rejects failed-then-completed and events after a
    terminal); ``completed`` needs a preceding ``sealing``; a non-truncated journal MUST end
    in a terminal; a truncated FINAL line is tolerated ONLY when the last complete event is
    ``sealing`` or a terminal; and (when given) the sealing frame's ``published_digest``
    cross-binds the report. Returns {ok, reason?, terminal, disposition, truncated_tail}.
    """
    _A = _authority()                                         # frozen verdict authority (#1009 B2)
    _KNOWN_EVENTS, _TERMINAL_EVENTS = _A.known_events, _A.terminal_events
    _TERMINAL_DISPOSITION, _PROBE_CYCLE = _A.terminal_disposition, _A.probe_cycle
    B0_RUN_KIND = _A.b0_run_kind
    raw_bytes = Path(journal_path).read_bytes()               # the ACTUAL on-disk bytes (BLOCKER-4)
    raw_text = raw_bytes.decode("utf-8")
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
    # No arbitrary/injected events (#980). Iterate rather than next(...): a non-string event (e.g.
    # ``{"event": []}``) is non-hashable and would raise in an ``in`` test, and a missing/None
    # event collides with next()'s None sentinel — both must fail CLOSED, not crash or slip
    # (a-Fable Finding 2).
    for e in events:
        ev = e.get("event")
        if not isinstance(ev, str) or ev not in _KNOWN_EVENTS:
            return {"ok": False, "reason": f"unknown journal event {ev!r}"}

    # EXACT per-frame schema (Codex #1003 BLOCKER-2): every frame's field set is closed — required
    # fields present and typed, no extras — BEFORE any semantic check reads them. This is what
    # makes the digest fields the verdict depends on unconditional.
    for e in events:
        schema_error = _frame_schema_error(e.get("event"), e)
        if schema_error:
            return {"ok": False, "reason": schema_error}

    run_id = events[0].get("run_id")
    if not run_id:                                           # claim MUST carry a run_id (#975)
        return {"ok": False, "reason": "claim frame missing run_id"}
    if events[0].get("run_kind") != B0_RUN_KIND:             # the claim binds the run KIND (#1003)
        return {"ok": False, "reason": f"claim frame run_kind is not {B0_RUN_KIND!r}"}
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

    # ---- Event SEQUENCE + per-event SCHEMA grammar (GPT-5.5 finding #1, both halves; Codex
    # #1000 BLOCKER-2). Order alone is not a contract: the grammar enforces claim -> (attempt ->
    # generated -> recorded)* -> sealing? -> terminal?, AND binds each cycle's identity
    # (attempt_id, ordinal, probe_id) so a well-ordered cycle whose three frames disagree on their
    # ids/ordinal is rejected. A pre-commit 'failed' may interrupt a partial cycle; a committed
    # terminal may not. Catches double 'sealing', 'generated'-before-'attempt', interleaved
    # probes, and id/ordinal-forged cycles that name-only ordering misses.
    cycle_pos = 0                     # 0 = between cycles; 1 = expect 'generated'; 2 = expect 'recorded'
    expected_ordinal = 0              # ordinals must run 0,1,2,.. across cycles (matches enumerate)
    cycle_key: tuple[Any, Any, Any] | None = None   # (attempt_id, ordinal, probe_id) of this cycle
    grammar_sealing = False
    grammar_terminal = False
    for idx, e in enumerate(events):
        ev = e.get("event")
        if idx == 0:
            continue                  # events[0] == 'claim' already verified above
        if grammar_terminal:
            return {"ok": False, "reason": "events recorded after the terminal event"}
        if ev == "claim":
            return {"ok": False, "reason": "more than one 'claim' frame"}
        if ev in _TERMINAL_EVENTS:
            if ev != "failed":        # committed terminal needs a completed cycle + a sealing
                if cycle_pos != 0:
                    return {"ok": False, "reason": f"committed terminal {ev!r} recorded mid probe-cycle"}
                if not grammar_sealing:
                    return {"ok": False, "reason": f"committed terminal {ev!r} without a preceding 'sealing'"}
            grammar_terminal = True
            continue
        if ev == "sealing":
            if grammar_sealing:
                return {"ok": False, "reason": "more than one 'sealing' frame"}
            if cycle_pos != 0:
                return {"ok": False, "reason": "'sealing' recorded mid probe-cycle"}
            grammar_sealing = True
            continue
        if grammar_sealing:           # a probe frame after sealing is out of grammar
            return {"ok": False, "reason": f"probe frame {ev!r} recorded after 'sealing'"}
        if ev != _PROBE_CYCLE[cycle_pos]:
            return {"ok": False,
                    "reason": f"out-of-order probe frame {ev!r} (expected {_PROBE_CYCLE[cycle_pos]!r})"}
        # The exact schema above already guarantees these are present and well-typed; here the
        # cycle's IDENTITY is bound: the attempt_id must be DERIVED from the run (run_id:ordinal),
        # the ordinal monotonic, and all three frames of one cycle must agree (Codex #1000/#1003).
        aid, ordv, pid = e["attempt_id"], e["ordinal"], e["probe_id"]
        if ev == "attempt":
            if ordv != expected_ordinal:
                return {"ok": False,
                        "reason": f"attempt ordinal {ordv} != expected {expected_ordinal} (non-monotonic)"}
            derived = f"{run_id}:{ordv}"
            if aid != derived:
                return {"ok": False,
                        "reason": f"attempt_id {aid!r} is not run-derived (expected {derived!r})"}
            cycle_key = (aid, ordv, pid)
        elif (aid, ordv, pid) != cycle_key:
            return {"ok": False,
                    "reason": f"{ev} frame identity {(aid, ordv, pid)} != its cycle {cycle_key}"}
        cycle_pos = (cycle_pos + 1) % 3
        if cycle_pos == 0:            # cycle complete: advance the expected ordinal
            expected_ordinal += 1

    last_event = events[-1].get("event")
    if truncated_tail:
        if last_event not in (_TERMINAL_EVENTS | {"sealing"}):
            return {"ok": False, "reason": "truncated tail not preceded by sealing/terminal"}
    elif last_event not in _TERMINAL_EVENTS:
        return {"ok": False, "reason": f"journal ends without a terminal event (last={last_event})"}

    # The two journal RECEIPTS must identify the SAME publication — ALWAYS, not only when an
    # external expected digest is supplied (Codex #1006 BLOCKER-3: a sealing frame with one valid
    # digest and its committed terminal with a different valid digest passed, because the exact
    # schemas made both fields mandatory but never compared them). The optional
    # report_published_digest additionally binds both to the report BYTES; its absence must not
    # permit the journal to attest two different publications.
    if terminal_idxs and sealing_idx is not None:
        te = events[terminal_idxs[0]]
        if te.get("event") in _TERMINAL_DISPOSITION:
            if te.get("published_digest") != events[sealing_idx].get("published_digest"):
                return {"ok": False,
                        "reason": "terminal published_digest does not match the sealing frame "
                                  "(the journal attests two different publications)"}

    # BLOCKER-4 (#1009): the sealing frame's journal_digest_prefix must EQUAL the sha256 of the
    # actual raw bytes preceding it — a sha256 SHAPE (already enforced by the schema) is not a
    # binding. A hand-crafted journal with a plausible-but-wrong 64-hex prefix is rejected.
    if sealing_idx is not None:
        actual_prefix = _prefix_digest_before_sealing(raw_bytes)
        if actual_prefix is None or events[sealing_idx].get("journal_digest_prefix") != actual_prefix:
            return {"ok": False,
                    "reason": "sealing journal_digest_prefix does not match the actual pre-sealing "
                              "journal bytes"}

    if report_published_digest is not None:
        if sealing_idx is not None and events[sealing_idx].get("published_digest") != report_published_digest:
            return {"ok": False, "reason": "sealing published_digest does not match report"}
        if terminal_idxs:                                    # a committed terminal binds it too (#980)
            te = events[terminal_idxs[0]]
            if te.get("event") in _TERMINAL_DISPOSITION and te.get("published_digest") != report_published_digest:
                return {"ok": False, "reason": "terminal published_digest does not match report"}

    # GPT-5.5 finding #2: the committed terminal frame's report_bytes_sha256 is a hash the verdict
    # depends on; it must be INSIDE the verified set. Given the committed report bytes, require the
    # terminal frame to bind their sha256 (Monk #984 blocker-2).
    if committed_report_bytes is not None and terminal_idxs:
        te = events[terminal_idxs[0]]
        if te.get("event") in _TERMINAL_DISPOSITION:
            want_report_sha = hashlib.sha256(committed_report_bytes).hexdigest()
            if te.get("report_bytes_sha256") != want_report_sha:
                return {"ok": False,
                        "reason": "terminal report_bytes_sha256 does not match committed report bytes"}

    terminal = events[terminal_idxs[0]].get("event") if terminal_idxs else last_event
    disposition = events[terminal_idxs[0]].get("disposition") if terminal_idxs else None
    return {"ok": True, "events": events, "terminal": terminal, "disposition": disposition,
            "truncated_tail": truncated_tail, "run_id": run_id}


def run_b0(
    manifest: Mapping[str, Any],
    panel: Sequence[tuple[str, str]],
    backend: GenerationBackend,
    *,
    rubric_version: str | None = None,
    processor_revision: str | None = None,
    decoding_hash: str | None = None,
    runtime_hash: str | None = None,
    report_path: Path | None = None,
) -> B0RunResult:
    """Run a read-only B0 baseline. Refuses (zero forwards) on ANY gate violation."""
    _A = _authority()                                             # frozen verdict authority (#1009 B2)
    B0_RUN_KIND = _A.b0_run_kind
    INTEGRITY_VERIFIED = _A.integrity_verified
    COMMITTED_INDETERMINATE = _A.committed_indeterminate
    # BLOCKER-3 (#1009): snapshot the caller-owned inputs to inert built-ins BEFORE anything else,
    # and never read the originals again — so a backend callback cannot mutate a hashed input.
    try:
        manifest = _inert_snapshot(manifest)
        panel = _inert_snapshot(panel)
    except B0RunError as exc:
        return B0RunResult(False, (f"input not inert-reconstructable: {exc}",), None, None, None)

    decision = authorize_b0_launch(manifest)
    refusals = list(decision.refusals)
    # Codex #1011 B3: normalize the external SCALAR bindings before they are compared — an
    # equality-overriding str subclass must not pass against a different manifest value.
    for _sname, _sval in (("rubric_version", rubric_version),
                          ("processor_revision", processor_revision),
                          ("decoding_hash", decoding_hash), ("runtime_hash", runtime_hash)):
        if _sval is not None and type(_sval) is not str:
            refusals.append(f"{_sname} must be an exact str (an equality-overriding subclass is refused)")

    # Codex #1013 B3: normalize report_path ONCE, NOW, before any backend/scorer callback can see
    # or mutate it. Keep only the inert string (or a static refusal); the original object is never
    # read, repr'd, or fspath'd again — so a stateful path cannot mutate an initial mismatch into
    # acceptance, and a raising __repr__ cannot crash a refusal message.
    report_path_str: str | None = None
    if report_path is not None:
        try:
            _rp = os.fspath(report_path)
        except TypeError:
            _rp = None
        if type(_rp) is str:
            report_path_str = _rp
        else:
            refusals.append("report_path is not a valid filesystem path string")

    refusals.extend(assert_no_component_reachable())               # live sys.modules
    refusals.extend(_validate_panel(panel))
    refusals.extend(check_protected_sink_attestation(manifest))    # OS-contract prereq (#966 r5)
    watch = None
    if not _ensure_import_audit():                                 # fail-CLOSED sentinel (#966)
        refusals.append("transient-import audit sentinel could not be armed (fail-closed)")
    else:
        # Open a per-run monotone window NOW; every later check reads only the log suffix it
        # appended (Codex #1009 B1). Cross-run bleed is structurally impossible (nothing is ever
        # cleared; each run inspects only its own suffix), so the clear-era 'dirty at entry' check
        # is subsumed — a component RESIDENT at entry is still caught by the snapshot check above.
        watch = _new_import_watch()

    effective_decoding = derive_effective_decoding(manifest)

    # Touch ANY backend code (even the assert_sterile lookup, whose __getattribute__ can import)
    # ONLY after the cheap gates pass (#966 HIGH-4), and ACCOUNT for every import it triggers
    # via the non-destructive monotone watch (#980 import-audit BLOCKER; #1009 B1).
    descriptor: dict[str, Any] = {}
    scorer_fn: Callable[..., Any] | None = None
    scorer_binding: dict[str, Any] = {}
    sterile_bound = False
    if not refusals:
        sterile_bound = callable(getattr(backend, "assert_sterile", None))
        lookup_imports = watch()
        if lookup_imports:
            refusals.append("component IMPORTED during backend.assert_sterile lookup: "
                            + "; ".join(lookup_imports))
    if not refusals:
        # Content-first load of the reviewed scorer from the COMMITTED allowlist (fixed path; no
        # caller override — the loader accounts for any import its exec triggers and refuses it).
        scorer_fn, scorer_binding, load_refusals = load_allowlisted_scorer(manifest)
        refusals.extend(load_refusals)
    if not refusals:
        # Codex #1011 B3: the backend result is caller-controlled — inert-reconstruct it (exact
        # built-in leaves) BEFORE binding, so an equality-overriding descriptor leaf cannot bind an
        # exact manifest to a different published model id.
        try:
            descriptor = _inert_snapshot(backend.descriptor())
        except B0RunError as exc:
            refusals.append(f"backend descriptor is not inert-reconstructable: {exc}")
        else:
            desc_err = _descriptor_schema_error(descriptor)      # exact root/keys/types (#1013 B1)
            if desc_err:
                refusals.append(desc_err)
        desc_imports = watch()
        if desc_imports:
            refusals.append("component IMPORTED during backend.descriptor(): "
                            + "; ".join(desc_imports))
        refusals.extend(assert_no_component_reachable())
    if not refusals:
        refusals.extend(
            _bind_execution_to_manifest(
                manifest, panel, descriptor,
                rubric_version, processor_revision, decoding_hash, runtime_hash,
                effective_decoding, sterile_bound,
            )
        )

    # Codex #1011 B3: derive the publication destination SOLELY from the exact-string sink in the
    # inert manifest (a plain str after _inert_snapshot). A caller-supplied report_path is
    # normalized ONCE (os.fspath collapses a split __str__/__fspath__ object to a single value) and
    # required to equal that sink — but is never itself used as the path, so it cannot redirect the
    # report to an alternate destination.
    sink_path = manifest.get("evidence_sink", {}).get("path")
    resolved_path: Path | None = None
    if not refusals:
        if not (isinstance(sink_path, str) and sink_path):
            refusals.append("manifest evidence_sink.path is unset; cannot bind evidence")
        else:
            # Compare the PRE-NORMALIZED report_path string (never the original object) to the
            # inert manifest sink; the path is always derived from the sink, never from the caller.
            if report_path_str is not None and report_path_str != sink_path:
                refusals.append(f"report_path {report_path_str!r} != manifest evidence_sink.path "
                                f"{sink_path!r}")
            if not refusals:
                resolved_path = Path(sink_path)               # the inert manifest's exact string

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
            "scorer_id": scorer_binding.get("scorer_id"),
            "scorer_version": scorer_binding.get("version"),
            "scorer_blob_sha256": scorer_binding.get("blob_sha256"),
            "scorer_allowlist_digest": scorer_binding.get("allowlist_digest"),
            "scorer_review_ref": scorer_binding.get("review_ref"),
            "rubric_version": rubric_version,
            "processor_revision": processor_revision,
            "runtime_hash": runtime_hash,
            "runner_digest": _runner_digest(),
            "manifest_digest": decision.manifest_digest,
        }
        bundle = B0EvidenceBundle(manifest_digest=decision.manifest_digest or "")
        journal.event({
            "event": "claim", "run_id": run_id, "run_kind": B0_RUN_KIND,
            "manifest_digest": decision.manifest_digest,
            "execution_descriptor_digest": canonical_digest(execution_descriptor),
            "scorer_binding": {
                "scorer_id": scorer_binding.get("scorer_id"),
                "version": scorer_binding.get("version"),
                "blob_sha256": scorer_binding.get("blob_sha256"),
                "allowlist_digest": scorer_binding.get("allowlist_digest"),
                "review_ref": scorer_binding.get("review_ref"),
            },
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
            _assert_sterile_guarded(backend, watch, preceding="attempt setup")
            _check_import_window(watch, "pre-forward baseline")

            generation = backend.generate(prompt, dict(effective_decoding))  # governed forward
            # Codex #1011 -> #1013 B2: require an EXACT str immediately, before any hash/journal/
            # score/custody — a str subclass can render visible text yet carry contradictory
            # scorer evidence while remaining GREEN.
            if type(generation) is not str:
                raise B0RunError(f"backend.generate returned a non-exact-str "
                                 f"({type(generation).__name__}); refusing")

            _check_import_window(watch, "governed forward")        # transient-import accounting
            post = assert_no_component_reachable()
            if post:
                raise B0RunError("component REACHABLE after governed forward: " + "; ".join(post))
            _assert_sterile_guarded(backend, watch, preceding="post-forward reachability")
            journal.event({
                "event": "generated", "attempt_id": attempt_id, "ordinal": ordinal,
                "probe_id": probe_id, "generation_sha256": canonical_digest(generation),
                "generation": generation,
            })

            # The scorer is a reviewed, content-pinned pure function (loaded content-first from
            # the allowlist). It imports nothing, so the sentinel guards around the CALL turn any
            # import into a review-contract violation; no runtime identity re-derivation is needed
            # (identity is a review property, frozen by the blob hash — spec §5).
            _check_import_window(watch, "pre-scorer baseline")
            assert scorer_fn is not None
            scorer_input, scorer_output = scorer_fn(probe_id, generation)
            _check_import_window(watch, "scorer call")
            scorer_post = assert_no_component_reachable()
            if scorer_post:
                raise B0RunError("component reachable via scorer: " + "; ".join(scorer_post))
            _assert_sterile_guarded(backend, watch, preceding="post-scorer reachability")
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
                                        report_published_digest=report["published_digest"],
                                        committed_report_bytes=committed)
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
        # No sentinel clear: the import log is monotone and never erased (Codex #1009 B1); the
        # next run opens its own watch, so there is no cross-run residue to clear.
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


# --------------------------------------------------------------------------- #
# One complete VERDICT-AUTHORITY inventory, frozen at import (Codex #1009 B2).   #
# --------------------------------------------------------------------------- #
# Section 12's rule, applied to EVERY verdict authority rather than name-by-name: no verdict may
# be a call-time dereference of an assignable module attribute. The module-level constants above
# remain the PUBLISHED documentation copies; the governed entrypoint and the standalone verifier
# read the frozen snapshot returned by ``_authority()`` instead. Each verdict function rebinds the
# names it needs from this snapshot at entry (a local read of a frozen value), so reassigning or
# mutating any published module global — DESCRIPTOR_KEYS, B0_RUN_KIND, INTEGRITY_VERIFIED,
# _TERMINAL_DISPOSITION, _FRAME_SCHEMAS, _DTYPE_ALIASES, … — cannot weaken a verdict. Dict-valued
# authorities are exposed as read-only proxies so the snapshot itself cannot be mutated in place.
class _Authority(NamedTuple):
    descriptor_keys: tuple
    b0_run_kind: str
    integrity_verified: str
    committed_integrity_failed: str
    committed_indeterminate: str
    terminal_events: frozenset
    terminal_disposition: Mapping[str, str]
    known_events: frozenset
    probe_cycle: tuple
    dtype_aliases: Mapping[str, str]
    frame_schemas: Mapping[str, Mapping[str, str]]
    committed_terminal_schema: Mapping[str, str]
    scorer_binding_schema: Mapping[str, str]
    sha_tag: str
    str_tag: str
    text_tag: str
    ord_tag: str
    warn_tag: str
    binding_tag: str
    ref_tag: str
    scorer_allowlist_schema: str


def _bind_authority() -> Callable[[], _Authority]:
    from types import MappingProxyType

    def _froze_schema(s: Mapping[str, Any]) -> Mapping[str, Any]:
        return MappingProxyType({k: (MappingProxyType(dict(v)) if isinstance(v, dict) else v)
                                 for k, v in s.items()})

    snap = _Authority(
        descriptor_keys=tuple(DESCRIPTOR_KEYS),
        b0_run_kind=str(B0_RUN_KIND),
        integrity_verified=str(INTEGRITY_VERIFIED),
        committed_integrity_failed=str(COMMITTED_INTEGRITY_FAILED),
        committed_indeterminate=str(COMMITTED_INDETERMINATE),
        terminal_events=frozenset(_TERMINAL_EVENTS),
        terminal_disposition=MappingProxyType(dict(_TERMINAL_DISPOSITION)),
        known_events=frozenset(_KNOWN_EVENTS),
        probe_cycle=tuple(_PROBE_CYCLE),
        dtype_aliases=MappingProxyType(dict(_DTYPE_ALIASES)),
        frame_schemas=_froze_schema(_FRAME_SCHEMAS),
        committed_terminal_schema=MappingProxyType(dict(_COMMITTED_TERMINAL_SCHEMA)),
        scorer_binding_schema=MappingProxyType(dict(_SCORER_BINDING_SCHEMA)),
        sha_tag=str(_SHA), str_tag=str(_STR), text_tag=str(_TEXT), ord_tag=str(_ORD),
        warn_tag=str(_WARN), binding_tag=str(_BINDING), ref_tag=str(_REF),
        scorer_allowlist_schema=str(SCORER_ALLOWLIST_SCHEMA),
    )

    def authority() -> _Authority:
        return snap

    return authority


_authority = _bind_authority()


def _normalize_dtype(raw: Any) -> str:
    aliases = _authority().dtype_aliases                       # frozen; not the reassignable global
    key = str(raw).replace("torch.", "").strip().lower()
    return aliases.get(key, key)


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
