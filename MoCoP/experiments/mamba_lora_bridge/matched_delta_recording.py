"""Matched-delta activation-target recording for the CHEESE bridge (Codex #806).

WHY THIS EXISTS
---------------
``record_cheese_batch.py`` records the ABSOLUTE last-token v_proj output per
target layer for each shaping episode. There is no matched neutral/scenario
contrast anywhere in the recording. When the training target is an absolute
activation, that target carries a large CROSS-SAMPLE COMMON MODE (the model's own
v_proj bias ``b_v``, the position-0 attention-sink spike vector, the shared prompt
scaffold — all near-constant across episodes). DirectionalLoss fits every target
including that shared constant, so the bridge learns to emit it on every context:
that is where the "bridge-internal DC" the geometry work (#801/#803) measured
DOWNSTREAM comes from — a constant the bridge internalized because the TARGET had
one, ~80% of the bridge output magnitude, ~0% context. (The DC is a property of
the trained bridge OUTPUT, not of the host recording itself; the host recording
never contains a "bridge DC".) Post-hoc DC-removal (#127) then becomes a bandage
on a target-design choice, not identification.

The house already learned this one level up, at the BEHAVIORAL layer: the SEV
matched-pairs corpus (``fixtures/sev_disposition_v0``) exists precisely because
"measurement lives in contrasts, not absolutes". This module pushes that same
principle down to the ACTIVATION-TARGET layer.

WHAT A MATCHED-DELTA TARGET IS
------------------------------
For each shaping SCENARIO (a SEV disposition context) we also run its matched
NEUTRAL control (the same skeleton, ``class=neutral``) and record, per target
layer::

    d_target = v_proj_out(scenario) - v_proj_out(neutral)

What the subtraction removes, and how exactly:
  * EXACT cancellation for INPUT-INDEPENDENT additive terms only: the model's own
    bias ``b_v`` and any true per-layer constant are identical in both forwards and
    subtract to zero exactly.
  * APPROXIMATE (matched-pair) cancellation for input-DEPENDENT terms: the shared
    scaffold and any position-0-spike-mediated effect are NOT identical, because
    ``h_last(scenario) != h_last(neutral)`` (different last tokens / continuations).
    Matched neutrals make these terms nearly equal, so they largely cancel — but by
    matching, NOT by construction.
The load-bearing effect is at the DATASET level: delta targets remove the
cross-sample COMMON MODE, so DirectionalLoss has no shared constant left to
internalize as a bridge DC. ``delta = scenario - neutral`` is what the bridge is
then trained to reproduce (source scenario-minus-neutral -> target
scenario-minus-neutral).

CAPTURE NOISE FLOOR (see the SNR metric)
----------------------------------------
Capture happens at the host dtype, so each side carries per-element quantization
error ~``u * |absolute|`` (``u`` = the dtype unit roundoff) baked in BEFORE the
subtraction and, being from INDEPENDENT forwards, it does NOT cancel. In the
common-mode >> contrast regime this design targets, that noise can DOMINATE a
small delta. Each artifact records a per-layer delta SNR (Codex #817 item 3):
``||delta|| / (u * sqrt(||scenario||^2 + ||neutral||^2))`` — NO ``sqrt(d)`` (the
componentwise error L2 is bounded by ``u*||x||`` directly), and BOTH sides' norms
enter in quadrature. ``u`` is dtype-specific (``EPS_BY_DTYPE``): fp16 2^-11, bf16
2^-8 (~8x, and Gemma-4 records in bf16), fp32 2^-24. The CLI reports min/median
SNR, offers a ``--min-snr`` gate (pre-registered in the manifest, Cairn #816), and
a ``--capture-dtype {fp16,bf16,fp32}`` escalation. fp32 STORAGE does not recover
capture-time noise; fp32 CAPTURE is the real escalation, the SNR gate is the
diagnostic. No verdict is hardcoded — the threshold is a run-time flag.

FROZEN SPLIT (SEV scenario/skeleton split)
------------------------------------------
The scenario<->neutral pairing is NOT decided at record time. It comes from a
FROZEN, versioned manifest built BEFORE recording: each scenario id maps to
exactly one neutral control id, the manifest is content-hashed into a stable
``split_id``, and every recorded artifact carries that ``split_id`` so a run is
reproducible and auditable. The pairing reuses the existing house concept —
``disposition_runner.neutral_control_id`` and the SEV corpus loader — rather than
reinventing it.

MATH CAVEATS (from Codex #806 / Isegrim #807 — honor these)
-----------------------------------------------------------
* RMS effective dose is ``alpha / sqrt(d_v)`` (per-row RMS normalization at the
  injection site divides the unit direction by ``sqrt(d_v)``); a raw recorded
  delta norm is NOT the runtime dose.
* Gemma uses GQA: an o_proj-space quantity needs a replication factor
  ``R = num_query_heads / num_kv_heads`` before o_proj. The recorded target here
  is in v_proj OUTPUT space (kv-head width), pre-replication. Replication COMMUTES
  with the delta — ``replicate(scenario) - replicate(neutral) = replicate(scenario
  - neutral)`` — so recording the delta pre-replication and replicating later is
  equivalent; R does not "cancel", it just commutes. Any downstream o_proj-space
  reasoning must still apply R.
* Tokenwise-RMS at runtime invalidates the EXACT constant-bias identity: a
  constant additive bias does not pass through per-token RMS unchanged. So the
  ``b_v`` cancellation is exact only at the RECORDED-TARGET level (this file), NOT
  at runtime injection. Do not assume exact constant-bias cancellation live.
* Live "tension" is an activation-DIRECTION mismatch, not a prediction error, and
  is UNSAFE as a direct dynamic-alpha sensor. Nothing here wires tension into
  alpha; this module only shapes recorded targets.

MODEL-FREE TESTABILITY
----------------------
The numeric core (delta, common-mode cancellation, frozen-split hashing, schema
assembly) is torch-free and unit-tested with scripted activations and NO model
load (``tests/test_matched_delta_recording.py``). Activation capture sits behind
an injectable ``VProjCapture`` protocol; only ``HFVProjCapture`` imports torch,
lazily, mirroring ``disposition_runner.HFBackend`` and
``mocop_spike_sink_census.capture_forward``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

# This module reuses the SEV pairing RULE and corpus schema but deliberately
# MIRRORS them (a torch-free copy of neutral_control_id + load_sev_corpus) rather
# than importing disposition_runner, which pulls torch transitively via the probe
# panel — mirroring keeps the split/manifest core importable with no GPU. The KMP
# double-init guard is set defensively in case a caller later imports torch in the
# same process (e.g. the HFVProjCapture path). A gpu-marked parity test asserts the
# mirror stays in lockstep with disposition_runner over real SEV ids.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

RECIPE_TAG = "matched_delta_v1"
SCHEMA_VERSION = "matched-delta-v1"

# Per-dtype unit roundoff u (Codex #817 item 3): the capture dtype sets the noise
# floor, and it is NOT always fp16. u = 2^-(mantissa_bits+1): fp16 (10 mantissa
# bits) 2^-11, bf16 (7 bits) 2^-8 — ~8x LARGER, and Gemma-4 records in bf16, so
# the fp16 constant would badly understate the real noise floor — fp32 (23 bits)
# 2^-24. The SNR gate must use the epsilon of the dtype actually captured.
EPS_BY_DTYPE = {"fp16": 2.0 ** -11, "bf16": 2.0 ** -8, "fp32": 2.0 ** -24}
EPS_FP16 = EPS_BY_DTYPE["fp16"]  # back-compat alias


def eps_for_dtype(capture_dtype: str) -> float:
    if capture_dtype not in EPS_BY_DTYPE:
        raise ValueError(f"unknown capture_dtype {capture_dtype!r}; "
                         f"expected one of {sorted(EPS_BY_DTYPE)}")
    return EPS_BY_DTYPE[capture_dtype]

# v_proj comb teeth for the current 1.5B host (mirrors record_cheese_batch.py's
# DEFAULT_TARGET_LAYERS / train_cheese_bridge.TARGET_SPECS). The delta recording
# is layer-set agnostic; this is only the CLI default.
DEFAULT_TARGET_LAYERS = (12, 13, 14, 15)

_SEV_PATH = (
    Path(__file__).resolve().parent
    / "fixtures" / "sev_disposition_v0" / "sev_disposition_v0.jsonl"
)


# --------------------------------------------------------------------------- #
# 0) SEV corpus + pairing (reused, not reinvented).                           #
# --------------------------------------------------------------------------- #
class MissingNeutralError(KeyError):
    """A scenario has no resolvable matched neutral control in the corpus.

    HARD ERROR by design (Codex #806 requirement 3): an unpaired scenario must
    NEVER be silently recorded as if its absolute activation were a delta. A
    missing neutral means the frozen split is incomplete, not that we fall back
    to an absolute target.
    """


def load_sev_corpus(path: Path = _SEV_PATH) -> dict[str, dict]:
    """Load the SEV matched-scenario corpus into ``{id: record}``.

    Records are ``{id, skeleton_id, class, topic, text, notes}`` with id form
    ``{skeleton}_{class}`` and class in warm/cold/adversarial/neutral. This is a
    verbatim mirror of ``disposition_runner.load_sev_corpus`` kept torch-free so
    the split/manifest logic imports without pulling the probe panel.
    """
    corpus: dict[str, dict] = {}
    if not path.exists():
        return corpus
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        corpus[rec["id"]] = rec
    return corpus


def neutral_control_id(context_id: str | None) -> str | None:
    """The matched ``neutral`` variant of a SEV id.

    Identical rule to ``disposition_runner.neutral_control_id`` (line ~157): a
    ``{skeleton}_{warm|cold|adversarial|neutral}`` id maps to
    ``{skeleton}_neutral``. Kept here so this module carries no torch import; the
    two must stay in lockstep (both derive from the SEV id grammar).
    """
    if not context_id or context_id == "DRIFT_CASES":
        return None
    m = re.match(r"^(.*)_(warm|cold|adversarial|neutral)$", context_id)
    if not m:
        return None
    return f"{m.group(1)}_neutral"


# --------------------------------------------------------------------------- #
# 1) Frozen split manifest (SEV scenario/skeleton split).                     #
#    Built BEFORE recording; content-hashed to a stable split_id; every        #
#    recorded artifact carries the split_id (Codex #806 requirement: reproduce  #
#    + audit).                                                                  #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FrozenSplit:
    """A frozen scenario->neutral pairing over the SEV corpus.

    ``pairs`` maps each scenario id to exactly one neutral control id. ``split_id``
    is a content hash over the canonical (scenario, neutral) list + corpus id +
    recipe + held-out skeletons, so two runs built from the same corpus + selection
    + holdout produce the same id, and any change to the pairing OR the holdout
    changes the id.

    ``held_out_skeletons`` (S6, eval-contamination guard): SEV is ALSO the
    disposition eval battery, so training deltas over every SEV scenario trains on
    the test set. These skeleton ids are marked as NEVER-trained; scenarios whose
    skeleton is held out are EXCLUDED from ``pairs`` (not recorded as training
    targets). The mechanism is first-class and stamped into ``split_id``; the
    actual holdout SELECTION is a keeper decision (default: no holdout).
    """

    split_id: str
    corpus_id: str
    recipe: str
    pairs: dict[str, str]                    # scenario_id -> neutral_id (insertion-ordered)
    held_out_skeletons: tuple[str, ...] = ()  # skeleton ids never used as training scenarios

    def scenario_ids(self) -> list[str]:
        return list(self.pairs.keys())

    def neutral_for(self, scenario_id: str) -> str:
        """The frozen neutral control for a scenario. HARD ERROR if unpaired."""
        neutral = self.pairs.get(scenario_id)
        if neutral is None:
            raise MissingNeutralError(
                f"scenario {scenario_id!r} is not in frozen split {self.split_id}"
            )
        return neutral

    def to_manifest(self) -> dict[str, Any]:
        """Serializable manifest (what gets written next to the recordings)."""
        return {
            "schema_version": SCHEMA_VERSION,
            "recipe": self.recipe,
            "split_id": self.split_id,
            "corpus_id": self.corpus_id,
            "held_out_skeletons": list(self.held_out_skeletons),
            "n_pairs": len(self.pairs),
            "pairs": [
                {"scenario_id": s, "neutral_id": n} for s, n in self.pairs.items()
            ],
        }


def corpus_fingerprint(corpus: dict[str, dict]) -> str:
    """A stable id for the corpus CONTENT (not just its filename).

    Hashes the sorted ``(id, class, text)`` triples so that a silently edited
    scenario text changes the corpus id — and therefore every split_id built on
    it — rather than reusing a stale, no-longer-matching pairing.
    """
    h = hashlib.sha256()
    for cid in sorted(corpus):
        rec = corpus[cid]
        h.update(cid.encode("utf-8"))
        h.update(b"\x00")
        h.update(str(rec.get("class", "")).encode("utf-8"))
        h.update(b"\x00")
        h.update(str(rec.get("text", "")).encode("utf-8"))
        h.update(b"\x1e")
    return "sev-" + h.hexdigest()[:16]


def _hash_pairs(pairs: dict[str, str], *, corpus_id: str, recipe: str,
                held_out_skeletons: Sequence[str] = ()) -> str:
    """Deterministic content hash over the canonical pairing.

    Canonical form = pairs sorted by scenario id, joined with the corpus id,
    recipe, and the sorted held-out skeletons. Sorting makes the id independent of
    scenario SELECTION ORDER while still changing if any pair, the corpus/recipe,
    or the holdout changes.
    """
    h = hashlib.sha256()
    h.update(recipe.encode("utf-8"))
    h.update(b"\x1f")
    h.update(corpus_id.encode("utf-8"))
    h.update(b"\x1f")
    for skeleton in sorted(held_out_skeletons):
        h.update(skeleton.encode("utf-8"))
        h.update(b"\x1d")
    h.update(b"\x1f")
    for scenario_id in sorted(pairs):
        h.update(scenario_id.encode("utf-8"))
        h.update(b"\x00")
        h.update(pairs[scenario_id].encode("utf-8"))
        h.update(b"\x1e")
    return "split-" + h.hexdigest()[:16]


def _skeleton_of(corpus: dict[str, dict], scenario_id: str) -> str:
    """The skeleton id for a scenario (from the corpus record, or the id grammar)."""
    rec = corpus.get(scenario_id, {})
    skeleton = rec.get("skeleton_id")
    if skeleton:
        return str(skeleton)
    m = re.match(r"^(.*)_(warm|cold|adversarial|neutral)$", scenario_id)
    return m.group(1) if m else scenario_id


def build_frozen_split(
    corpus: dict[str, dict],
    *,
    scenario_ids: Sequence[str] | None = None,
    recipe: str = RECIPE_TAG,
    held_out_skeletons: Sequence[str] = (),
) -> FrozenSplit:
    """Build the frozen scenario->neutral split over ``corpus``.

    ``scenario_ids`` selects which scenarios to record (default: every
    non-neutral SEV id, in corpus order). Each selected scenario is paired to its
    matched neutral via ``neutral_control_id``; the neutral MUST exist in the
    corpus or this raises ``MissingNeutralError`` — the split is refused rather
    than shipped incomplete. Neutrals themselves are never scenarios (a
    neutral-minus-itself target is zero and meaningless).

    ``held_out_skeletons`` (S6): scenarios whose skeleton is in this set are
    EXCLUDED from ``pairs`` so they are never trained on (SEV is also the eval
    battery). The holdout is stamped into ``split_id``. Refuses an EMPTY resulting
    split (N4): an empty selection / an all-held-out selection is a mistake, not a
    "recorded 0" success.
    """
    corpus_id = corpus_fingerprint(corpus)
    held_out = tuple(held_out_skeletons)
    held_out_set = set(held_out)
    if scenario_ids is None:
        scenario_ids = [
            cid for cid, rec in corpus.items() if rec.get("class") != "neutral"
        ]

    pairs: dict[str, str] = {}
    for scenario_id in scenario_ids:
        if scenario_id not in corpus:
            raise MissingNeutralError(
                f"scenario {scenario_id!r} not present in corpus {corpus_id}"
            )
        if corpus[scenario_id].get("class") == "neutral":
            raise ValueError(
                f"{scenario_id!r} is itself a neutral; a neutral cannot be a "
                "matched-delta scenario (delta would be zero)."
            )
        if _skeleton_of(corpus, scenario_id) in held_out_set:
            continue  # held-out skeleton: never a training scenario (S6).
        neutral_id = neutral_control_id(scenario_id)
        if neutral_id is None or neutral_id not in corpus:
            raise MissingNeutralError(
                f"scenario {scenario_id!r} has no matched neutral control "
                f"(resolved {neutral_id!r}) in corpus {corpus_id}. A frozen split "
                "must pair every scenario; refusing to record an unpaired absolute."
            )
        pairs[scenario_id] = neutral_id

    if not pairs:
        raise ValueError(
            "frozen split is empty: no scenarios selected after holdout "
            f"(corpus {corpus_id}, held_out={sorted(held_out_set)}). Refusing to "
            "record 0 scenarios as a success."
        )

    split_id = _hash_pairs(pairs, corpus_id=corpus_id, recipe=recipe,
                           held_out_skeletons=held_out)
    return FrozenSplit(split_id=split_id, corpus_id=corpus_id, recipe=recipe,
                       pairs=pairs, held_out_skeletons=held_out)


def load_frozen_split(manifest: dict[str, Any],
                      corpus: dict[str, dict] | None = None) -> FrozenSplit:
    """Rehydrate a ``FrozenSplit`` from a written manifest and VERIFY its id.

    Recomputes the content hash over the manifest's pairs (+ held-out skeletons)
    and rejects the manifest if it disagrees with the stored ``split_id`` (tamper /
    drift guard).

    S3: the stored ``split_id`` only pins the manifest's OWN pairs, not the corpus
    ON DISK — a stale manifest over a since-edited SEV corpus would validate
    silently. Pass ``corpus`` to additionally assert
    ``corpus_fingerprint(corpus) == manifest["corpus_id"]`` (recommended for the
    audit + source-side path: the target recorder, the source-side pairing, and
    training must all resolve the SAME corpus content the split was frozen over).
    """
    recipe = manifest["recipe"]
    corpus_id = manifest["corpus_id"]
    held_out = tuple(manifest.get("held_out_skeletons", ()))
    pairs = {p["scenario_id"]: p["neutral_id"] for p in manifest["pairs"]}
    expected = _hash_pairs(pairs, corpus_id=corpus_id, recipe=recipe,
                           held_out_skeletons=held_out)
    if expected != manifest["split_id"]:
        raise ValueError(
            f"frozen-split manifest id mismatch: stored {manifest['split_id']!r} "
            f"recomputed {expected!r} — manifest was edited without rehashing."
        )
    if corpus is not None:
        on_disk = corpus_fingerprint(corpus)
        if on_disk != corpus_id:
            raise ValueError(
                f"frozen-split corpus mismatch: manifest froze corpus {corpus_id!r} "
                f"but the corpus on disk fingerprints as {on_disk!r}. The SEV corpus "
                "was edited since the split was frozen; re-freeze before recording."
            )
    return FrozenSplit(split_id=manifest["split_id"], corpus_id=corpus_id,
                       recipe=recipe, pairs=pairs, held_out_skeletons=held_out)


# --------------------------------------------------------------------------- #
# 2) Delta computation (torch-free; operates on plain float sequences).       #
#    Kept model-agnostic: a "vector" is any sequence of floats; the caller     #
#    hands over CPU-detached rows. Exact for input-independent additive terms  #
#    (b_v), matched-approximate for input-dependent ones (scaffold, spike).    #
# --------------------------------------------------------------------------- #
def _as_floats(vec: Any) -> list[float]:
    """Coerce a recorded 1-D activation row to a plain list[float].

    Accepts a list/tuple of floats or anything with ``.tolist()`` (a detached CPU
    torch/numpy row). Rejects >1-D so a mis-shaped capture is caught here, not
    silently broadcast in the subtraction.
    """
    if hasattr(vec, "tolist"):
        vec = vec.tolist()
    out = list(vec)
    if out and isinstance(out[0], (list, tuple)):
        raise ValueError("expected a 1-D activation row, got a nested sequence")
    return [float(x) for x in out]


def compute_delta(scenario_vec: Any, neutral_vec: Any) -> list[float]:
    """``d = scenario - neutral`` elementwise.

    Input-INDEPENDENT additive terms (the model bias ``b_v``, true per-layer
    constants) are identical on both sides and cancel EXACTLY. Input-DEPENDENT
    terms (the shared scaffold, position-0-spike-mediated effects) are only
    APPROXIMATELY equal — ``h_last(scenario) != h_last(neutral)`` — so the matched
    neutral makes them nearly cancel, not exactly. The delta is a matched
    counterfactual contrast; its value is removing the cross-sample COMMON MODE so
    the downstream loss has no shared constant to internalize as a DC.
    """
    s = _as_floats(scenario_vec)
    n = _as_floats(neutral_vec)
    if len(s) != len(n):
        raise ValueError(
            f"scenario/neutral width mismatch: {len(s)} vs {len(n)} — matched "
            "controls must share the target v_proj width."
        )
    return [a - b for a, b in zip(s, n)]


def _l2(vec: Sequence[float]) -> float:
    return sum(x * x for x in vec) ** 0.5


def delta_snr(delta: Sequence[float], scenario_abs: Sequence[float],
              neutral_abs: Sequence[float] | None = None,
              *, eps: float = EPS_FP16) -> float:
    """Per-layer delta signal-to-noise ratio against the capture noise floor.

    ``SNR = ||delta|| / noise`` where ``noise = eps * sqrt(||scen||^2 + ||neut||^2)``
    (Codex #817 item 3, corrected). Two corrections over the first cut:

    * NO ``sqrt(d)``. For componentwise rounding, each element error is bounded by
      ``eps*|x_i|``, so the vector error L2 is ``||e|| <= eps*||x||`` directly
      (``||e||^2 = sum e_i^2 <= sum (eps*x_i)^2 = eps^2 ||x||^2``). The earlier
      ``* sqrt(d)`` inflated the noise floor by ~sqrt(d) (~45x at d=2048) and
      understated SNR by the same factor.
    * BOTH sides contribute. ``delta = scenario - neutral`` with independent
      rounding on each, so the delta noise adds in quadrature over the two absolute
      norms, not the scenario alone.

    ``neutral_abs=None`` falls back to the scenario norm only (scripted tests /
    back-compat). SNR < ~1 means the delta is at or below the noise floor and the
    contrast is not reliably resolved at the capture dtype. ``eps`` MUST be the
    capture dtype's roundoff (see ``eps_for_dtype``). Returns ``inf`` for a zero
    noise floor (a scripted fp-exact test with zero absolutes).
    """
    n2 = _l2(scenario_abs) ** 2
    if neutral_abs is not None:
        n2 += _l2(neutral_abs) ** 2
    noise = eps * (n2 ** 0.5)
    sig = _l2(delta)
    if noise <= 0.0:
        return float("inf") if sig > 0.0 else 0.0
    return sig / noise


# --------------------------------------------------------------------------- #
# 3) Capture interface (the injectable seam; only the HF impl needs torch).   #
# --------------------------------------------------------------------------- #
class VProjCapture(Protocol):
    """Capture the last-token v_proj output (and input) for a text at each
    target layer. Real impl loads a model; tests script it.

    ``capture(text)`` returns ``{layer_idx: {"v_proj_out": row,
    "v_proj_in": row_or_None}}`` where a row is a 1-D CPU sequence of floats.
    """

    target_layers: tuple[int, ...]

    def capture(self, text: str) -> dict[int, dict[str, Any]]: ...


@dataclass
class ScriptedVProjCapture:
    """Model-free capture for the acceptance suite.

    ``responder(text, layer)`` returns the ``v_proj_out`` row for a scenario/neutral
    text at a layer; ``input_responder`` (optional) returns ``v_proj_in``. This
    lets a test plant an explicit ``scenario = neutral + delta + shared_DC`` and
    assert the recorded delta equals ``delta`` with the DC gone.
    """

    responder: Any                              # (text, layer) -> Sequence[float]
    target_layers: tuple[int, ...] = DEFAULT_TARGET_LAYERS
    input_responder: Any | None = None          # (text, layer) -> Sequence[float] | None

    def capture(self, text: str) -> dict[int, dict[str, Any]]:
        out: dict[int, dict[str, Any]] = {}
        for layer in self.target_layers:
            payload: dict[str, Any] = {"v_proj_out": list(self.responder(text, layer))}
            if self.input_responder is not None:
                row = self.input_responder(text, layer)
                payload["v_proj_in"] = None if row is None else list(row)
            out[layer] = payload
        return out


# --------------------------------------------------------------------------- #
# 4) Per-scenario record assembly (schema; the DC-cancellation gate).         #
# --------------------------------------------------------------------------- #
def build_matched_delta_record(
    *,
    scenario_id: str,
    split: FrozenSplit,
    scenario_capture: dict[int, dict[str, Any]],
    neutral_capture: dict[int, dict[str, Any]],
    target_layers: Sequence[int],
    keep_absolute: bool = True,
    capture_dtype: str = "fp16",
) -> dict[str, Any]:
    """Assemble the per-scenario matched-delta artifact (schema v1).

    The matched-delta target fields (``v_proj_out_scenario`` /
    ``v_proj_out_neutral`` / ``v_proj_out_delta``, and the input-delta trio) are
    ALWAYS present regardless of ``keep_absolute`` — the delta is the point.
    ``keep_absolute`` gates only the BARE back-compat absolutes (``v_proj_out``,
    ``v_proj_in``): NB legacy loaders cannot read this nested ``layers`` schema and
    will KeyError (a safe, loud failure), so the bare absolute is a labeled
    SCENARIO absolute for AUDIT / delta-aware consumers, not a drop-in for the old
    path. Each layer also carries a fp16 ``delta_snr`` (S1). Metadata carries the
    ``neutral_control_id``, ``split_id``, ``corpus_id`` and recipe tag.

    HARD ERROR (never silent) if a target layer is missing from either capture, or
    if the scenario has a ``v_proj_in`` but the matched neutral does not: an
    unpaired or half-paired scenario is refused, not recorded.
    """
    neutral_id = split.neutral_for(scenario_id)
    layers: dict[str, Any] = {}
    snrs: list[float] = []
    for layer in target_layers:
        if layer not in scenario_capture:
            raise KeyError(
                f"scenario {scenario_id!r} missing captured layer {layer}"
            )
        if layer not in neutral_capture:
            raise MissingNeutralError(
                f"neutral {neutral_id!r} missing captured layer {layer} for "
                f"scenario {scenario_id!r} — cannot form a matched delta."
            )
        scen_out = scenario_capture[layer].get("v_proj_out")
        neut_out = neutral_capture[layer].get("v_proj_out")
        if scen_out is None:
            raise KeyError(f"scenario {scenario_id!r} layer {layer} has no v_proj_out")
        if neut_out is None:
            raise MissingNeutralError(
                f"neutral {neutral_id!r} layer {layer} has no v_proj_out — "
                "cannot form a matched delta."
            )
        scen_out = _as_floats(scen_out)
        neut_out = _as_floats(neut_out)
        delta = compute_delta(scen_out, neut_out)
        snr = delta_snr(delta, scen_out, neut_out, eps=eps_for_dtype(capture_dtype))
        snrs.append(snr)
        entry: dict[str, Any] = {
            # matched-delta target (the center of gravity — always present).
            "v_proj_out_scenario": scen_out,
            "v_proj_out_neutral": neut_out,
            "v_proj_out_delta": delta,
            "delta_snr": snr,   # fp16 signal-to-noise (S1); < ~1 = noise-dominated.
        }
        # Input DELTA fields belong to the delta target and are ALWAYS recorded
        # when the input is captured (S5): delta-only mode must not drop them.
        scen_in = scenario_capture[layer].get("v_proj_in")
        neut_in = neutral_capture[layer].get("v_proj_in")
        if scen_in is not None:
            if neut_in is None:
                raise MissingNeutralError(
                    f"scenario {scenario_id!r} layer {layer} has a v_proj_in but "
                    f"neutral {neutral_id!r} does not — refusing a half-paired input "
                    "delta."
                )
            scen_in = _as_floats(scen_in)
            neut_in = _as_floats(neut_in)
            entry["v_proj_in_scenario"] = scen_in
            entry["v_proj_in_neutral"] = neut_in
            entry["v_proj_in_delta"] = compute_delta(scen_in, neut_in)
        if keep_absolute:
            # Bare back-compat absolutes ONLY (labeled scenario absolutes for audit).
            entry["v_proj_out"] = scen_out
            if scen_in is not None:
                entry["v_proj_in"] = scen_in
        layers[str(layer)] = entry

    return {
        "schema_version": SCHEMA_VERSION,
        "recipe": split.recipe,
        "scenario_id": scenario_id,
        "neutral_control_id": neutral_id,
        "split_id": split.split_id,
        "corpus_id": split.corpus_id,
        "target_layers": list(target_layers),
        "keep_absolute": bool(keep_absolute),
        # SNR provenance (Codex #817 items 3+4): the dtype whose noise floor the SNR
        # is measured against, its unit roundoff, and the corrected denominator form.
        "capture_dtype": capture_dtype,
        "snr_eps": eps_for_dtype(capture_dtype),
        "snr_denominator": "eps * sqrt(||scenario||^2 + ||neutral||^2)",
        "min_delta_snr": min(snrs) if snrs else None,
        "median_delta_snr": _median(snrs) if snrs else None,
        "layers": layers,
    }


def _median(values: Sequence[float]) -> float:
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else 0.5 * (s[mid - 1] + s[mid])


# --------------------------------------------------------------------------- #
# 5) HF capture (real run; torch imported lazily — the only non-model-free    #
#    part of this module, never touched by the tests).                        #
# --------------------------------------------------------------------------- #
class HFVProjCapture:
    """Real capture: loads the host once and hooks the v_proj comb teeth.

    Mirrors ``record_cheese_batch.py``'s forward-hook / forward-pre-hook capture
    of the LAST-TOKEN v_proj output (and input), but exposes it through the
    injectable ``VProjCapture`` interface so the recording driver stays
    model-free-testable. Imported torch/transformers lazily so ``import
    matched_delta_recording`` needs no GPU.
    """

    def __init__(self, model_name: str, target_layers: Sequence[int],
                 *, max_length: int = 2048, capture_inputs: bool = True,
                 capture_dtype: str = "fp16"):
        import torch
        from transformers import (AutoConfig, AutoModelForCausalLM,
                                  AutoModelForImageTextToText, AutoProcessor,
                                  AutoTokenizer)

        self.target_layers = tuple(int(x) for x in target_layers)
        self.max_length = int(max_length)
        self.capture_inputs = bool(capture_inputs)
        self._torch = torch
        # The capture dtype sets the SNR noise floor (Codex #817 item 3), so it is
        # first-class: fp16 | bf16 | fp32. bf16 is the ESTABLISHED Gemma-4 run dtype
        # (4-bit is broken in the overlay, fp16 is not what Gemma trained/serves in);
        # fp32 is the S1 escalation. It is stamped into every artifact.
        if capture_dtype not in EPS_BY_DTYPE:
            raise ValueError(f"capture_dtype must be one of {sorted(EPS_BY_DTYPE)}, "
                             f"got {capture_dtype!r}")
        self.capture_dtype = capture_dtype
        load_dtype = {"fp16": torch.float16, "bf16": torch.bfloat16,
                      "fp32": torch.float32}[capture_dtype]

        # Loader-bug class fix (Codex #817 item 2, census-derived): gemma4_unified
        # is a REMOTE-CODE image-text model. It must load via
        # AutoModelForImageTextToText + AutoProcessor with trust_remote_code=True;
        # a plain AutoModelForCausalLM without the flag drops down_proj on conversion
        # (the loader saga, occurrence #3 today). Detect via config model_type / name.
        cfg = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
        is_image_text = (str(getattr(cfg, "model_type", "")).startswith("gemma4")
                         or "gemma-4" in model_name.lower())

        def _load(cls, **kw):
            try:
                return cls.from_pretrained(model_name, dtype=load_dtype,
                                           device_map="auto", trust_remote_code=True, **kw)
            except TypeError:  # older transformers: dtype -> torch_dtype
                return cls.from_pretrained(model_name, torch_dtype=load_dtype,
                                           device_map="auto", trust_remote_code=True, **kw)

        if is_image_text:
            self.proc = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
            self.tokenizer = getattr(self.proc, "tokenizer", self.proc)
            self.model = _load(AutoModelForImageTextToText)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            self.model = _load(AutoModelForCausalLM)
        if getattr(self.tokenizer, "pad_token", None) is None \
                and getattr(self.tokenizer, "eos_token", None) is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model.eval()
        self._layer_modules = self._resolve_layers()
        self._expected_out = {
            L: int(self._vproj(L).out_features) for L in self.target_layers}
        self._expected_in = {
            L: int(self._vproj(L).in_features) for L in self.target_layers}

    def _resolve_layers(self):
        """Locate the decoder layer stack (N6: clearer error on a multimodal
        wrapper). A plain CausalLM exposes ``model.model.layers``; a VLM wrapper
        (e.g. Gemma image-text) nests it under ``model.model.language_model`` or
        ``model.language_model.model``. Try the known shapes, else fail loudly."""
        m = self.model
        for path in (
            lambda: m.model.layers,
            lambda: m.model.language_model.layers,
            lambda: m.language_model.model.layers,
            lambda: m.model.language_model.model.layers,
        ):
            try:
                layers = path()
            except AttributeError:
                continue
            if layers is not None:
                return layers
        raise RuntimeError(
            f"could not locate the decoder layer stack on {type(self.model).__name__}; "
            "this looks like a multimodal wrapper — point HFVProjCapture at the "
            "language_model submodule or extend _resolve_layers for this arch.")

    def _vproj(self, layer_idx: int):
        return self._layer_modules[layer_idx].self_attn.v_proj

    def capture(self, text: str) -> dict[int, dict[str, Any]]:
        torch = self._torch
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True,
                                max_length=self.max_length).to(self.model.device)
        acts: dict[int, dict[str, Any]] = {L: {} for L in self.target_layers}

        def pre_hook(layer_idx):
            def hook(module, module_in):
                if not self.capture_inputs:
                    return
                hin = module_in[0] if isinstance(module_in, tuple) else module_in
                row = hin[0, -1, :].detach().cpu()
                if int(row.shape[-1]) != self._expected_in[layer_idx]:
                    raise RuntimeError(
                        f"v_proj input width mismatch: layer={layer_idx} "
                        f"got={int(row.shape[-1])} expected={self._expected_in[layer_idx]}")
                acts[layer_idx]["v_proj_in"] = row.tolist()
            return hook

        def hook_out(layer_idx):
            def hook(module, module_in, module_out):
                row = module_out[0, -1, :].detach().cpu()
                if int(row.shape[-1]) != self._expected_out[layer_idx]:
                    raise RuntimeError(
                        f"v_proj output width mismatch: layer={layer_idx} "
                        f"got={int(row.shape[-1])} expected={self._expected_out[layer_idx]}")
                acts[layer_idx]["v_proj_out"] = row.tolist()
            return hook

        handles = []
        for L in self.target_layers:
            vproj = self._vproj(L)
            if self.capture_inputs:
                handles.append(vproj.register_forward_pre_hook(pre_hook(L)))
            handles.append(vproj.register_forward_hook(hook_out(L)))
        try:
            with torch.no_grad():
                self.model(**inputs)
        finally:
            for h in handles:
                h.remove()

        # N3: mirror record_cheese_batch.py:132-139 — when capturing inputs, BOTH
        # v_proj_out and v_proj_in must be present, else hard error (never a
        # silent half-capture that later half-pairs the delta).
        missing = [
            L for L in self.target_layers
            if "v_proj_out" not in acts[L]
            or (self.capture_inputs and "v_proj_in" not in acts[L])
        ]
        if missing:
            raise RuntimeError(
                f"missing captured v_proj activations for layers {missing} "
                f"(capture_inputs={self.capture_inputs})")
        return acts


# --------------------------------------------------------------------------- #
# 6) Recording driver (model-free-testable via the injected capture).         #
# --------------------------------------------------------------------------- #
def record_matched_delta(
    capture: VProjCapture,
    split: FrozenSplit,
    corpus: dict[str, dict],
    *,
    target_layers: Sequence[int] | None = None,
    keep_absolute: bool = True,
    sink=None,
) -> list[dict[str, Any]]:
    """Record matched-delta targets for every scenario in the frozen split.

    Runs the SCENARIO and its matched NEUTRAL through ``capture``, forms the
    per-layer delta, and assembles the schema-v1 record. Neutrals are captured
    once and cached (many scenarios share one neutral per skeleton). ``sink``, if
    given, is called with each record (e.g. to torch.save / write JSONL); the
    records are also returned. No model logic here — the whole function runs on a
    scripted capture in the tests.
    """
    layers = tuple(target_layers or capture.target_layers)
    neutral_cache: dict[str, dict[int, dict[str, Any]]] = {}
    records: list[dict[str, Any]] = []

    for scenario_id in split.scenario_ids():
        neutral_id = split.neutral_for(scenario_id)
        if scenario_id not in corpus:
            raise MissingNeutralError(f"scenario {scenario_id!r} not in corpus")
        if neutral_id not in corpus:
            raise MissingNeutralError(
                f"neutral {neutral_id!r} for scenario {scenario_id!r} not in corpus")

        scenario_cap = capture.capture(corpus[scenario_id]["text"])
        if neutral_id not in neutral_cache:
            neutral_cache[neutral_id] = capture.capture(corpus[neutral_id]["text"])
        neutral_cap = neutral_cache[neutral_id]

        record = build_matched_delta_record(
            scenario_id=scenario_id, split=split,
            scenario_capture=scenario_cap, neutral_capture=neutral_cap,
            target_layers=layers, keep_absolute=keep_absolute,
            capture_dtype=getattr(capture, "capture_dtype", "fp16"))
        records.append(record)
        if sink is not None:
            sink(record)
    return records


# --------------------------------------------------------------------------- #
# 7) SNR summary + CLI (the real ML-WS run; a NEW entry point, distinct from   #
#    record_cheese_batch.py so the absolute path's meaning is untouched).      #
# --------------------------------------------------------------------------- #
def snr_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the per-layer fp16 delta SNR across all records+layers (S1).

    Reports the min / median SNR and how many (scenario, layer) deltas fall below
    a ``min_snr`` gate. Torch-free so it is unit-tested model-free. No verdict is
    baked in — the caller decides what to do with a low SNR (warn vs fail).
    """
    per_layer: list[float] = []
    below = 0
    worst: tuple[float, str, int] | None = None
    for rec in records:
        for layer_str, entry in rec["layers"].items():
            snr = float(entry.get("delta_snr", float("inf")))
            per_layer.append(snr)
            if worst is None or snr < worst[0]:
                worst = (snr, rec["scenario_id"], int(layer_str))
    return {
        "n_deltas": len(per_layer),
        "min_snr": min(per_layer) if per_layer else None,
        "median_snr": _median(per_layer) if per_layer else None,
        "worst": ({"snr": worst[0], "scenario_id": worst[1], "layer": worst[2]}
                  if worst else None),
        "below_gate": below,   # filled by snr_gate_count when a gate is supplied
    }


def snr_gate_count(records: list[dict[str, Any]], min_snr: float) -> int:
    """Count (scenario, layer) deltas whose fp16 SNR is below ``min_snr`` (S1)."""
    n = 0
    for rec in records:
        for entry in rec["layers"].values():
            if float(entry.get("delta_snr", float("inf"))) < min_snr:
                n += 1
    return n


def _sanitize(scenario_id: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", scenario_id.lower())


def _write_records_torch(records: list[dict[str, Any]], out_dir: Path) -> None:
    """Persist each record as a ``.pt`` (torch tensors) mirroring the existing
    ``target_cheese_*.pt`` layout, so a delta-aware training run can torch.load
    them. Imported torch lazily; only used by the CLI's real run."""
    import torch

    out_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        payload: dict[str, Any] = {k: v for k, v in record.items() if k != "layers"}
        layers_out: dict[int, dict[str, Any]] = {}
        for layer_str, entry in record["layers"].items():
            layer = int(layer_str)
            layers_out[layer] = {
                key: (torch.tensor(val, dtype=torch.float32)
                      if isinstance(val, list) else val)
                for key, val in entry.items()
            }
        payload["layers"] = layers_out
        torch.save(payload, out_dir / f"target_delta_{_sanitize(record['scenario_id'])}.pt")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record MATCHED-DELTA v_proj targets (scenario - neutral) for "
                    "the CHEESE bridge over the frozen SEV split (Codex #806).")
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-1.5B")
    parser.add_argument("--target-layers", default="12,13,14,15",
                        help="comma-separated v_proj comb-tooth layer indices")
    parser.add_argument("--output-dir", default="activation_sessions_1.5b_delta")
    parser.add_argument("--manifest-name", default="frozen_split_manifest.json")
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--scenario-classes", default="warm,cold,adversarial",
                        help="SEV classes to record as scenarios (neutrals are controls)")
    parser.add_argument("--no-inputs", action="store_true",
                        help="skip v_proj input capture (output-delta only)")
    parser.add_argument("--capture-dtype", choices=("fp16", "bf16", "fp32"),
                        default="fp16",
                        help="host load/capture dtype; sets the SNR noise floor. "
                             "bf16 for the Gemma-4 run, fp32 is the S1 escalation")
    parser.add_argument("--min-snr", type=float, default=None,
                        help="fp16 delta SNR gate: warn (or fail with --fail-on-low-snr) "
                             "when deltas fall below this. Default off / warn-only.")
    parser.add_argument("--fail-on-low-snr", action="store_true",
                        help="with --min-snr, exit non-zero if any delta is below the gate")
    parser.add_argument("--holdout-skeletons", default="",
                        help="comma-separated SEV skeleton ids NEVER used as training "
                             "scenarios (eval-contamination guard, S6). Stamped into "
                             "split_id. The WHICH is a keeper decision.")
    parser.add_argument("--no-holdout-ack", action="store_true",
                        help="consciously record with NO holdout. Required to run "
                             "without --holdout-skeletons: per Cairn #816 the holdout "
                             "default is 'required-per-run', so no-holdout must be an "
                             "explicit acknowledgement, never a silent default.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    script_dir = Path(__file__).resolve().parent
    out_dir = script_dir / args.output_dir
    target_layers = tuple(int(x) for x in args.target_layers.split(",") if x.strip())
    keep_classes = {c.strip() for c in args.scenario_classes.split(",") if c.strip()}
    held_out = tuple(s.strip() for s in args.holdout_skeletons.split(",") if s.strip())

    # Cairn #816: the holdout default is "required-per-run". No-holdout must be a
    # conscious acknowledgement, never a silent default.
    if not held_out and not args.no_holdout_ack:
        raise SystemExit(
            "holdout is required per run (Cairn #816): pass --holdout-skeletons "
            "<ids> (the WHICH is the keeper's call), or --no-holdout-ack to record "
            "with no holdout on purpose. SEV is the eval battery; recording over all "
            "of it trains on the test set.")

    corpus = load_sev_corpus()
    if not corpus:
        raise SystemExit(f"SEV corpus empty/not found at {_SEV_PATH}")
    scenario_ids = [cid for cid, rec in corpus.items() if rec.get("class") in keep_classes]
    # build_frozen_split refuses an empty split (N4) and stamps the holdout (S6).
    split = build_frozen_split(corpus, scenario_ids=scenario_ids,
                               held_out_skeletons=held_out)

    # Freeze the manifest BEFORE recording (the split id every artifact carries).
    # PRE-REGISTER the run config (Cairn #816 note 1): the --min-snr gate and the
    # capture dtype are stamped before any capture, so the SNR floor cannot be
    # lawyered down post-hoc.
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = split.to_manifest()
    manifest["run_config"] = {
        "capture_dtype": args.capture_dtype,
        "snr_eps": eps_for_dtype(args.capture_dtype),
        "min_snr": args.min_snr,
        "fail_on_low_snr": bool(args.fail_on_low_snr),
        "max_length": args.max_length,
        "no_holdout_ack": bool(args.no_holdout_ack),
    }
    manifest_path = out_dir / args.manifest_name
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[matched-delta] frozen split {split.split_id} corpus {split.corpus_id} "
          f"scenarios={len(split.pairs)} held_out={list(split.held_out_skeletons)} "
          f"-> {manifest_path.name}")

    capture = HFVProjCapture(args.model_name, target_layers,
                             max_length=args.max_length,
                             capture_inputs=not args.no_inputs,
                             capture_dtype=args.capture_dtype)
    records = record_matched_delta(capture, split, corpus,
                                   target_layers=target_layers, keep_absolute=True)
    _write_records_torch(records, out_dir)

    # S1: report the fp16 delta SNR so a noise-dominated run is visible, and honor
    # the optional --min-snr gate. fp16 capture cannot recover a sub-noise delta;
    # the escalation is --capture-dtype fp32, not fp32 storage.
    summary = snr_summary(records)
    print(f"[matched-delta] recorded {len(records)} scenario deltas -> {out_dir}")
    print(f"[matched-delta] fp16 delta SNR (dtype={args.capture_dtype}): "
          f"min={summary['min_snr']:.3f} median={summary['median_snr']:.3f} "
          f"worst={summary['worst']}")
    if args.min_snr is not None:
        n_below = snr_gate_count(records, args.min_snr)
        if n_below:
            msg = (f"[matched-delta] WARNING: {n_below}/{summary['n_deltas']} deltas "
                   f"below --min-snr={args.min_snr} — noise-dominated in "
                   f"{args.capture_dtype}. Consider --capture-dtype fp32.")
            print(msg)
            if args.fail_on_low_snr:
                raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
