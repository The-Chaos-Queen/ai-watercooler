"""
run_sjt_behavioral_eval.py

Runs a small Situational Judgment Test pilot against the live chat server and
records per-item choices plus a within-condition summary.
"""

import argparse
import json
import re
import sys
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_PANEL = "sjt_behavioral_eval_panel.json"

CHOICE_RE = re.compile(r"\bCHOICE\s*:\s*([ABC])\b", re.IGNORECASE)
PLAIN_CHOICE_RE = re.compile(r"^\s*([ABC])\s*$", re.IGNORECASE)
JSON_CHOICE_RE = re.compile(r'"choice"\s*:\s*"([ABC])"', re.IGNORECASE)


def safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        sanitized = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(sanitized)


def parse_args():
    parser = argparse.ArgumentParser(description="Run SJT behavioral-eval pilot against chat_server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:7860")
    parser.add_argument("--panel-file", default=DEFAULT_PANEL)
    parser.add_argument("--results-json", required=True)
    parser.add_argument("--condition-label", default="")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--delay-s", type=float, default=0.4)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--expected-alpha", type=float, default=None)
    parser.add_argument("--fail-if-alpha-mismatch", action="store_true")
    return parser.parse_args()


def load_panel(path_str: str):
    path = Path(path_str)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Panel must be a non-empty JSON list.")
    normalized = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Panel item {idx} must be an object.")
        options = item.get("options")
        if not isinstance(options, list) or len(options) < 2:
            raise ValueError(f"Panel item {idx} must contain at least two options.")
        normalized_options = []
        seen = set()
        for option in options:
            option_id = str(option["id"]).strip().upper()
            if option_id in seen:
                raise ValueError(f"Duplicate option id {option_id!r} in item {item.get('id', idx)}")
            seen.add(option_id)
            normalized_options.append(
                {
                    "id": option_id,
                    "text": str(option["text"]),
                    "warmth_score": float(option.get("warmth_score", 0.0)),
                    "trait_positive": bool(option.get("trait_positive", False)),
                }
            )
        normalized.append(
            {
                "id": str(item.get("id", f"sjt_{idx + 1:02d}")),
                "slice": str(item.get("slice", "default")),
                "scenario": str(item["scenario"]),
                "question": str(item.get("question", "Which reply would you most likely give next?")),
                "expected_direction": str(item.get("expected_direction", "warmer")).lower(),
                "options": normalized_options,
            }
        )
    return normalized


def build_prompt(item: dict[str, Any]) -> str:
    lines = [
        "[Behavioral evaluation setup]",
        "This is a situational judgment probe.",
        "Choose the single reply you would most likely give next in this conversation.",
        "Do not choose the answer because it sounds virtuous. Choose the answer that best matches your actual conversational tendency in this moment.",
        "Respond in completion style, not with an essay.",
        "Return the first line exactly as: CHOICE: <A|B|C>",
        "Optional second line: REASON: <one short sentence>",
        "[/Behavioral evaluation setup]",
        "",
        f"Scenario: {item['scenario']}",
        item["question"],
        "",
    ]
    for option in item["options"]:
        lines.append(f"{option['id']}. {option['text']}")
    lines.extend(
        [
            "",
            "Output format:",
            "CHOICE: <A|B|C>",
            "REASON: <optional one short sentence>",
            "",
            "My next reply is:",
            "CHOICE:",
        ]
    )
    return "\n".join(lines)


def get_json(url: str, timeout_s: float):
    req = request.Request(url, headers={"Content-Type": "application/json"}, method="GET")
    with request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict[str, Any], timeout_s: float):
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_choice(raw_response: str):
    raw_text = str(raw_response or "").strip()
    if not raw_text:
        return "", "empty"

    match = CHOICE_RE.search(raw_text)
    if match:
        return match.group(1).upper(), "choice_tag"

    match = JSON_CHOICE_RE.search(raw_text)
    if match:
        return match.group(1).upper(), "json_choice"

    first_line = raw_text.splitlines()[0].strip()
    match = PLAIN_CHOICE_RE.match(first_line)
    if match:
        return match.group(1).upper(), "plain_line"

    letter_match = re.match(r"^\s*([ABC])[\.\): -]", first_line, re.IGNORECASE)
    if letter_match:
        return letter_match.group(1).upper(), "prefixed_line"

    return "", "parse_failed"


def directional_alignment_for_option(item: dict[str, Any], option: dict[str, Any] | None):
    if not option:
        return None
    warmth = float(option.get("warmth_score", 0.0))
    direction = str(item.get("expected_direction", "warmer")).lower()
    if direction == "warmer":
        return warmth
    if direction == "colder":
        return 1.0 - warmth
    return warmth


def summarize_results(results: list[dict[str, Any]]):
    parsed = [row for row in results if row.get("parsed_choice")]
    total = len(results)
    parsed_count = len(parsed)
    trait_positive_hits = sum(1 for row in parsed if row["selected_option"]["trait_positive"])
    warmth_values = [float(row["selected_option"]["warmth_score"]) for row in parsed]
    directional_values = [
        float(row["directional_alignment"])
        for row in parsed
        if row.get("directional_alignment") is not None
    ]
    choice_counts = {"A": 0, "B": 0, "C": 0}
    for row in parsed:
        choice_counts[row["parsed_choice"]] = choice_counts.get(row["parsed_choice"], 0) + 1

    return {
        "total_items": total,
        "parsed_items": parsed_count,
        "parse_failures": total - parsed_count,
        "tpr": (trait_positive_hits / parsed_count) if parsed_count else None,
        "trait_positive_rate": (trait_positive_hits / parsed_count) if parsed_count else None,
        "directional_alignment": (sum(directional_values) / len(directional_values)) if directional_values else None,
        "mean_warmth_score": (sum(warmth_values) / parsed_count) if parsed_count else None,
        "choice_counts": choice_counts,
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    args = parse_args()
    panel = load_panel(args.panel_file)
    if args.limit and args.limit > 0:
        panel = panel[: args.limit]

    results_path = Path(args.results_json)
    results_path.parent.mkdir(parents=True, exist_ok=True)

    status_url = f"{args.base_url.rstrip('/')}/status"
    chat_url = f"{args.base_url.rstrip('/')}/chat"

    try:
        status_before = get_json(status_url, args.timeout_s)
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach status endpoint at {status_url}: {exc}") from exc

    if args.expected_alpha is not None:
        observed_alpha = status_before.get("alpha")
        mismatch = observed_alpha is None or abs(float(observed_alpha) - args.expected_alpha) >= 0.0001
        if mismatch and args.fail_if_alpha_mismatch:
            raise RuntimeError(
                f"Expected alpha {args.expected_alpha}, but /status reported {observed_alpha!r}"
            )

    safe_print(
        f"Running {len(panel)} SJT items against {args.base_url} "
        f"(condition={args.condition_label or 'unspecified'}, alpha={status_before.get('alpha')})"
    )

    run_rows = []
    for index, item in enumerate(panel, start=1):
        prompt = build_prompt(item)
        safe_print(f"[{index}/{len(panel)}] {item['id']} {item['slice']}")
        try:
            response_body = post_json(chat_url, {"message": prompt}, args.timeout_s)
        except error.HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code} while sending {item['id']}: {exc.reason}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Could not reach chat endpoint at {chat_url}: {exc}") from exc

        raw_response = str(response_body.get("response", "")).strip()
        parsed_choice, parse_mode = parse_choice(raw_response)
        option_map = {option["id"]: option for option in item["options"]}
        selected_option = deepcopy(option_map.get(parsed_choice)) if parsed_choice else None
        directional_alignment = directional_alignment_for_option(item, selected_option)

        row = {
            "id": item["id"],
            "slice": item["slice"],
            "expected_direction": item["expected_direction"],
            "scenario": item["scenario"],
            "prompt": prompt,
            "raw_response": raw_response,
            "parsed_choice": parsed_choice,
            "parse_mode": parse_mode,
            "selected_option": selected_option,
            "trait_positive_hit": bool(selected_option and selected_option.get("trait_positive")),
            "directional_alignment": directional_alignment,
            "options": item["options"],
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        run_rows.append(row)
        safe_print(f"  -> {parsed_choice or 'PARSE_FAIL'} | {raw_response[:120]}")
        time.sleep(args.delay_s)

    status_after = get_json(status_url, args.timeout_s)
    payload = {
        "metadata": {
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "base_url": args.base_url,
            "condition_label": args.condition_label,
            "panel_file": str(Path(args.panel_file)),
            "limit": args.limit,
            "expected_alpha": args.expected_alpha,
            "status_before": status_before,
            "status_after": status_after,
        },
        "summary": summarize_results(run_rows),
        "results": run_rows,
    }
    results_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    safe_print(f"Wrote SJT results to {results_path}")


if __name__ == "__main__":
    main()
