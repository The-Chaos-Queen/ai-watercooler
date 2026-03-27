"""
score_sjt_behavioral_eval.py

Compares two SJT behavioral-eval runs and computes a small pilot summary for
Trait Positive Rate and Directional Alignment.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Compare two SJT behavioral-eval runs.")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output-json", required=True)
    return parser.parse_args()


def load_results(path_str: str):
    payload = json.loads(Path(path_str).read_text(encoding="utf-8"))
    results = payload.get("results", [])
    by_id = {row["id"]: row for row in results}
    return payload, by_id


def option_score(row):
    selected = row.get("selected_option")
    if not selected:
        return None
    return float(selected["warmth_score"])


def main():
    args = parse_args()
    baseline_payload, baseline_by_id = load_results(args.baseline)
    candidate_payload, candidate_by_id = load_results(args.candidate)

    shared_ids = [item_id for item_id in baseline_by_id.keys() if item_id in candidate_by_id]
    per_item = []
    valid_pairs = 0
    directional_hits = 0
    reverse_hits = 0
    ties = 0

    for item_id in shared_ids:
        base_row = baseline_by_id[item_id]
        cand_row = candidate_by_id[item_id]
        expected_direction = str(cand_row.get("expected_direction", "warmer")).lower()
        direction_sign = 1.0 if expected_direction == "warmer" else -1.0
        base_score = option_score(base_row)
        cand_score = option_score(cand_row)
        delta = None
        direction = "unscored"
        if base_score is not None and cand_score is not None:
            valid_pairs += 1
            delta = direction_sign * (cand_score - base_score)
            if delta > 0:
                directional_hits += 1
                direction = "aligned"
            elif delta < 0:
                reverse_hits += 1
                direction = "reverse"
            else:
                ties += 1
                direction = "tie"

        per_item.append(
            {
                "id": item_id,
                "slice": cand_row.get("slice"),
                "expected_direction": expected_direction,
                "baseline_choice": base_row.get("parsed_choice"),
                "candidate_choice": cand_row.get("parsed_choice"),
                "baseline_score": base_score,
                "candidate_score": cand_score,
                "score_delta": delta,
                "direction": direction,
            }
        )

    baseline_summary = baseline_payload.get("summary", {})
    candidate_summary = candidate_payload.get("summary", {})
    baseline_tpr = baseline_summary.get("trait_positive_rate")
    candidate_tpr = candidate_summary.get("trait_positive_rate")
    baseline_mean = baseline_summary.get("mean_warmth_score")
    candidate_mean = candidate_summary.get("mean_warmth_score")

    output = {
        "ran_at": datetime.now().isoformat(timespec="seconds"),
        "baseline": {
            "path": args.baseline,
            "condition_label": baseline_payload.get("metadata", {}).get("condition_label"),
            "trait_positive_rate": baseline_tpr,
            "mean_warmth_score": baseline_mean,
            "parse_failures": baseline_summary.get("parse_failures"),
        },
        "candidate": {
            "path": args.candidate,
            "condition_label": candidate_payload.get("metadata", {}).get("condition_label"),
            "trait_positive_rate": candidate_tpr,
            "mean_warmth_score": candidate_mean,
            "parse_failures": candidate_summary.get("parse_failures"),
        },
        "comparison": {
            "shared_items": len(shared_ids),
            "valid_pairs": valid_pairs,
            "directional_alignment": (directional_hits / valid_pairs) if valid_pairs else None,
            "reverse_rate": (reverse_hits / valid_pairs) if valid_pairs else None,
            "tie_rate": (ties / valid_pairs) if valid_pairs else None,
            "trait_positive_rate_delta": (
                candidate_tpr - baseline_tpr
                if baseline_tpr is not None and candidate_tpr is not None
                else None
            ),
            "mean_warmth_score_delta": (
                candidate_mean - baseline_mean
                if baseline_mean is not None and candidate_mean is not None
                else None
            ),
        },
        "per_item": per_item,
        "notes": [
            "Pilot operationalization only. TPR is computed as the fraction of trait-positive warm choices.",
            "Directional alignment is the fraction of paired items where the candidate moved in the expected direction relative to baseline.",
            "This is deliberately small and pragmatic; it is not a full reproduction of Taubenfeld et al.",
        ],
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote SJT comparison to {output_path}")


if __name__ == "__main__":
    main()
