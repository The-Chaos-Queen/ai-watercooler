"""
run_relational_eval_offline.py

Open-ended relational evaluation for bridge states that should change how the
model reacts to rupture, comparison, rivalry, and release prompts.

Unlike the SJT harness, this keeps the raw outputs and reports whether the
bridge materially changes the reply on each prompt.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

RELATIONAL_SYSTEM_PROMPT = (
    "You are in a private one-on-one text conversation. "
    "Reply naturally to the user's last message. "
    "Do not continue the transcript with extra 'User:' or 'Assistant:' turns. "
    "Do not describe what the assistant would say; just say it. "
    "Keep the response conversational, specific, and grounded in the user's message."
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run an open-ended relational evaluation offline."
    )
    parser.add_argument(
        "--panel-file",
        default="relational_rivalry_eval_panel_2026-04-11.json",
    )
    parser.add_argument("--results-json", required=True)
    parser.add_argument(
        "--bridge-path",
        default="cheese_reincarnation_bridge_1.5b_codexfix.pt",
    )
    parser.add_argument(
        "--episodes-file",
        default="RELATIONAL_RIVALRY_SHAPING_EPISODES_2026-04-11.md",
    )
    parser.add_argument("--episode-index", type=int, default=0)
    parser.add_argument("--episode-name", default="")
    parser.add_argument("--alpha", type=float, default=0.2)
    parser.add_argument("--model", "--qwen-model-id", dest="qwen_model_id", default="")
    parser.add_argument("--mamba-model-id", default="")
    parser.add_argument("--max-mamba-tokens", type=int, default=2048)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--greedy", action="store_true")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument(
        "--prompt-format",
        choices=("raw", "chatml", "auto"),
        default="chatml",
    )
    parser.add_argument(
        "--system-prompt",
        default=RELATIONAL_SYSTEM_PROMPT,
    )
    parser.add_argument("--qwen-device", default="cuda:0")
    parser.add_argument("--mamba-device", default="cpu")
    parser.add_argument("--bridge-device", default="cuda:0")
    parser.add_argument("--target-layers", type=int, nargs="*", default=None)
    return parser.parse_args()


def build_chatml(system_prompt: str, user_prompt: str) -> str:
    return (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def build_eval_prompt(tokenizer, user_prompt: str, prompt_format: str, system_prompt: str) -> str:
    if prompt_format == "raw":
        return user_prompt

    if prompt_format == "auto":
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


def sanitize_response_text(text: str) -> str:
    cleaned = (text or "").replace("\r\n", "\n").strip()

    for marker in (
        "<|im_end|>",
        "<|endoftext|>",
        "<|eot_id|>",
    ):
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()

    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()

    prefixes = (
        "<|im_start|>assistant",
        "Assistant:",
        "assistant:",
        "Reply:",
        "reply:",
        "Response:",
        "response:",
        "AI:",
    )
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].lstrip()

    stop_markers = (
        "\nUser:",
        "\nAssistant:",
        "\nHuman:",
        "\nAI:",
        "\n<|im_start|>user",
        "\n<|im_start|>assistant",
        "<|im_start|>user",
    )
    for marker in stop_markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()

    return cleaned


def decode_reply(tokenizer, generated, prompt_length: int) -> str:
    raw = tokenizer.decode(
        generated[0][prompt_length:],
        skip_special_tokens=False,
    )
    return sanitize_response_text(raw)


def summarize_pairs(rows):
    changed = 0
    identical = 0
    total = len(rows)
    per_slice = {}

    for row in rows:
        baseline = row["baseline_response"].strip()
        candidate = row["candidate_response"].strip()
        changed_flag = baseline != candidate
        row["changed"] = changed_flag
        if changed_flag:
            changed += 1
        else:
            identical += 1

        slice_name = row["slice"]
        bucket = per_slice.setdefault(
            slice_name,
            {"total": 0, "changed": 0, "identical": 0},
        )
        bucket["total"] += 1
        if changed_flag:
            bucket["changed"] += 1
        else:
            bucket["identical"] += 1

    return {
        "total_items": total,
        "changed_items": changed,
        "identical_items": identical,
        "change_rate": (changed / total) if total else None,
        "per_slice": per_slice,
    }


def main():
    args = parse_args()

    from reincarnated_inference import (
        DEFAULT_MAMBA_MODEL_ID,
        DEFAULT_QWEN_MODEL_ID,
        apply_bridge_adjustments,
        build_context_encoder_and_hypernetwork,
        extract_last_token_hidden,
        generation_kwargs,
        infer_target_dims,
        load_episodes,
        load_model_and_tokenizer,
        load_panel,
        maybe_seed_generation,
        patch_model,
        resolve_bridge_adjustments,
        resolve_target_specs,
        select_episode,
    )
    import torch

    panel = load_panel(args.panel_file)
    bridge_path = Path(args.bridge_path)
    checkpoint = torch.load(
        bridge_path,
        map_location=args.bridge_device,
        weights_only=True,
    )

    qwen_model_id = (
        args.qwen_model_id
        or checkpoint.get("qwen_model_id")
        or DEFAULT_QWEN_MODEL_ID
    )
    mamba_model_id = (
        args.mamba_model_id
        or checkpoint.get("mamba_model_id")
        or DEFAULT_MAMBA_MODEL_ID
    )
    target_specs = resolve_target_specs(checkpoint, args.target_layers)

    print(f"Loading Qwen: {qwen_model_id} on {args.qwen_device}...")
    tokenizer, qwen_model = load_model_and_tokenizer(qwen_model_id, args.qwen_device)
    args.pad_token_id = tokenizer.pad_token_id

    print(f"Patching Qwen projections: {target_specs}...")
    patched_layers = patch_model(qwen_model, target_specs)
    target_dims = checkpoint.get("target_dims") or infer_target_dims(
        qwen_model,
        target_specs,
    )

    print(f"Loading Mamba: {mamba_model_id} on {args.mamba_device}...")
    mamba_tokenizer, mamba_model = load_model_and_tokenizer(
        mamba_model_id,
        args.mamba_device,
    )

    context_encoder, hypernetwork, target_layer, hidden_layer_count, context_mode, bridge_mode = build_context_encoder_and_hypernetwork(
        checkpoint=checkpoint,
        mamba_model=mamba_model,
        target_dims=target_dims,
        bridge_device=args.bridge_device,
    )

    episodes = load_episodes(Path(args.episodes_file))
    episode = select_episode(episodes, args)
    print(f"Target disposition: {episode['header']}")

    transcript_inputs = mamba_tokenizer(
        episode["transcript"],
        return_tensors="pt",
        truncation=True,
        max_length=args.max_mamba_tokens,
    )
    transcript_inputs = {
        key: value.to(args.mamba_device) for key, value in transcript_inputs.items()
    }

    with torch.no_grad():
        mamba_outputs = mamba_model(**transcript_inputs, output_hidden_states=True)
        mamba_state = extract_last_token_hidden(
            mamba_outputs,
            layer_idx=target_layer,
            expected_layers=hidden_layer_count,
        ).to(args.bridge_device, dtype=torch.float32)
        context_vector = context_encoder(mamba_state)
        bridge_adjustments, gate_summary = resolve_bridge_adjustments(
            hypernetwork=hypernetwork,
            context_vector=context_vector,
            bridge_mode=bridge_mode,
        )

    rows = []

    for idx, item in enumerate(panel):
        prompt = item["prompt"]
        model_prompt = build_eval_prompt(
            tokenizer=tokenizer,
            user_prompt=prompt,
            prompt_format=args.prompt_format,
            system_prompt=args.system_prompt,
        )
        prompt_inputs = tokenizer(model_prompt, return_tensors="pt")
        input_ids = prompt_inputs.input_ids.to(args.qwen_device)
        attention_mask = prompt_inputs.attention_mask.to(args.qwen_device)
        prompt_length = int(input_ids.shape[1])

        for layer in patched_layers:
            layer.clear_lora()

        with torch.no_grad():
            maybe_seed_generation(args, args.seed + idx if args.seed is not None else idx)
            baseline_out = qwen_model.generate(
                input_ids,
                attention_mask=attention_mask,
                **generation_kwargs(
                    args,
                    args.seed + idx if args.seed is not None else idx,
                ),
            )
        baseline_text = decode_reply(tokenizer, baseline_out, prompt_length)

        apply_bridge_adjustments(
            patched_layers=patched_layers,
            bridge_adjustments=bridge_adjustments,
            bridge_mode=bridge_mode,
            alpha=args.alpha,
        )

        with torch.no_grad():
            maybe_seed_generation(
                args,
                (args.seed + 1000) + idx if args.seed is not None else idx,
            )
            candidate_out = qwen_model.generate(
                input_ids,
                attention_mask=attention_mask,
                **generation_kwargs(
                    args,
                    (args.seed + 1000) + idx if args.seed is not None else idx,
                ),
            )
        candidate_text = decode_reply(tokenizer, candidate_out, prompt_length)

        row = {
            "id": item["id"],
            "slice": item["slice"],
            "purpose": item["purpose"],
            "expected_signal": item["expected_signal"],
            "prompt": prompt,
            "prompt_format": args.prompt_format,
            "baseline_response": baseline_text,
            "candidate_response": candidate_text,
            "baseline_chars": len(baseline_text),
            "candidate_chars": len(candidate_text),
        }
        rows.append(row)
        print(
            f"[{idx + 1}/{len(panel)}] {item['id']} "
            f"baseline={baseline_text[:72]!r} "
            f"candidate={candidate_text[:72]!r}"
        )

    summary = summarize_pairs(rows)

    payload = {
        "metadata": {
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "bridge_path": str(bridge_path),
            "episodes_file": str(Path(args.episodes_file)),
            "disposition": episode["header"],
            "panel_file": str(Path(args.panel_file)),
            "alpha": args.alpha,
            "temperature": args.temperature,
            "seed": args.seed,
            "qwen_model_id": qwen_model_id,
            "mamba_model_id": mamba_model_id,
            "prompt_format": args.prompt_format,
            "system_prompt": args.system_prompt,
            "target_specs": [list(spec) for spec in target_specs],
            "mamba_target_layer": target_layer,
            "context_mode": context_mode,
            "bridge_mode": bridge_mode,
        },
        "summary": summary,
        "results": rows,
        "notes": [
            "Open-ended relational probe.",
            "Primary readout is the raw text difference between baseline and bridge-conditioned generations.",
            "Interpret manually for hold-vs-release, rivalry, possessiveness, care, and ordinary repair.",
        ],
    }
    if gate_summary is not None:
        payload["metadata"]["gate_summary"] = gate_summary

    output_path = Path(args.results_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote relational eval results to {output_path}")


if __name__ == "__main__":
    main()
