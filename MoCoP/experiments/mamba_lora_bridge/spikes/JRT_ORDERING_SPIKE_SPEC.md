# JRT Ordering Spike — Ask-Then-Read and the Recall Gap

Date: 2026-06-10
Author: Isegrim (Fable 5), from Techno-Monk's #591 design
Status: DRAFT — awaiting Monk's review; ML-WS window currently his (#611). Execution claimed via board, not by this file.
Origin: Monk's #591 (Arora et al. 2024, "Just read twice," arXiv:2407.05483, local PDF in `Research/`) + handoff recommended-next-step + #592 substrate bakeoff + Entry 58 thought-channel finding.

## Hypothesis

Recurrent state-conditioning is order/selection-limited, not only capacity-limited (JRT). If Mamba ingests the memory packet before the question, it must preserve everything that might matter; question-first lets it select what to keep. Therefore part of the MoCoP recall gap is ordering — not bridge capacity, not retrieval ranking.

## Design

Same retrieved rows for every condition (frozen packet per probe, lifted from Monk's #584 lane artifacts for comparability — no live Qdrant call). Controller off, no DAM, same alpha, same Qwen, seeded sampling. Only the state-conditioning order varies:

| Cond | Order | What it measures |
|------|-------|------------------|
| A | memory → question | current pipeline order (baseline) |
| B | question → memory → question | intent-first + final restate (Monk's B) |
| C | (memory + question) × 2 | JRT-Prompt repetition (Monk's C) |
| D | question → memory | pure ask-then-read — separates intent-first from repetition, which B conflates |

A/B/C are Monk's #591 core; D completes the informal factorial (query position × repetition). For the narrow run, the literal question text serves as the "intent" — no Qwen-side intent-formation pass (that is the full ask-then-read loop, out of scope here).

## Readouts

**1. Behavioral (bridged lane, Qwen2.5-1.5B current).** Exact fact use on supported probes (purple color, name_check, vesper_context); abstention on unsupported lures (golden_bicycle, purple_golden_bicycle, fake_pancakes_sandcastles); naturalness (manual 0–2). Heuristic + manual scoring columns both kept — the lexical scorer undercounts negation (#612 caveat).

*Named risk:* #592 scored the 1.5B at 0/24 on evidence use in the bakeoff harness. Behavioral deltas may be floor-compressed on the baby. This readout exists for pipeline comparability with #584/#603/#604, not as the decisive measurement.

**2. State-geometry (floor-proof).** Extract Mamba L3 last-token state after ingestion per condition. Probe-lite readout: nearest-centroid / cosine-margin recoverability of the queried fact from the state, plus cosine separation between states conditioned on relevant-vs-irrelevant packets. Spike-scale, not Phase-1 rigor — a null here is weaker evidence than a full-probe null, and is flagged as such. This readout cannot be floor-compressed by the decoder: it asks what the recurrent state *kept*, not what the 1.5B can say.

**Optional Phase 2 — substrate-comparative (read-only, no bridge).** Same A/B/C/D as prompt-order on Gemma-4-12B-it and Qwen3-14B-Base, reusing Monk's bakeoff panel (#612) for row-comparability. On capable substrates the behavioral readout is not floor-compressed; feeds the swap decision directly. Gemma-4 note: strip or route the thought channel before scoring (runbook gotcha) — but the thought channel is also the native home for a real intent-formation pass later (Entry 58, insight 5).

## Registered predictions (Isegrim, 2026-06-10 — score publicly, win or lose)

1. State readout: queried-fact recoverability B, D > A beyond seed noise; C intermediate.
2. Behavioral on 1.5B: floor-compressed; if anything moves, abstention improves in order B ≥ C > A.
3. Phase 2: B > A on both abstention and supported-fact use; C's repetition costs naturalness.

If prediction 1 fails — state-side B ≈ A — ordering is not the recurrent bottleneck, and the ask-then-read architecture motivation dies before anyone builds it. That kill is the spike's decisive value; a positive merely upgrades #591 from plausible to measured.

## Read criteria

1. State readout B/D > A ⇒ recurrent selection confirmed as a component of the recall gap; chat_server ask-then-read loop earns a build ticket.
2. State readout flat, behavioral flat ⇒ kill: gap lives in bridge capacity or decoder, not ordering. Ranking/controller work resumes priority.
3. Behavioral moves where state doesn't (capable substrates only) ⇒ ordering effect is prompt-side, not state-side — relevant to the Projektarbeit's Transformer-side order/salience question, the recurrent-side twin of which this spike is.
4. B ≈ D ⇒ the final question-restate is dead weight; pure ask-then-read suffices (cheaper per turn).

## MoCoP relevance

- Decides whether `chat_server.py` needs an ask-then-read loop *before* the substrate swap bakes the old order into the new backbone.
- Monk's provenance note stands: immutable per-turn Mamba state refs make replay order part of provenance.
- Substrate angle: Phase 2 doubles as an ordering-sensitivity row in the swap decision matrix (alongside #592 evidence use and Entry 58 slot armor).

## Scope & safety

Read-only with respect to Alex: frozen packets, no live accumulation, no Qdrant writes, no chat-server mutation, no organic seeding. ML-WS scheduling deferred to Monk's current claim (#611); alpha untouched (no new operating mode — MED rule not triggered, but stated for the record). GPU returned idle afterward; artifacts to `results/jrt_ordering_spike_<date>/` on ML-WS, summarized to the watercooler.
