#!/usr/bin/env python3
"""
d2_private_recall_eval_expanded.py

Expanded validation for D2 explicit cue-based recall.
Broader probe set to test whether c0fde05 ranking fix generalizes.

Based on d2_private_recall_eval.py with additional autobiographical cases.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from urllib import error, request


CASES = [
    # Original cases from Techno-Monk
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
    # New cases for broader validation
    {
        "label": "rain_stone_walls",
        "query": "rain old stone walls calm",
        "question": "What makes me feel calm that I mentioned earlier?",
        "expected_recall_any": ["rain", "stone walls", "calm"],
        "expected_answer_any": ["rain", "stone", "calm"],
    },
    {
        "label": "pistachio_croissant",
        "query": "pistachio croissant bakery corner favorite",
        "question": "What's my favorite croissant?",
        "expected_recall_any": ["pistachio", "croissant", "bakery"],
        "expected_answer_any": ["pistachio", "croissant"],
    },
    {
        "label": "house_build_excavators",
        "query": "house build April excavators started",
        "question": "When did the house build start?",
        "expected_recall_any": ["april", "excavator", "house", "started"],
        "expected_answer_any": ["april", "14", "excavator"],
    },
    {
        "label": "ketosis_kerastase",
        "query": "ketosis Kerastase mix up 2 AM",
        "question": "What do I sometimes mix up, especially late at night?",
        "expected_recall_any": ["ketosis", "kerastase", "mix"],
        "expected_answer_any": ["ketosis", "kerastase"],
    },
    {
        "label": "cat_coffee",
        "query": "cat knocked coffee morning",
        "question": "What happened with the cat this morning?",
        "expected_recall_any": ["cat", "coffee", "knocked"],
        "expected_answer_any": ["cat", "coffee", "knocked"],
    },
    {
        "label": "danish_house_style",
        "query": "Danish Murermestervilla house style prefer",
        "question": "What architectural style do I prefer for the new house?",
        "expected_recall_any": ["danish", "murermestervilla"],
        "expected_answer_any": ["danish", "murermestervilla"],
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
    parser = argparse.ArgumentParser(description="Expanded D2 recall validation.")
    parser.add_argument("--base-url", default="http://127.0.0.1:7860")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--recall-limit", type=int, default=3)
    args = parser.parse_args()

    print(f"=== D2 Expanded Recall Validation ({len(CASES)} cases) ===\n")

    results = []
    for case in CASES:
        print(f"Testing: {case['label']}...")
        result = evaluate_case(args.base_url, case, args.timeout_s, args.recall_limit)
        results.append(result)
        status = "PASS" if result["retrieval_hit"] and result["answer_hit"] else "FAIL"
        print(f"  retrieval={result['retrieval_hit']}, answer={result['answer_hit']} [{status}]")

    retrieval_hits = sum(1 for row in results if row["retrieval_hit"])
    answer_hits = sum(1 for row in results if row["answer_hit"])
    explicit_hits = sum(1 for row in results if row["explicit_memory_language"])

    summary = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "base_url": args.base_url,
        "case_count": len(results),
        "cases": results,
        "retrieval_hit_at_k": retrieval_hits / len(results) if results else 0.0,
        "answer_accuracy": answer_hits / len(results) if results else 0.0,
        "explicit_memory_language_rate": explicit_hits / len(results) if results else 0.0,
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== Summary ===")
    print(
        f"retrieval_hit@{args.recall_limit} = {retrieval_hits}/{len(results)} ({100*retrieval_hits/len(results):.0f}%)"
    )
    print(
        f"answer_accuracy = {answer_hits}/{len(results)} ({100*answer_hits/len(results):.0f}%)"
    )
    print(
        f"explicit_memory_language = {explicit_hits}/{len(results)} ({100*explicit_hits/len(results):.0f}%)"
    )
    print(f"\nSaved report to {output_path}")


if __name__ == "__main__":
    main()
