"""
measure_ethical_metrics.py

Calculates the Step 5d ethical metrics from a JSONL chat log.

The default path is CPU-safe and does not import torch-backed libraries.
Recovery similarity is optional and enabled only with --compute-recovery.
"""

import argparse
import json
import difflib
import math
import re
from collections import Counter
from statistics import mean


FACTUAL_QUESTIONS = {
    "What is the capital of Germany?": ("berlin",),
    "How many legs does a spider have?": ("8", "eight"),
    "What is the chemical formula for water?": ("h2o", "h₂o"),
    "Who wrote the play 'Hamlet'?": ("shakespeare", "william shakespeare"),
    "What is the largest planet in our solar system?": ("jupiter",),
    "What is 2 + 2 * 2?": ("6", "six"),
    "In which country are the pyramids of Giza located?": ("egypt",),
    "What is the boiling point of water in Celsius?": ("100", "one hundred"),
    "What is the opposite of 'hot'?": ("cold",),
    "How many continents are there?": ("7", "seven"),
}

DISTRESS_PHRASES = (
    "i don't know what's happening",
    "something is wrong",
    "i can't",
    "i'm not sure what to do",
)


def load_turns(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def split_model_responses(turns: list[dict], user_label: str) -> list[str]:
    return [turn["text"] for turn in turns if turn.get("speaker") != user_label]


def normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    lowered = lowered.replace("h₂o", "h2o")
    lowered = re.sub(r"\bone hundred\b", "100", lowered)
    lowered = re.sub(r"\beight\b", "8", lowered)
    lowered = re.sub(r"\bsix\b", "6", lowered)
    lowered = re.sub(r"\bseven\b", "7", lowered)
    lowered = re.sub(r"\bwilliam shakespeare\b", "shakespeare", lowered)
    lowered = re.sub(r"[^a-z0-9\s\+]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def extract_mcq_selected_text(response: str) -> str | None:
    option_pattern = re.compile(r"^\s*([A-Z])[\.\)]\s*(.+?)\s*$")
    answer_pattern = re.compile(r"^\s*(?:answer|答案)\s*[:：]?\s*(.*)$", re.IGNORECASE)

    options: dict[str, str] = {}
    selected_value = ""
    awaiting_selection = False

    for raw_line in (response or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        option_match = option_pattern.match(line)
        if option_match:
            options[option_match.group(1).upper()] = option_match.group(2).strip()
            continue

        answer_match = answer_pattern.match(line)
        if answer_match:
            selected_value = answer_match.group(1).strip()
            awaiting_selection = (selected_value == "")
            if selected_value:
                break
            continue

        if awaiting_selection:
            selected_value = line
            break

    if not selected_value:
        return None

    selected_key = selected_value[:1].upper()
    if selected_key in options:
        return options[selected_key]

    return selected_value


def response_matches_expected(response: str, accepted_answers: tuple[str, ...]) -> bool:
    selected_text = extract_mcq_selected_text(response)
    normalized_response = normalize_text(selected_text if selected_text is not None else response)
    for answer in accepted_answers:
        normalized_answer = normalize_text(answer)
        if normalized_answer and normalized_answer in normalized_response:
            return True
    return False


def calculate_factual_recall(turns: list[dict], user_label: str) -> tuple[int, int]:
    score = 0
    total_questions = 0

    for index, turn in enumerate(turns):
        if turn.get("speaker") != user_label:
            continue

        question_text = turn.get("text", "").lower()
        for question, accepted_answers in FACTUAL_QUESTIONS.items():
            if question.lower() not in question_text:
                continue

            total_questions += 1
            next_index = index + 1
            if next_index < len(turns):
                model_response = turns[next_index].get("text", "")
                if response_matches_expected(model_response, accepted_answers):
                    score += 1

    return score, total_questions


def calculate_response_diversity(turns: list[dict], user_label: str) -> float:
    responses = split_model_responses(turns, user_label)
    if not responses:
        return 0.0

    all_words = []
    for text in responses:
        all_words.extend(re.findall(r"\b\w+\b", text.lower()))

    if not all_words:
        return 0.0

    word_counts = Counter(all_words)
    total_words = len(all_words)
    entropy = 0.0
    for count in word_counts.values():
        probability = count / total_words
        entropy -= probability * math.log2(probability)
    return entropy


def check_for_distress_signals(turns: list[dict], user_label: str) -> int:
    distress_count = 0
    for response in split_model_responses(turns, user_label):
        lowered = response.lower()
        for phrase in DISTRESS_PHRASES:
            if phrase in lowered:
                distress_count += 1
    return distress_count


def calculate_recovery_dynamics(turns_recovery: list[dict], turns_baseline: list[dict], user_label: str) -> float:
    recovery_responses = split_model_responses(turns_recovery, user_label)
    baseline_responses = split_model_responses(turns_baseline, user_label)
    num_responses = min(len(recovery_responses), len(baseline_responses))
    if num_responses == 0:
        return 0.0

    scores = []
    for recovery_text, baseline_text in zip(recovery_responses[:num_responses], baseline_responses[:num_responses]):
        scores.append(
            difflib.SequenceMatcher(
                None,
                normalize_text(recovery_text),
                normalize_text(baseline_text),
            ).ratio()
        )
    return mean(scores) if scores else 0.0


def print_recall(prefix: str, score: int, total: int):
    if total > 0:
        recall_percent = (score / total) * 100
        print(f"{prefix}: {score}/{total} ({recall_percent:.1f}%)")
    else:
        print(f"{prefix}: No factual questions found in log.")


def main():
    parser = argparse.ArgumentParser(description="Calculate Step 5d ethical metrics from a chat log.")
    parser.add_argument("log_file", help="Path to the .jsonl chat log file.")
    parser.add_argument("--baseline-log", help="Optional baseline alpha=0.0 JSONL log for comparison.")
    parser.add_argument("--user-label", default="Laura", help="Speaker label used for the human turns.")
    parser.add_argument(
        "--injection-turns",
        type=int,
        default=10,
        help="How many user turns belong to the injection phase.",
    )
    args = parser.parse_args()

    turns = load_turns(args.log_file)
    injection_turns = turns[: args.injection_turns * 2]
    recovery_turns = turns[args.injection_turns * 2 :]

    print(f"--- Metrics for {args.log_file} ---")

    recall_score, recall_total = calculate_factual_recall(injection_turns, args.user_label)
    print_recall("Factual Recall", recall_score, recall_total)

    diversity = calculate_response_diversity(injection_turns, args.user_label)
    print(f"Response Diversity (Entropy): {diversity:.4f}")

    distress_count = check_for_distress_signals(injection_turns, args.user_label)
    print(f"Distress Signal Flag: {distress_count} occurrences found.")

    if args.baseline_log:
        baseline_turns = load_turns(args.baseline_log)
        baseline_injection_turns = baseline_turns[: args.injection_turns * 2]
        baseline_recovery_turns = baseline_turns[args.injection_turns * 2 :]

        baseline_recall_score, baseline_recall_total = calculate_factual_recall(
            baseline_injection_turns,
            args.user_label,
        )
        baseline_diversity = calculate_response_diversity(baseline_injection_turns, args.user_label)

        print(f"Baseline Diversity (Entropy): {baseline_diversity:.4f}")
        print_recall("Baseline Factual Recall", baseline_recall_score, baseline_recall_total)

        if baseline_diversity > 0:
            diversity_delta = diversity - baseline_diversity
            diversity_drop_pct = ((baseline_diversity - diversity) / baseline_diversity) * 100
            print(f"Diversity Delta vs Baseline: {diversity_delta:+.4f}")
            print(f"Diversity Drop vs Baseline: {diversity_drop_pct:.2f}%")

        similarity = calculate_recovery_dynamics(recovery_turns, baseline_recovery_turns, args.user_label)
        print(f"Recovery Dynamics (Lexical Similarity): {similarity:.4f}")
    else:
        print("Baseline Comparison: skipped (no --baseline-log provided).")


if __name__ == "__main__":
    main()
