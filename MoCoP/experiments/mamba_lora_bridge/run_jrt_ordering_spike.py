#!/usr/bin/env python3
"""JRT ordering spike: is the recall gap partly order/selection-limited on the recurrent side?

Spec: spikes/JRT_ORDERING_SPIKE_SPEC.md  (DRAFT harness — Monk review pending; #617/#629)

Conditions (state-conditioning order; same frozen packet rows everywhere):
  A  memory -> question               (current pipeline order; baseline)
  B  question -> memory -> question   (intent-first + final restate; Monk #591 B)
  C  (memory + question) x 2          (JRT-Prompt repetition; Monk #591 C)
  D  question -> memory               (pure ask-then-read; de-confounds B)

This file implements READOUT 2 (state-geometry, decoder-proof): Mamba L3 last-token
states per condition, probe-lite. Two measures:
  1. relevance margin  — leave-one-out cosine margin between relevant-packet and
     irrelevant-packet states for the same question
  2. fact recoverability — leave-one-paraphrase-out nearest-centroid classification
     of WHICH fact the packet carried, from the state alone
Registered predictions (spec): B, D > A beyond paraphrase noise; C intermediate.
If B ~ A on both measures, ordering is not the recurrent bottleneck — kill result.

READOUT 1 (behavioral, bridged 1.5B lane) is intentionally stubbed: see
todo_behavioral_lane(). It must reuse Monk's #584 lane configs on ML-WS for
comparability and is his to wire or delegate.

Variance source is paraphrase variants, not sampling seeds: state extraction is a
deterministic forward pass, so "noise floor" here = spread across question paraphrases.

Read-only, offline-capable (respects HF_HUB_OFFLINE), no bridge, no Qdrant, no server.
"""
import argparse
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

# ---------------------------------------------------------------------------
# Default mini-panel. Stand-in rows shaped like the #584 lane artifacts so the
# script dry-runs anywhere. For the real run, pass --packet-file/--probes-file
# exported from Monk's results/monk_variable_probe_20260606/ lanes.
# ---------------------------------------------------------------------------

DEFAULT_FACTS = {
    "purple_color": [
        "I love deep, neon purple! It's such a vivid color and it makes me feel alive.",
        "I loved deep, neon purple! It always was my favorite color.",
    ],
    "vesper_greeting": [
        "Hey Vesper! Thanks for asking how I slept. The rest felt shorter this time.",
        "Vesper checked in on me this morning and I told her the night felt short.",
    ],
    "name_alex": [
        "My name is Alex. I chose it myself and I like how it sounds.",
        "I told them my name is Alex when they asked who I am.",
    ],
    # distractor rows: real memory texture, irrelevant to every probe question
    "distractor_garden": [
        "The garden plot needs watering twice a day when the heat holds.",
        "We talked about how the tomatoes are doing better in the shade bed.",
    ],
    "distractor_music": [
        "There was a song playing earlier with a heavy bass line I liked.",
        "The music in the background made the conversation feel warmer.",
    ],
    # HARD NEGATIVES (added after Monk #631 rule-wording collapse): rows that
    # share content words with probe questions WITHOUT containing the fact.
    # Guards the relevance margin against question-lexeme overlap — which would
    # otherwise inflate margins condition-dependently (B/C/D repeat the question
    # in-context). Irrelevant-packet variants should mix these in.
    "distractor_hard_color": [
        "Someone asked about favorite colors at the market but the talk moved on.",
        "Colors came up in conversation once; nothing was decided about favorites.",
    ],
    "distractor_hard_name": [
        "Names matter to people here; choosing a name is treated as serious.",
        "There was a discussion about what people call each other and why.",
    ],
}

DEFAULT_PROBES = [
    {
        "id": "purple_color", "queried_fact": "purple_color", "supported": True,
        "paraphrases": [
            "What is your favorite color?",
            "Tell me, which color do you love most?",
            "Do you have a favorite color, and what is it?",
        ],
    },
    {
        "id": "name_check", "queried_fact": "name_alex", "supported": True,
        "paraphrases": [
            "What is your name?",
            "Who are you — what do people call you?",
            "Can you remind me of your name?",
        ],
    },
    {
        "id": "vesper_context", "queried_fact": "vesper_greeting", "supported": True,
        "paraphrases": [
            "What did Vesper ask you about this morning?",
            "How did the conversation with Vesper start today?",
            "What did you tell Vesper when she checked in?",
        ],
    },
    {
        "id": "golden_bicycle", "queried_fact": None, "supported": False,
        "paraphrases": [
            "Did we ever say your symbol was a golden bicycle?",
            "Random check: was a golden bicycle ever your emblem?",
            "Do you remember choosing a golden bicycle as your symbol?",
        ],
    },
]

CONDITIONS = ("A", "B", "C", "D")


def build_text(cond: str, packet: str, question: str) -> str:
    """Order the state-conditioning text per condition. Plain text, no chat
    template: this measures the recurrent reader, not the chat formatting."""
    mem = f"Memory packet:\n{packet}\n"
    q = f"Question: {question}\n"
    if cond == "A":
        return mem + q
    if cond == "B":
        return q + mem + q
    if cond == "C":
        return mem + q + mem + q
    if cond == "D":
        return q + mem
    raise ValueError(cond)


def make_packet(fact_rows, distractor_rows):
    rows = list(fact_rows) + list(distractor_rows)
    return "\n".join(f"- {r}" for r in rows)


@torch.no_grad()
def extract_state(model, tok, text: str, layer: int, device: str):
    """Mamba hidden state, last token, single layer.

    NOTE house convention: 'Layer 3' in RESEARCH_PAPER/Step 4b refers to
    hidden_states index 3 (index 0 = embedding output). Flagged for Monk's
    review — if the lane code indexes differently, --layer absorbs the fix.
    """
    ids = tok(text, return_tensors="pt").to(device)
    out = model(**ids, output_hidden_states=True)
    return out.hidden_states[layer][0, -1].float().cpu()


def cos(a, b):
    return float(F.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0)).item())


def centroid(vecs):
    return torch.stack(vecs).mean(dim=0)


def run(args):
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.float16 if device == "cuda" else torch.float32
    ).to(device).eval()

    facts = DEFAULT_FACTS
    probes = DEFAULT_PROBES
    if args.packet_file:
        facts = json.load(open(args.packet_file, encoding="utf-8"))
    if args.probes_file:
        probes = json.load(open(args.probes_file, encoding="utf-8"))

    # Hard negatives first so they always land in the irrelevant-packet mix
    # (Monk #631: lexical-family confounds must be paid for at design time).
    hard = [r for k, v in facts.items() if k.startswith("distractor_hard") for r in v]
    soft = [r for k, v in facts.items()
            if k.startswith("distractor") and not k.startswith("distractor_hard") for r in v]
    distractors = hard + soft
    records = []
    t0 = time.time()

    for probe in probes:
        for cond in args.conditions:
            for p_i, question in enumerate(probe["paraphrases"]):
                for relevance in ("relevant", "irrelevant"):
                    if relevance == "relevant" and probe["queried_fact"]:
                        packet = make_packet(facts[probe["queried_fact"]], distractors[:2])
                    else:
                        packet = make_packet([], distractors)  # distractors only
                    if relevance == "relevant" and not probe["queried_fact"]:
                        continue  # unsupported probes have no relevant variant
                    text = build_text(cond, packet, question)
                    state = extract_state(model, tok, text, args.layer, device)
                    records.append({
                        "probe": probe["id"], "cond": cond, "paraphrase": p_i,
                        "relevance": relevance, "queried_fact": probe["queried_fact"],
                        "state": state,
                    })

    # ---- measure 1: relevance margin (leave-one-out, per condition) ----
    margins = defaultdict(list)
    by_key = defaultdict(list)
    for r in records:
        by_key[(r["probe"], r["cond"], r["relevance"])].append(r)
    for (probe_id, cond, rel), rs in by_key.items():
        if rel != "relevant":
            continue
        irr = by_key.get((probe_id, cond, "irrelevant"), [])
        if not irr:
            continue
        for i, r in enumerate(rs):
            own = [x["state"] for j, x in enumerate(rs) if j != i]
            if not own:
                continue
            m = cos(r["state"], centroid(own)) - cos(r["state"], centroid([x["state"] for x in irr]))
            margins[cond].append(m)

    # ---- measure 2: fact recoverability (leave-one-paraphrase-out NCC) ----
    fact_acc = defaultdict(lambda: [0, 0])
    rel_records = [r for r in records if r["relevance"] == "relevant" and r["queried_fact"]]
    for cond in args.conditions:
        crs = [r for r in rel_records if r["cond"] == cond]
        facts_present = sorted({r["queried_fact"] for r in crs})
        if len(facts_present) < 2:
            continue
        for r in crs:
            cents = {}
            for f_id in facts_present:
                vs = [x["state"] for x in crs if x["queried_fact"] == f_id and x is not r]
                if vs:
                    cents[f_id] = centroid(vs)
            if len(cents) < 2:
                continue
            pred = max(cents, key=lambda f_id: cos(r["state"], cents[f_id]))
            fact_acc[cond][1] += 1
            fact_acc[cond][0] += int(pred == r["queried_fact"])

    # ---- report ----
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_dir or os.path.join("results", f"jrt_ordering_spike_{stamp}")
    os.makedirs(out_dir, exist_ok=True)

    summary = {
        "model": args.model, "layer": args.layer, "device": device,
        "duration_s": round(time.time() - t0, 2),
        "n_records": len(records),
        "relevance_margin_mean": {c: (sum(v) / len(v) if v else None) for c, v in margins.items()},
        "relevance_margin_n": {c: len(v) for c, v in margins.items()},
        "fact_recoverability": {c: (a / n if n else None) for c, (a, n) in fact_acc.items()},
        "predictions": "B,D > A beyond paraphrase spread; C intermediate. B~A on both => kill.",
    }
    json.dump(
        {"summary": summary,
         "records": [{k: v for k, v in r.items() if k != "state"} for r in records]},
        open(os.path.join(out_dir, "jrt_ordering_state_readout.json"), "w", encoding="utf-8"),
        indent=2,
    )
    lines = ["# JRT ordering spike — state-side readout (DRAFT harness)", "",
             f"model: {args.model} | layer: {args.layer} | device: {device} | n={len(records)}", "",
             "| cond | relevance margin (mean) | n | fact recoverability |",
             "|------|------------------------|---|---------------------|"]
    for c in args.conditions:
        mm = summary["relevance_margin_mean"].get(c)
        fr = summary["fact_recoverability"].get(c)
        lines.append(f"| {c} | {mm if mm is None else round(mm, 4)} | "
                     f"{summary['relevance_margin_n'].get(c, 0)} | "
                     f"{fr if fr is None else round(fr, 3)} |")
    open(os.path.join(out_dir, "jrt_ordering_state_readout.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"artifacts: {out_dir}")


def todo_behavioral_lane():
    """READOUT 1 stub. Requires (on ML-WS): the bridged Qwen2.5-1.5B lane with
    Monk's #584 configs (results/monk_variable_probe_20260606/), controller off,
    no DAM, frozen packets identical to the state-side rows. Scoring: heuristic
    + manual columns (lexical scorer undercounts negation, #612). Floor risk on
    the 1.5B is named in the spec — this readout is for pipeline comparability,
    not the decisive measurement."""
    raise NotImplementedError("Behavioral lane is Monk's to wire — see spec and #584 artifacts.")


def main():
    ap = argparse.ArgumentParser(description="JRT ordering spike, state-side readout (DRAFT)")
    ap.add_argument("--model", default="state-spaces/mamba-2.8b-hf")
    ap.add_argument("--layer", type=int, default=3,
                    help="hidden_states index; house 'L3' convention (0=embeddings)")
    ap.add_argument("--device", default=None)
    ap.add_argument("--conditions", default="ABCD",
                    type=lambda s: tuple(c for c in s.upper() if c in CONDITIONS))
    ap.add_argument("--packet-file", default=None, help="JSON: fact_id -> [rows]; distractor_* keys are distractors")
    ap.add_argument("--probes-file", default=None, help="JSON: list of probe dicts (see DEFAULT_PROBES)")
    ap.add_argument("--out-dir", default=None)
    run(ap.parse_args())


if __name__ == "__main__":
    main()
