"""
Offline per-memory tension metric for the A3 sleep N-loop shadow experiment.

Zwölf — answers the semantic question Cairn flagged on #121 / Zwölf #535.

WHY NOT reuse compute_tension_proxy offline:
  compute_tension_proxy(pre, user, post) is a WAKE-turn metric — it measures the
  direction-mismatch between the incoming user pull (pre->user) and the model's
  response (user->post). Offline consolidation has no user turn and no response,
  so shoehorning pre/user/post would (a) measure integration-coherence, not
  tension, and (b) re-import the wake "input creates tension" semantics that the
  firewall ("sleep replay does NOT re-tension; only wake can") forbids. That is
  how you manufacture a fourth subtle by-construction bug.

WHAT tension means offline:
  A memory's tension is its MISALIGNMENT with the current consolidated self-state:

      tension(M, S) = 1 - cos(encode(M), S)     # 0 aligned, 1 orthogonal, 2 opposed

  This matches compute_tension_proxy's output scale (also 1 - cosine), so the
  guard's epsilon stays comparable and NLoopAbortGuard needs zero change — it is
  metric-agnostic and just consumes per-memory scores.

THE FIREWALL CHECK (Zwölf #530 C1):
  Re-tensioning = a consolidation pass moving S so a memory becomes MORE misaligned:

      delta(M) = tension(M, S_after) - tension(M, S_before)

  C1 aborts if delta(M) > epsilon for any M.

EPSILON:
  Calibrated from the A1 frozen-state run. With S frozen, tension(M, S) must not
  move pass-to-pass; the residual jitter IS the zero-signal floor. CRITICAL: A1
  calibration and A3 gating must use THIS metric, or epsilon is meaningless.

DECOUPLING:
  The encoder is injected (encode_fn), so this module never imports chat_server.
  Pass the stateless encoder (encode_text_to_mamba_hidden_last_token) — fresh
  encode of M for measurement, never the cache-carrying advance path.
"""
from __future__ import annotations

from typing import Callable, Mapping, Sequence

import numpy as np


def cosine(a, b) -> float:
    """Cosine similarity of two vectors; 0.0 if either is (near-)zero length."""
    av = np.asarray(a, dtype=np.float64).reshape(-1)
    bv = np.asarray(b, dtype=np.float64).reshape(-1)
    na = float(np.linalg.norm(av))
    nb = float(np.linalg.norm(bv))
    if na <= 1e-12 or nb <= 1e-12:
        return 0.0
    return float(np.dot(av, bv) / (na * nb))


def memory_tension(memory_vec, state_vec) -> float:
    """Offline tension of one memory against the self-state. 0=aligned .. 2=opposed.

    Same 1-cosine scale as chat_server.compute_tension_proxy so epsilon is comparable.
    """
    return round(1.0 - cosine(memory_vec, state_vec), 6)


def per_memory_tension_offline(
    memory_ids: Sequence[str],
    memory_texts: Mapping[str, str],
    state_vec,
    encode_fn: Callable[[str], "np.ndarray"],
) -> dict:
    """tension(M, S) for each memory against a single state snapshot.

    encode_fn is injected (e.g. encode_text_to_mamba_hidden_last_token) so this
    module never imports chat_server. Memories with empty text are skipped.
    """
    scores: dict = {}
    for mid in memory_ids:
        text = (memory_texts.get(mid, "") or "").strip()
        if not text:
            continue
        scores[mid] = memory_tension(encode_fn(text), state_vec)
    return scores


def tension_deltas(
    before: Mapping[str, float],
    after: Mapping[str, float],
) -> dict:
    """delta(M) = tension(M, S_after) - tension(M, S_before), for memories in both."""
    return {
        mid: round(float(after[mid]) - float(before[mid]), 6)
        for mid in after
        if mid in before
    }


def calibrate_epsilon_from_a1(
    frozen_state_passes: Sequence[Mapping[str, float]],
    *,
    safety_factor: float = 3.0,
    floor: float = 1e-6,
) -> float:
    """Epsilon = the zero-signal jitter measured on the A1 frozen-state run.

    frozen_state_passes: per-pass {memory_id -> tension(M, S_frozen)} for the A1
    run. Because S is frozen, any pass-to-pass movement is noise. Epsilon =
    safety_factor * (max observed pass-to-pass |delta|), floored at `floor`.

    Use THIS metric for both A1 and A3 or the epsilon does not transfer.
    """
    max_jitter = 0.0
    passes = list(frozen_state_passes)
    for prev, curr in zip(passes, passes[1:]):
        for mid, t in curr.items():
            if mid in prev:
                max_jitter = max(max_jitter, abs(float(t) - float(prev[mid])))
    return max(float(floor), round(safety_factor * max_jitter, 9))
