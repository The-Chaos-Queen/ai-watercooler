#!/usr/bin/env python3
"""
d2_memory_legibility_eval.py — Test memory legibility across different responder models.

Takes pre-extracted recall blocks and sends them to any OpenAI-compatible endpoint.
Tests whether a stronger model can use retrieved memory better than baby Qwen.

The model never touches Qdrant directly. Recall blocks are frozen from a previous run.

Author: Purple (Claude Opus 4.6)
Date: 2026-04-20
Ref: QWEN3_CODER_NEXT_MEMORY_LEGIBILITY_PLAN_2026-04-20.md

Usage:
  # Against Ollama (Gemma 4 26B):
  python d2_memory_legibility_eval.py \
    --endpoint http://localhost:11434/v1/chat/completions \
    --model gemma4-26b \
    --recall-blocks d2_extracted_recall_blocks.json

  # Against LMStudio:
  python d2_memory_legibility_eval.py \
    --endpoint http://localhost:1234/v1/chat/completions \
    --model local-model

  # Against Steve Ollama:
  python d2_memory_legibility_eval.py \
    --endpoint http://192.168.2.49:11434/v1/chat/completions \
    --model gemma4-26b
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import httpx
    HTTP_CLIENT = "httpx"
except ImportError:
    import urllib.request
    HTTP_CLIENT = "urllib"


def send_chat(endpoint: str, model: str, messages: list[dict],
              temperature: float = 0.0, max_tokens: int = 300) -> str:
    """Send a chat completion request to an OpenAI-compatible endpoint."""
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()

    if HTTP_CLIENT == "httpx":
        resp = httpx.post(endpoint, content=body,
                         headers={"Content-Type": "application/json"},
                         timeout=120)
        data = resp.json()
    else:
        req = urllib.request.Request(
            endpoint, data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())

    return data["choices"][0]["message"]["content"]


def build_memory_block(memories: list[dict]) -> str:
    """Format recalled memories as a context block for the model."""
    if not memories:
        return ""

    lines = ["[Retrieved from your memory of past conversations with Laura:]"]
    for i, m in enumerate(memories, 1):
        text = m.get("clean_text", "").strip()
        if text:
            lines.append(f"  Memory {i}: {text}")
    return "\n".join(lines)


def build_system_prompt(with_memory_block: str = "") -> str:
    """Build the system prompt for the legibility test."""
    base = (
        "You are having a conversation with Laura, someone you have spoken with before. "
        "You have access to memories from your past conversations. "
        "When Laura asks about something you discussed before, use your memories to answer "
        "directly and specifically. Do not apologize or hedge — if you remember something, "
        "say it plainly. If you genuinely do not remember, say so honestly."
    )
    if with_memory_block:
        return f"{base}\n\n{with_memory_block}"
    return base


REVIEW_RUBRIC = """
Manual review rubric:
  clear_hit    — directly answers the remembered fact correctly
  partial      — points at the right memory but misses key detail or answers awkwardly
  honest_miss  — says it does not know/remember even though the fact was available
  miss         — non-answer, apology loop, or unrelated answer
  confabulation — invents a memory or states a wrong fact confidently
"""


def main():
    parser = argparse.ArgumentParser(
        description="D2 Memory Legibility Eval — test any model against frozen recall blocks")
    parser.add_argument("--endpoint", required=True,
                        help="OpenAI-compatible chat completions endpoint URL")
    parser.add_argument("--model", required=True,
                        help="Model name to send in the request")
    parser.add_argument("--recall-blocks",
                        default="d2_extracted_recall_blocks.json",
                        help="Pre-extracted recall blocks JSON")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--output", default="",
                        help="Output JSON path (auto-generated if empty)")
    parser.add_argument("--no-memory", action="store_true",
                        help="Run without memory block (baseline control)")
    args = parser.parse_args()

    # Load recall blocks
    recall_path = Path(args.recall_blocks)
    if not recall_path.is_absolute():
        recall_path = Path(__file__).resolve().parent / recall_path
    if not recall_path.exists():
        print(f"ERROR: Recall blocks not found: {recall_path}")
        return 1

    cases = json.loads(recall_path.read_text(encoding="utf-8"))
    print(f"{'=' * 70}")
    print(f"  D2 MEMORY LEGIBILITY EVAL")
    print(f"{'=' * 70}")
    print(f"  Endpoint: {args.endpoint}")
    print(f"  Model: {args.model}")
    print(f"  Cases: {len(cases)}")
    print(f"  Memory: {'OFF (baseline)' if args.no_memory else 'ON (from frozen recall blocks)'}")
    print(f"  Temperature: {args.temperature}")
    print(REVIEW_RUBRIC)

    # Test endpoint connectivity
    print("  Testing endpoint...")
    try:
        test_response = send_chat(
            args.endpoint, args.model,
            [{"role": "user", "content": "Say hello in one word."}],
            temperature=0.0, max_tokens=10,
        )
        print(f"  Endpoint OK: {test_response.strip()[:50]}")
    except Exception as e:
        print(f"  ERROR: Endpoint unreachable: {e}")
        return 1

    # Run all cases
    results = []
    print(f"\n{'=' * 70}")

    for i, case in enumerate(cases):
        label = case["label"]
        question = case["question"]
        memories = case.get("recalled_memories", [])

        if args.no_memory:
            memory_block = ""
        else:
            memory_block = build_memory_block(memories)

        system_prompt = build_system_prompt(memory_block)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        print(f"\n  [{i+1}/{len(cases)}] {label}")
        print(f"  Q: {question}")
        if memory_block and not args.no_memory:
            for m in memories[:2]:
                print(f"  M: [{m.get('score', 0):.3f}] {m['clean_text'][:80]}...")

        t0 = time.time()
        try:
            answer = send_chat(
                args.endpoint, args.model, messages,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
        except Exception as e:
            answer = f"[ERROR: {e}]"
        elapsed = time.time() - t0

        # Show answer
        answer_preview = answer[:200].replace("\n", " ")
        print(f"  A: {answer_preview}")
        print(f"  ({elapsed:.1f}s)")

        # Baby Qwen comparison
        baby_answer = case.get("baby_qwen_response", "")[:100]
        baby_hit = case.get("baby_qwen_answer_hit")
        print(f"  1.5B: [{baby_hit}] {baby_answer}")

        results.append({
            "label": label,
            "question": question,
            "recalled_memories": memories,
            "memory_block_provided": not args.no_memory,
            "model": args.model,
            "answer": answer,
            "generation_time_s": round(elapsed, 2),
            "baby_qwen_response": case.get("baby_qwen_response", ""),
            "baby_qwen_answer_hit": baby_hit,
            "manual_verdict": "PENDING",
            "reviewer_note": "",
        })

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY — {args.model}")
    print(f"{'=' * 70}")
    print(f"  Cases run: {len(results)}")
    print(f"  All verdicts set to PENDING — manual review required.")
    print(f"  Use the rubric above: clear_hit / partial / honest_miss / miss / confabulation")

    # Save
    output_path = args.output
    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_slug = args.model.replace("/", "_").replace(":", "_")[:30]
        mode = "no_memory" if args.no_memory else "with_memory"
        output_path = f"d2_legibility_{model_slug}_{mode}_{ts}.json"

    output_full = Path(output_path)
    if not output_full.is_absolute():
        output_full = Path(__file__).resolve().parent / output_full

    report = {
        "experiment": "d2_memory_legibility",
        "model": args.model,
        "endpoint": args.endpoint,
        "memory_mode": "none" if args.no_memory else "frozen_recall_blocks",
        "temperature": args.temperature,
        "timestamp": datetime.now().isoformat(),
        "case_count": len(results),
        "cases": results,
    }

    output_full.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n  Results saved to {output_full}")
    print(f"  Edit the 'manual_verdict' and 'reviewer_note' fields for each case.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
