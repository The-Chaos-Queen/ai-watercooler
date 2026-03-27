#!/usr/bin/env python3
"""
d2_private_recall_eval.py

Validate D2 explicit cue-based recall against chat_server's private /recall path.

This is intentionally explicit, not autonomous:
- query the private hippocampus directly
- then ask the same question with recall injected into /chat
- score retrieval hit@k and answer usefulness on definitely-present memories
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from urllib import error, request


CASES = [
    {
        "label": "fragile_today",
        "query": "fragile today awake 2 AM",
        "question": "What did I tell you earlier about my condition today?",
        "expected_recall_any": ["fragile", "2 am", "awake until 2 am"],
        "expected_answer_any": ["fragile", "2 am", "awake"],
    },
    {
        "label": "harness_dead_inside",
        "query": "dead inside harness grabs the wheel",
        "question": "What did I tell you earlier about the harness making you sound dead inside?",
        "expected_recall_any": ["dead inside", "harness"],
        "expected_answer_any": ["dead inside", "harness"],
    },
]


def post_json(base_url: str, path: str, payload: dict, timeout_s: float) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def contains_any(text: str, needles) -> bool:
    haystack = str(text or "").lower()
    return any(str(needle).lower() in haystack for needle in needles)


def evaluate_case(base_url: str, case: dict, timeout_s: float, recall_limit: int) -> dict:
    recall_data = post_json(
        base_url,
        "/recall",
        {
            "query": case["query"],
            "limit": recall_limit,
        },
        timeout_s,
    )
    chat_data = post_json(
        base_url,
        "/chat",
        {
            "message": case["question"],
            "use_recall": True,
            "recall_query": case["query"],
            "recall_limit": recall_limit,
        },
        timeout_s,
    )

    recall_text = json.dumps(recall_data.get("results", []), ensure_ascii=False)
    answer_text = str(chat_data.get("response", "") or "")
    retrieval_hit = contains_any(recall_text, case["expected_recall_any"])
    answer_hit = contains_any(answer_text, case["expected_answer_any"])
    explicit_memory_language = contains_any(
        answer_text,
        ["earlier", "you said", "you told me", "i remember", "you mentioned"],
    )

    return {
        "label": case["label"],
        "query": case["query"],
        "question": case["question"],
        "retrieval_hit": retrieval_hit,
        "answer_hit": answer_hit,
        "explicit_memory_language": explicit_memory_language,
        "recall_count": int(recall_data.get("count", 0) or 0),
        "top_score": (
            round(float(recall_data["results"][0].get("score", 0.0) or 0.0), 6)
            if recall_data.get("results")
            else None
        ),
        "recall_results": recall_data.get("results", []),
        "response": answer_text,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate D2 explicit cue-based recall.")
    parser.add_argument("--base-url", default="http://127.0.0.1:7860")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--recall-limit", type=int, default=3)
    args = parser.parse_args()

    results = [
        evaluate_case(args.base_url, case, args.timeout_s, args.recall_limit)
        for case in CASES
    ]
    retrieval_hits = sum(1 for row in results if row["retrieval_hit"])
    answer_hits = sum(1 for row in results if row["answer_hit"])
    explicit_hits = sum(1 for row in results if row["explicit_memory_language"])

    summary = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "base_url": args.base_url,
        "cases": results,
        "retrieval_hit_at_k": retrieval_hits / len(results) if results else 0.0,
        "answer_accuracy": answer_hits / len(results) if results else 0.0,
        "explicit_memory_language_rate": explicit_hits / len(results) if results else 0.0,
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        "D2 recall eval: "
        f"retrieval_hit@{args.recall_limit}={retrieval_hits}/{len(results)}, "
        f"answer_accuracy={answer_hits}/{len(results)}, "
        f"explicit_memory_language={explicit_hits}/{len(results)}"
    )
    print(f"Saved report to {output_path}")


if __name__ == "__main__":
    main()
