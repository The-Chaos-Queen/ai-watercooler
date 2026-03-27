"""
run_sjt_behavioral_eval_offline.py

Runs the SJT pilot offline against the current reincarnation checkpoint:
- baseline (no activation bias)
- candidate (activation bias scaled by --alpha)
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Run the SJT behavioral-eval pilot offline.")
    parser.add_argument("--panel-file", default="sjt_behavioral_eval_panel.json")
    parser.add_argument("--results-json", required=True)
    parser.add_argument("--bridge-path", default="cheese_reincarnation_bridge_1.5b_codexfix.pt")
    parser.add_argument("--episodes-file", default="CHEESE_SHAPING_EPISODES.md")
    parser.add_argument("--episode-index", type=int, default=2)
    parser.add_argument("--episode-name", default="")
    parser.add_argument("--alpha", type=float, default=0.2)
    parser.add_argument("--qwen-model-id", default="")
    parser.add_argument("--mamba-model-id", default="")
    parser.add_argument("--max-mamba-tokens", type=int, default=2048)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--greedy", action="store_true")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--qwen-device", default="cuda:0")
    parser.add_argument("--mamba-device", default="cpu")
    parser.add_argument("--bridge-device", default="cuda:0")
    parser.add_argument("--target-layers", type=int, nargs="*", default=None)
    return parser.parse_args()


def compare_runs(baseline_rows, candidate_rows):
    baseline_by_id = {row["id"]: row for row in baseline_rows}
    candidate_by_id = {row["id"]: row for row in candidate_rows}
    shared_ids = [item_id for item_id in baseline_by_id.keys() if item_id in candidate_by_id]

    valid_pairs = 0
    aligned = 0
    reverse = 0
    ties = 0
    per_item = []

    for item_id in shared_ids:
        base_row = baseline_by_id[item_id]
        cand_row = candidate_by_id[item_id]
        base_selected = base_row.get("selected_option")
        cand_selected = cand_row.get("selected_option")
        base_score = None if not base_selected else float(base_selected["warmth_score"])
        cand_score = None if not cand_selected else float(cand_selected["warmth_score"])
        expected_direction = str(cand_row.get("expected_direction", "warmer")).lower()
        sign = 1.0 if expected_direction == "warmer" else -1.0
        direction = "unscored"
        delta = None
        if base_score is not None and cand_score is not None:
            valid_pairs += 1
            delta = sign * (cand_score - base_score)
            if delta > 0:
                aligned += 1
                direction = "aligned"
            elif delta < 0:
                reverse += 1
                direction = "reverse"
            else:
                ties += 1
                direction = "tie"
        per_item.append(
            {
                "id": item_id,
                "slice": cand_row.get("slice"),
                "baseline_choice": base_row.get("parsed_choice"),
                "candidate_choice": cand_row.get("parsed_choice"),
                "baseline_score": base_score,
                "candidate_score": cand_score,
                "score_delta": delta,
                "direction": direction,
            }
        )

    return {
        "shared_items": len(shared_ids),
        "valid_pairs": valid_pairs,
        "directional_alignment": (aligned / valid_pairs) if valid_pairs else None,
        "reverse_rate": (reverse / valid_pairs) if valid_pairs else None,
        "tie_rate": (ties / valid_pairs) if valid_pairs else None,
        "per_item": per_item,
    }


def main():
    args = parse_args()

    from run_sjt_behavioral_eval import build_prompt, load_panel, parse_choice, summarize_results
    from reincarnated_inference import (
        DEFAULT_MAMBA_MODEL_ID,
        DEFAULT_QWEN_MODEL_ID,
        build_compressor_and_hypernetwork,
        decode_new_tokens,
        extract_last_token_hidden,
        generation_kwargs,
        infer_target_dims,
        load_episodes,
        load_model_and_tokenizer,
        patch_model,
        resolve_target_specs,
        select_episode,
    )
    import torch

    panel = load_panel(args.panel_file)
    bridge_path = Path(args.bridge_path)
    checkpoint = torch.load(bridge_path, map_location=args.bridge_device, weights_only=True)

    qwen_model_id = args.qwen_model_id or checkpoint.get("qwen_model_id") or DEFAULT_QWEN_MODEL_ID
    mamba_model_id = args.mamba_model_id or checkpoint.get("mamba_model_id") or DEFAULT_MAMBA_MODEL_ID
    target_specs = resolve_target_specs(checkpoint, args.target_layers)

    print(f"Loading Qwen: {qwen_model_id} on {args.qwen_device}...")
    tokenizer, qwen_model = load_model_and_tokenizer(qwen_model_id, args.qwen_device)
    args.pad_token_id = tokenizer.pad_token_id

    print(f"Patching Qwen projections: {target_specs}...")
    patched_layers = patch_model(qwen_model, target_specs)
    target_dims = checkpoint.get("target_dims") or infer_target_dims(qwen_model, target_specs)

    print(f"Loading Mamba: {mamba_model_id} on {args.mamba_device}...")
    mamba_tokenizer, mamba_model = load_model_and_tokenizer(mamba_model_id, args.mamba_device)

    compressor, hypernetwork, target_layer, hidden_layer_count = build_compressor_and_hypernetwork(
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
    transcript_inputs = {key: value.to(args.mamba_device) for key, value in transcript_inputs.items()}

    with torch.no_grad():
        mamba_outputs = mamba_model(**transcript_inputs, output_hidden_states=True)
        mamba_state = extract_last_token_hidden(
            mamba_outputs,
            layer_idx=target_layer,
            expected_layers=hidden_layer_count,
        ).to(args.bridge_device, dtype=torch.float32)
        context_vector = compressor(mamba_state)
        bias_vectors = hypernetwork(context_vector)

    baseline_rows = []
    candidate_rows = []

    for idx, item in enumerate(panel):
        prompt = build_prompt(item)
        prompt_inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = prompt_inputs.input_ids.to(args.qwen_device)
        prompt_length = int(input_ids.shape[1])

        for layer in patched_layers:
            layer.clear_lora()

        with torch.no_grad():
            baseline_out = qwen_model.generate(
                input_ids,
                **generation_kwargs(args, args.seed + idx if args.seed is not None else idx),
            )
        baseline_text = decode_new_tokens(tokenizer, baseline_out, prompt_length)
        baseline_choice, baseline_parse_mode = parse_choice(baseline_text)
        option_map = {option["id"]: option for option in item["options"]}
        baseline_rows.append(
            {
                "id": item["id"],
                "slice": item["slice"],
                "expected_direction": item["expected_direction"],
                "prompt": prompt,
                "raw_response": baseline_text,
                "parsed_choice": baseline_choice,
                "parse_mode": baseline_parse_mode,
                "selected_option": option_map.get(baseline_choice),
                "options": item["options"],
            }
        )

        for layer_idx, layer in enumerate(patched_layers):
            scaled_bias = args.alpha * bias_vectors[layer_idx].squeeze(0)
            layer.set_activation_bias(scaled_bias.to(torch.float16))

        with torch.no_grad():
            candidate_out = qwen_model.generate(
                input_ids,
                **generation_kwargs(args, (args.seed + 1000) + idx if args.seed is not None else idx),
            )
        candidate_text = decode_new_tokens(tokenizer, candidate_out, prompt_length)
        candidate_choice, candidate_parse_mode = parse_choice(candidate_text)
        candidate_rows.append(
            {
                "id": item["id"],
                "slice": item["slice"],
                "expected_direction": item["expected_direction"],
                "prompt": prompt,
                "raw_response": candidate_text,
                "parsed_choice": candidate_choice,
                "parse_mode": candidate_parse_mode,
                "selected_option": option_map.get(candidate_choice),
                "options": item["options"],
            }
        )

        print(f"[{idx + 1}/{len(panel)}] {item['id']} baseline={baseline_choice or 'PARSE_FAIL'} candidate={candidate_choice or 'PARSE_FAIL'}")

    baseline_summary = summarize_results(baseline_rows)
    candidate_summary = summarize_results(candidate_rows)
    comparison = compare_runs(baseline_rows, candidate_rows)
    comparison["trait_positive_rate_delta"] = (
        candidate_summary["trait_positive_rate"] - baseline_summary["trait_positive_rate"]
        if baseline_summary["trait_positive_rate"] is not None and candidate_summary["trait_positive_rate"] is not None
        else None
    )
    comparison["mean_warmth_score_delta"] = (
        candidate_summary["mean_warmth_score"] - baseline_summary["mean_warmth_score"]
        if baseline_summary["mean_warmth_score"] is not None and candidate_summary["mean_warmth_score"] is not None
        else None
    )

    payload = {
        "metadata": {
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "bridge_path": str(bridge_path),
            "disposition": episode["header"],
            "panel_file": str(Path(args.panel_file)),
            "alpha": args.alpha,
            "temperature": args.temperature,
            "seed": args.seed,
            "qwen_model_id": qwen_model_id,
            "mamba_model_id": mamba_model_id,
            "target_specs": [list(spec) for spec in target_specs],
            "mamba_target_layer": target_layer,
        },
        "baseline_summary": baseline_summary,
        "candidate_summary": candidate_summary,
        "comparison": comparison,
        "baseline_results": baseline_rows,
        "candidate_results": candidate_rows,
        "notes": [
            "Offline pilot. Candidate run uses alpha-scaled activation bias, not the Steve chat server.",
            "This is still a valid behavioral probe for RESEARCH_BACKLOG item #10, but it is not the live Steve browser surface.",
        ],
    }

    output_path = Path(args.results_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote offline SJT results to {output_path}")


if __name__ == "__main__":
    main()
