"""
baseline_solvability_probe.py - Step 0 probe for MoCoP Phase 2.

This script asks a plain causal LM to answer the MoCoP fact-recall task without
any bridge injection. It is meant to answer the baseline question first:

    Can the target model solve the task at all when the relevant facts are
    explicitly visible in the prompt text?

It supports three prompt modes:

- question_only: just the question
- compact_fact: the target fact is explicitly shown in compact text form
- full_history: the full synthetic 8192-token history is placed in the user prompt

Outputs:
- aggregate exact-match / token-overlap-F1 metrics
- a JSON file with raw predictions for inspection
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TQDM_DISABLE", "1")

import torch

try:
    from transformers.utils import logging as hf_logging

    hf_logging.set_verbosity_error()
    hf_logging.disable_progress_bar()
except Exception:
    pass

from transformers import AutoModelForCausalLM, AutoTokenizer

from bridge_dataset import (
    BridgeDataset,
    BridgeDatasetConfig,
    FACT_SYSTEM_PROMPT,
    QWEN_MODEL_ID,
)

LOGGER = logging.getLogger("BaselineProbe")


@dataclass
class ProbeRow:
    index: int
    prompt_mode: str
    fact_kind: str
    question: str
    answer: str
    prediction: str
    normalized_prediction: str
    exact_match: bool
    token_f1: float


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def normalize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize_soft(text: str) -> List[str]:
    clean = normalize_text(text).lower()
    return [tok for tok in re.split(r"[^\w']+", clean) if tok]


def token_f1(prediction: str, target: str) -> float:
    pred_tokens = tokenize_soft(prediction)
    target_tokens = tokenize_soft(target)
    if not pred_tokens and not target_tokens:
        return 1.0
    if not pred_tokens or not target_tokens:
        return 0.0

    pred_counts: Dict[str, int] = {}
    target_counts: Dict[str, int] = {}
    for token in pred_tokens:
        pred_counts[token] = pred_counts.get(token, 0) + 1
    for token in target_tokens:
        target_counts[token] = target_counts.get(token, 0) + 1

    overlap = 0
    for token, count in pred_counts.items():
        overlap += min(count, target_counts.get(token, 0))

    if overlap == 0:
        return 0.0

    precision = overlap / len(pred_tokens)
    recall = overlap / len(target_tokens)
    return 2 * precision * recall / (precision + recall)


def render_user_prompt(sample: Dict[str, Any], prompt_mode: str) -> str:
    question = sample["question_text"]
    answer = sample["answer_text"]
    if prompt_mode == "question_only":
        return question
    if prompt_mode == "compact_fact":
        return (
            "Facts visible in the current context:\n"
            f"[memory]\n{question}\n{answer}\n\n"
            f"Question: {question}"
        )
    if prompt_mode == "full_history":
        return (
            "Visible context follows. The answer is present somewhere in it.\n\n"
            f"{sample['mamba_context_text']}\n\n"
            f"Question: {question}"
        )
    raise ValueError(f"Unsupported prompt_mode: {prompt_mode}")


def build_chatml(system_prompt: str, user_prompt: str) -> str:
    return (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def build_prompt(tokenizer, system_prompt: str, user_prompt: str, chat_template: str) -> str:
    if chat_template == "chatml":
        return build_chatml(system_prompt, user_prompt)
    if chat_template == "auto":
        template = getattr(tokenizer, "chat_template", None)
        if template:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        return build_chatml(system_prompt, user_prompt)
    raise ValueError(f"Unsupported chat_template mode: {chat_template}")


def decode_generation(tokenizer, generated_ids: torch.Tensor, prompt_len: int) -> str:
    answer_ids = generated_ids[0, prompt_len:]
    text = tokenizer.decode(answer_ids, skip_special_tokens=False)
    for marker in ("<|im_end|>", tokenizer.eos_token or ""):
        if marker and marker in text:
            text = text.split(marker, 1)[0]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return normalize_text(text)


def load_model(model_id: str, device: str, use_4bit: bool):
    resolved_device = torch.device("cuda" if device == "auto" and torch.cuda.is_available() else device)
    model_kwargs: Dict[str, Any] = {"low_cpu_mem_usage": True}

    if resolved_device.type != "cpu":
        model_kwargs["device_map"] = "auto"
        if use_4bit:
            from transformers import BitsAndBytesConfig

            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        else:
            model_kwargs["torch_dtype"] = torch.float16
    else:
        model_kwargs["torch_dtype"] = torch.float32

    LOGGER.info("Loading tokenizer: %s", model_id)
    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    LOGGER.info("Loading model: %s", model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
    model.eval()
    return tokenizer, model


def run_probe(args: argparse.Namespace) -> Dict[str, Any]:
    tokenizer, model = load_model(
        model_id=args.model_id,
        device=args.device,
        use_4bit=not args.no_4bit,
    )

    dataset = BridgeDataset(
        BridgeDatasetConfig(
            num_samples=args.samples,
            mode="fact",
            mamba_context_tokens=args.mamba_context_tokens,
            max_qwen_tokens=args.max_qwen_tokens,
            min_post_target_tokens=args.min_post_target_tokens,
            max_post_target_tokens=args.max_post_target_tokens,
            seed=args.seed,
            include_text=True,
        ),
        qwen_tokenizer=tokenizer,
    )

    rows: List[ProbeRow] = []

    for index in range(len(dataset)):
        sample = dataset[index]
        question = sample["question_text"]
        answer = normalize_text(sample["answer_text"])
        user_prompt = render_user_prompt(sample, prompt_mode=args.prompt_mode)
        prompt_text = build_prompt(
            tokenizer,
            FACT_SYSTEM_PROMPT,
            user_prompt,
            chat_template=args.chat_template,
        )

        inputs = tokenizer(prompt_text, return_tensors="pt")
        inputs = {key: value.to(model.device) for key, value in inputs.items()}
        prompt_len = int(inputs["input_ids"].shape[1])

        with torch.no_grad():
            generated = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
                top_k=None,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        prediction = decode_generation(tokenizer, generated, prompt_len=prompt_len)
        exact_match = prediction == answer
        rows.append(
            ProbeRow(
                index=index,
                prompt_mode=args.prompt_mode,
                fact_kind=sample["metadata"]["fact_kind"],
                question=question,
                answer=answer,
                prediction=prediction,
                normalized_prediction=prediction.lower(),
                exact_match=exact_match,
                token_f1=token_f1(prediction, answer),
            )
        )

        LOGGER.info(
            "sample=%d/%d mode=%s exact=%s f1=%.3f q=%r gold=%r pred=%r",
            index + 1,
            len(dataset),
            args.prompt_mode,
            exact_match,
            rows[-1].token_f1,
            question,
            answer,
            prediction,
        )

    exact_scores = [1.0 if row.exact_match else 0.0 for row in rows]
    f1_scores = [row.token_f1 for row in rows]
    result = {
        "model_id": args.model_id,
        "prompt_mode": args.prompt_mode,
        "chat_template": args.chat_template,
        "samples": args.samples,
        "exact_match": {
            "accuracy": sum(exact_scores) / max(1, len(exact_scores)),
            "correct": int(sum(exact_scores)),
            "total": len(exact_scores),
        },
        "token_f1": {
            "mean": statistics.fmean(f1_scores) if f1_scores else 0.0,
            "median": statistics.median(f1_scores) if f1_scores else 0.0,
        },
        "rows": [asdict(row) for row in rows],
    }
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe a plain LM on MoCoP fact recall.")
    parser.add_argument("--model-id", type=str, default=QWEN_MODEL_ID)
    parser.add_argument(
        "--prompt-mode",
        type=str,
        choices=("question_only", "compact_fact", "full_history"),
        default="compact_fact",
    )
    parser.add_argument(
        "--chat-template",
        type=str,
        choices=("chatml", "auto"),
        default="chatml",
        help="Use exact training-style ChatML or the tokenizer's native chat template if available.",
    )
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--no-4bit", action="store_true")
    parser.add_argument("--mamba-context-tokens", type=int, default=8192)
    parser.add_argument("--max-qwen-tokens", type=int, default=256)
    parser.add_argument("--min-post-target-tokens", type=int, default=1024)
    parser.add_argument("--max-post-target-tokens", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=16)
    parser.add_argument("--output", type=str, default="baseline_probe_results.json")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    configure_logging(verbose=args.verbose)
    set_seed(args.seed)
    result = run_probe(args)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    LOGGER.info(
        "saved=%s exact=%.3f (%d/%d) mean_f1=%.3f",
        output_path,
        result["exact_match"]["accuracy"],
        result["exact_match"]["correct"],
        result["exact_match"]["total"],
        result["token_f1"]["mean"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
