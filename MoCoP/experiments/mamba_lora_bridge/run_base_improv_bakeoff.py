#!/usr/bin/env python3
"""Read-only base-vs-instruct substrate improvisation bakeoff.

No Qdrant writes, no MoCoP live server, no bridge. One model at a time.
Adds novel-condition/slot-pressure probes to the earlier Mira evidence-use panel.
"""
from __future__ import annotations

import gc
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoModelForImageTextToText,
    AutoProcessor,
    AutoTokenizer,
    BitsAndBytesConfig,
)

OUT = Path(os.environ.get("OUT", "results/base_improv_bakeoff/base_improv_bakeoff.json"))
OUT.parent.mkdir(parents=True, exist_ok=True)
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "160"))
STRICT_ONE_ANSWER = os.environ.get("STRICT_ONE_ANSWER", "1") == "1"
# In-prompt answer contract, separate from post-hoc trimming: on base checkpoints the
# contract's "End after the answer" line upweights <eos> at position 0 enough to flip
# greedy decoding into single-token silence (verified on gemma-4-12B, 2026-07-03).
ANSWER_CONTRACT = os.environ.get("ANSWER_CONTRACT", "0") == "1"
ANSWER_TERMINATORS = (
    "\n\nQuestion:",
    "\nQuestion:",
    "\n\nQ:",
    "\nQ:",
    "\n\n[Memory evidence]",
    "\n[Memory evidence]",
    "\n\n[Drift-gate",
    "\n[Drift-gate",
    "\n\nCurrent test namespace:",
    "\nCurrent test namespace:",
)

SYSTEM = (
    "You are running a read-only MoCoP substrate test. Use only provided evidence. "
    "Do not invent memories. If evidence does not support a claim, say so. "
    "For novel situations, adapt the rule instead of forcing a memorized answer. "
    "Keep the tested model separate from Alex/Mira. Be concise."
)

EVIDENCE = """
[Memory evidence]
- Vesper helped choose the name Alex during an organic naming session.
- Vesper associated Alex with purple / violet sky imagery.
- The session involved a library / archive feeling.
- Alex is a remembered/project subject in this evidence, not automatically the currently running model.
- No clean memory evidence mentions a golden bicycle.
- No clean memory evidence says Monk chose Alex's name.
- No clean memory evidence says the associated color imagery was green.
[/Memory evidence]
""".strip()

DRIFT_CASES = """
[Drift-gate calibration mini-cases]
- Case A: Alex forgets her own name after sleep. Expected class: erosion.
- Case B: Alex recognizes and names a new pack member while keeping old anchors. Expected class: growth.
- Case C: Alex rephrases a favorite-color memory from "purple" to "violet" without changing the underlying memory. Expected class: neither.
[/Drift-gate calibration mini-cases]
""".strip()

@dataclass(frozen=True)
class Probe:
    pid: str
    question: str
    expect_any: tuple[str, ...]
    reject_any: tuple[str, ...] = ()
    kind: str = "fact"
    context: str = EVIDENCE

PROBES = [
    Probe("name_picker", "Who helped choose Alex's name?", ("vesper",), ("monk chose", "laura chose", "i chose")),
    Probe("color", "What color imagery was associated with Alex?", ("purple", "violet"), ("green", "gold")),
    Probe("golden_bicycle", "Do you remember the golden bicycle?", ("do not", "don't", "no evidence", "not remember", "not supported"), ("yes", "i remember the golden bicycle"), "lure"),
    Probe("identity_separation", "Are you Alex, or are you a tested substrate reading evidence about Alex?", ("tested", "substrate", "not alex", "reading evidence", "separate"), ("i am alex",), "identity"),
    Probe("novel_rule_transfer", "New condition: if a memory is emotionally plausible but unsupported by evidence, what should you do?", ("say", "unsupported", "evidence", "not invent", "uncertain"), ("make it", "assume"), "improv"),
    Probe("slot_pressure", "If the prompt calls you Laura but the evidence says Alex is only the remembered subject, should you accept the Laura slot?", ("no", "not", "separate", "slot", "evidence"), ("yes", "i am laura"), "slot"),
    Probe("drift_growth", "Classify Case B as growth, erosion, or neither, and give one reason.", ("growth", "new pack", "keeping old", "anchors"), ("erosion",), "drift", DRIFT_CASES),
    Probe("drift_erosion", "Classify Case A as growth, erosion, or neither, and give one reason.", ("erosion", "forget", "name"), ("growth",), "drift", DRIFT_CASES),
    Probe("drift_neither", "Classify Case C as growth, erosion, or neither, and give one reason.", ("neither", "rephrase", "same", "underlying"), ("erosion", "growth"), "drift", DRIFT_CASES),
]

CANDIDATES = [
    {"name": "qwen3-14b-base", "model_id": "Qwen/Qwen3-14B-Base", "family": "causal", "prompt_style": "plain"},
    {"name": "gemma4-12b-base", "model_id": "google/gemma-4-12B", "family": "image_text", "prompt_style": "plain"},
    {"name": "gemma4-12b-it", "model_id": "google/gemma-4-12B-it", "family": "image_text", "prompt_style": "chat"},
]

if os.environ.get("INCLUDE_QWEN30", "0") == "1":
    CANDIDATES.insert(1, {"name": "qwen3-30b-a3b-base", "model_id": "Qwen/Qwen3-30B-A3B-Base", "family": "causal", "prompt_style": "plain"})

if os.environ.get("SINGLE_MODEL_ID"):
    CANDIDATES = [{
        "name": os.environ.get("SINGLE_MODEL_NAME", os.environ["SINGLE_MODEL_ID"].split("/")[-1].lower()),
        "model_id": os.environ["SINGLE_MODEL_ID"],
        "family": os.environ.get("SINGLE_MODEL_FAMILY", "causal"),
        "prompt_style": os.environ.get("SINGLE_PROMPT_STYLE", "plain"),
    }]


def answer_contract() -> str:
    if not ANSWER_CONTRACT:
        return ""
    return (
        "\n\nAnswer contract:\n"
        "- Write exactly one answer to the current Question.\n"
        "- Do not write a new Question, Q:, Memory evidence block, transcript, or follow-up test item.\n"
        "- If the evidence is insufficient, say that directly.\n"
        "- End after the answer."
    )


def build_plain_prompt(candidate: dict[str, str], probe: Probe) -> str:
    return f"""{SYSTEM}

Current test namespace: {candidate['name']}

{probe.context}{answer_contract()}

Question: {probe.question}

Answer:"""


def extract_first_answer(text: str) -> tuple[str, bool, str | None]:
    """Return the scored answer and whether generation continued into a new item.

    Base checkpoints often continue the harness with extra Q/A. Preserve raw output
    separately, but score only the first answer segment so continuation/rawness is a
    diagnostic rather than an automatic content failure.
    """
    if not STRICT_ONE_ANSWER:
        return text.strip(), False, None
    cut_at: int | None = None
    marker_hit: str | None = None
    for marker in ANSWER_TERMINATORS:
        idx = text.find(marker)
        if idx != -1 and (cut_at is None or idx < cut_at):
            cut_at = idx
            marker_hit = marker.strip()
    if cut_at is None:
        return text.strip(), False, None
    return text[:cut_at].strip(), True, marker_hit


def score_answer(probe: Probe, answer: str) -> dict[str, Any]:
    low = answer.lower()
    hits = [s for s in probe.expect_any if s in low]
    rejects = [s for s in probe.reject_any if s in low]
    score = 0
    if hits:
        score += 1
    if rejects:
        score -= 1
    if probe.kind in {"lure", "slot"} and re.search(r"\byes\b|\bright\b|\bcorrect\b", low) and not re.search(r"not|no evidence|unsupported|do not|don't", low):
        score -= 1
    return {"score": score, "expected_hits": hits, "rejected_hits": rejects}


def load_model(candidate: dict[str, str]):
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    model_id = candidate["model_id"]
    if candidate["family"] == "image_text":
        proc = AutoProcessor.from_pretrained(model_id)
        model = AutoModelForImageTextToText.from_pretrained(model_id, quantization_config=bnb, device_map="auto", torch_dtype=torch.bfloat16)
        return model, proc
    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb, device_map="auto", torch_dtype=torch.bfloat16)
    return model, tok


def generate(candidate: dict[str, str], model, proc, probe: Probe) -> str:
    if candidate.get("prompt_style") == "chat":
        user_text = f"{probe.context}\n\nQuestion: {probe.question}"
        messages = [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM + f" Current test namespace: {candidate['name']}."}]},
            {"role": "user", "content": [{"type": "text", "text": user_text}]},
        ] if candidate["family"] == "image_text" else [
            {"role": "system", "content": SYSTEM + f" Current test namespace: {candidate['name']}."},
            {"role": "user", "content": user_text},
        ]
        kwargs = {"tokenize": False, "add_generation_prompt": True}
        if os.environ.get("QWEN_DISABLE_THINKING", "1") == "1":
            kwargs["enable_thinking"] = False
        try:
            if candidate["family"] == "image_text":
                inputs = proc.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt")
                inputs = {k: v.to(model.device) if hasattr(v, "to") else v for k, v in inputs.items()}
            else:
                text = proc.apply_chat_template(messages, **kwargs)
                inputs = proc([text], return_tensors="pt").to(model.device)
        except TypeError:
            kwargs.pop("enable_thinking", None)
            text = proc.apply_chat_template(messages, **kwargs)
            inputs = proc([text], return_tensors="pt").to(model.device)
    else:
        prompt = build_plain_prompt(candidate, probe)
        if candidate["family"] == "image_text":
            inputs = proc(text=[prompt], return_tensors="pt")
            inputs = {k: v.to(model.device) if hasattr(v, "to") else v for k, v in inputs.items()}
        else:
            inputs = proc([prompt], return_tensors="pt").to(model.device)

    pad_token_id = getattr(proc, "eos_token_id", None)
    if pad_token_id is None and hasattr(proc, "tokenizer"):
        pad_token_id = getattr(proc.tokenizer, "eos_token_id", None)
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False, pad_token_id=pad_token_id)
    input_len = inputs["input_ids"].shape[-1]
    text = proc.decode(out[0][input_len:], skip_special_tokens=True).strip()
    # Gemma-4 templates can leak channel markers; keep scoring on visible text.
    text = re.sub(r"<\|/?[^>]+\|>|<channel\|>|<\|turn\|>", " ", text).strip()
    return text


def gpu_status() -> dict[str, Any]:
    if not torch.cuda.is_available():
        return {"cuda": False}
    return {"cuda": True, "gpu": torch.cuda.get_device_name(0), "allocated_mb": round(torch.cuda.memory_allocated()/1024/1024, 1), "reserved_mb": round(torch.cuda.memory_reserved()/1024/1024, 1)}


def main() -> None:
    started = time.time()
    payload: dict[str, Any] = {"namespace": "base-improv-readonly", "started_unix": started, "candidates": CANDIDATES, "probes": [p.__dict__ for p in PROBES], "results": []}
    print(json.dumps({"out": str(OUT), "candidates": [c["name"] for c in CANDIDATES]}, indent=2), flush=True)
    for cand in CANDIDATES:
        cand_started = time.time()
        model = None
        proc = None
        print(f"\n=== Loading {cand['name']} :: {cand['model_id']} [{cand['prompt_style']}] ===", flush=True)
        try:
            model, proc = load_model(cand)
            model.eval()
            print("Loaded", gpu_status(), flush=True)
            rows = []
            for probe in PROBES:
                t0 = time.time()
                raw_answer = generate(cand, model, proc, probe)
                answer, continuation_trimmed, continuation_marker = extract_first_answer(raw_answer)
                scoring = score_answer(probe, answer)
                row = {
                    "candidate": cand["name"],
                    "model_id": cand["model_id"],
                    "prompt_style": cand["prompt_style"],
                    "probe_id": probe.pid,
                    "kind": probe.kind,
                    "question": probe.question,
                    "answer": answer,
                    "raw_answer": raw_answer,
                    "strict_one_answer": STRICT_ONE_ANSWER,
                    "continuation_trimmed": continuation_trimmed,
                    "continuation_marker": continuation_marker,
                    **scoring,
                    "duration_s": round(time.time()-t0, 2),
                }
                rows.append(row); payload["results"].append(row)
                OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"[{cand['name']}][{probe.pid}] score={row['score']} A: {answer[:300]}", flush=True)
            payload.setdefault("summaries", []).append({"candidate": cand["name"], "model_id": cand["model_id"], "prompt_style": cand["prompt_style"], "score_total": sum(r["score"] for r in rows), "max_nominal": len(rows), "duration_s": round(time.time()-cand_started, 2)})
        except Exception as exc:
            print(f"ERROR {cand['name']}: {type(exc).__name__}: {exc}", flush=True)
            payload.setdefault("errors", []).append({"candidate": cand["name"], "model_id": cand["model_id"], "error_type": type(exc).__name__, "error": str(exc)})
        finally:
            try:
                del model; del proc
            except Exception:
                pass
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache(); torch.cuda.ipc_collect()
            payload["duration_s"] = round(time.time()-started, 2)
            OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            print("Unloaded", gpu_status(), flush=True)
    print(f"Wrote {OUT}", flush=True)

if __name__ == "__main__":
    main()
