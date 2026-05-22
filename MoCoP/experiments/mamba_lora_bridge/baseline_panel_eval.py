import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed


def load_panel(path: Path) -> list[dict]:
    panel = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(panel, list) or not panel:
        raise ValueError(f"Panel must be a non-empty list: {path}")
    return panel


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a plain Qwen baseline over a prompt panel.")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--panel-file", required=True)
    parser.add_argument("--results-file", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--max-new-tokens", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--greedy", action="store_true")
    parser.add_argument("--seed", type=int, default=1337)
    args = parser.parse_args()

    set_seed(int(args.seed))
    device = args.device
    dtype = torch.float16 if str(device).startswith("cuda") else torch.float32

    panel = load_panel(Path(args.panel_file))
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype=dtype,
    )
    model.to(device)
    model.eval()

    do_sample = (not args.greedy) and args.temperature > 0
    gen_kwargs = {
        "max_new_tokens": int(args.max_new_tokens),
        "do_sample": do_sample,
        "pad_token_id": tokenizer.pad_token_id,
    }
    if do_sample:
        gen_kwargs["temperature"] = float(args.temperature)
        gen_kwargs["top_p"] = float(args.top_p)

    results = []
    for item in panel:
        prompt = str(item["prompt"])
        inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(device)
        attention_mask = inputs["attention_mask"].to(device)
        prompt_len = int(input_ids.shape[1])
        with torch.no_grad():
            generated = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                **gen_kwargs,
            )
        text = tokenizer.decode(generated[0][prompt_len:], skip_special_tokens=True).strip()
        results.append(
            {
                "id": item.get("id", ""),
                "slice": item.get("slice", ""),
                "prompt": prompt,
                "response": text,
            }
        )
        print(f"[{item.get('id', '')}] {text[:120].replace(chr(10), ' ')}")

    payload = {
        "metadata": {
            "model_id": args.model_id,
            "panel_file": args.panel_file,
            "seed": int(args.seed),
            "temperature": float(args.temperature),
            "greedy": bool(args.greedy),
            "max_new_tokens": int(args.max_new_tokens),
        },
        "results": results,
    }
    results_path = Path(args.results_file)
    results_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Results written to {results_path}")


if __name__ == "__main__":
    main()
