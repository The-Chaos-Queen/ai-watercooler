#!/usr/bin/env python3
"""
probe_mamba3.py — Bridge contract probe for any HuggingFace Mamba model.

Probes a MambaForCausalLM-compatible model and reports whether the
hidden-state extraction path (Layer 3 last-token) matches the bridge
contract. Use to validate Mamba-2 baseline or future Mamba-3 weights.

Usage (Opa-PC, Windows Python or WSL):
  python -X utf8 probe_mamba3.py --model-id state-spaces/mamba-2.8b-hf
  python -X utf8 probe_mamba3.py --model-id <future-mamba3-id> --output report.json

Output: JSON report + human-readable summary.
See MoCoP/experiments/mamba3_migration_memo.md for the full scoping result.
"""

import argparse
import json
import sys
import time
import traceback

def probe(args):
    report = {
        "model_id": args.model_id,
        "baseline_model_id": "state-spaces/mamba-2.8b-hf",
        "device": args.device,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "steps": {},
    }

    # Step 0: Imports
    print("=" * 60)
    print(f"Mamba-3 Migration Probe: {args.model_id}")
    print(f"Device: {args.device}")
    print("=" * 60)

    try:
        import torch
        report["torch_version"] = torch.__version__
        report["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            report["cuda_device"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            mem = getattr(props, "total_memory", None) or getattr(props, "total_mem", 0)
            report["cuda_memory_gb"] = round(mem / 1e9, 1)
        print(f"[ok] torch {torch.__version__}, CUDA={torch.cuda.is_available()}")
    except Exception as e:
        report["steps"]["imports"] = {"ok": False, "error": str(e)}
        dump_report(report, args)
        return 1

    # Step 1: Load model
    print(f"\n--- Step 1: Load model ---")
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, MambaForCausalLM

        t0 = time.time()
        tokenizer = AutoTokenizer.from_pretrained(args.model_id)
        print(f"[ok] tokenizer loaded ({time.time()-t0:.1f}s)")

        t0 = time.time()
        # Try MambaForCausalLM first (specific), fall back to Auto
        try:
            model = MambaForCausalLM.from_pretrained(
                args.model_id, torch_dtype=torch.float32
            )
            model_class = "MambaForCausalLM"
        except Exception:
            model = AutoModelForCausalLM.from_pretrained(
                args.model_id, torch_dtype=torch.float32
            )
            model_class = type(model).__name__

        model.to(args.device)
        model.eval()
        load_time = time.time() - t0
        print(f"[ok] model loaded as {model_class} ({load_time:.1f}s)")

        report["steps"]["load"] = {
            "ok": True,
            "model_class": model_class,
            "load_time_s": round(load_time, 1),
        }
    except Exception as e:
        print(f"[FAIL] model load: {e}")
        report["steps"]["load"] = {"ok": False, "error": str(e)}
        traceback.print_exc()
        dump_report(report, args)
        return 1

    # Step 2: Model architecture inspection
    print(f"\n--- Step 2: Architecture inspection ---")
    try:
        config = model.config
        arch_info = {}
        for attr in ["d_model", "n_layer", "d_state", "d_inner", "d_conv",
                      "num_heads", "head_dim", "expand", "vocab_size",
                      "ssm_cfg", "rms_norm", "residual_in_fp32",
                      "hidden_size", "num_hidden_layers", "intermediate_size",
                      "state_size", "conv_kernel"]:
            val = getattr(config, attr, None)
            if val is not None:
                arch_info[attr] = val if not hasattr(val, 'item') else val.item()

        report["architecture"] = arch_info
        d_model = arch_info.get("d_model") or arch_info.get("hidden_size", "?")
        n_layers = arch_info.get("n_layer") or arch_info.get("num_hidden_layers", "?")
        print(f"[ok] d_model={d_model}, n_layers={n_layers}")
        for k, v in arch_info.items():
            print(f"     {k}: {v}")

        report["steps"]["architecture"] = {"ok": True}
    except Exception as e:
        print(f"[WARN] architecture inspection: {e}")
        report["steps"]["architecture"] = {"ok": False, "error": str(e)}

    # Step 3: Forward pass with hidden states
    print(f"\n--- Step 3: Forward pass ---")
    try:
        test_text = "The quick brown fox jumps over the lazy dog."
        inputs = tokenizer(test_text, return_tensors="pt").to(args.device)
        seq_len = inputs["input_ids"].shape[1]
        print(f"[ok] tokenized: {seq_len} tokens")

        with torch.no_grad():
            outputs = model(**inputs, output_hidden_states=True)

        # Hidden states
        if hasattr(outputs, "hidden_states") and outputs.hidden_states is not None:
            hs = outputs.hidden_states
            n_hidden = len(hs)
            shapes = [tuple(h.shape) for h in hs]
            print(f"[ok] hidden_states: {n_hidden} layers")
            for i, s in enumerate(shapes[:6]):
                print(f"     layer {i}: {s}")
            if n_hidden > 6:
                print(f"     ... ({n_hidden - 6} more)")
                print(f"     layer {n_hidden-1}: {shapes[-1]}")

            report["hidden_states"] = {
                "count": n_hidden,
                "shapes": [list(s) for s in shapes],
                "layer3_shape": list(shapes[3]) if n_hidden > 3 else None,
            }

            # Layer 3 last-token extraction (the bridge contract)
            if n_hidden > 3:
                layer3 = hs[3]
                last_token = layer3[:, -1, :]  # [batch, d_model]
                print(f"\n[KEY] Layer 3 last-token shape: {tuple(last_token.shape)}")
                print(f"      dtype: {last_token.dtype}")
                print(f"      norm: {last_token.norm().item():.4f}")
                print(f"      min/max: {last_token.min().item():.4f} / {last_token.max().item():.4f}")

                report["bridge_contract"] = {
                    "layer3_last_token_shape": list(last_token.shape),
                    "expected_shape": [1, 2560],
                    "shape_match": list(last_token.shape) == [1, 2560],
                    "width": last_token.shape[-1],
                    "expected_width": 2560,
                    "dtype": str(last_token.dtype),
                    "norm": round(last_token.norm().item(), 4),
                }
            else:
                report["bridge_contract"] = {"error": f"only {n_hidden} hidden layers, need >3"}
        else:
            print("[WARN] no hidden_states in output")
            report["hidden_states"] = {"error": "not available"}

        # SSM states (cache)
        if hasattr(outputs, "cache_params") and outputs.cache_params is not None:
            cache = outputs.cache_params
            cache_info = {"type": type(cache).__name__}
            if hasattr(cache, "ssm_states"):
                ssm = cache.ssm_states
                if isinstance(ssm, (list, tuple)):
                    cache_info["ssm_count"] = len(ssm)
                    cache_info["ssm_shapes"] = [list(s.shape) for s in ssm[:4]]
                elif hasattr(ssm, "shape"):
                    cache_info["ssm_shape"] = list(ssm.shape)
                print(f"[ok] SSM cache: {cache_info}")
            else:
                cache_attrs = [a for a in dir(cache) if not a.startswith("_")]
                cache_info["attrs"] = cache_attrs
                print(f"[ok] cache attrs: {cache_attrs}")
            report["ssm_cache"] = cache_info
        else:
            print("[info] no cache_params in output (expected for some configs)")
            report["ssm_cache"] = {"available": False}

        report["steps"]["forward"] = {"ok": True, "seq_len": seq_len}
    except Exception as e:
        print(f"[FAIL] forward pass: {e}")
        report["steps"]["forward"] = {"ok": False, "error": str(e)}
        traceback.print_exc()

    # Step 4: Compressor compatibility check
    print(f"\n--- Step 4: Compressor compatibility ---")
    try:
        bridge_contract = report.get("bridge_contract", {})
        width = bridge_contract.get("width")
        if width:
            # Current compressor: input_flat_size = d_model * d_state = 2560 * 1 = 2560
            current_input_size = 2560
            if width == current_input_size:
                verdict = "COMPATIBLE — same width, drop-in replacement"
            else:
                verdict = f"INCOMPATIBLE — width {width} vs expected {current_input_size}. Compressor projection layer needs reinitialization."

            report["compressor_compat"] = {
                "current_input_flat_size": current_input_size,
                "mamba3_width": width,
                "compatible": width == current_input_size,
                "verdict": verdict,
            }
            print(f"[KEY] {verdict}")
        else:
            report["compressor_compat"] = {"error": "no width data from forward pass"}
            print("[SKIP] no hidden state width to check")
    except Exception as e:
        print(f"[WARN] compressor check: {e}")
        report["compressor_compat"] = {"ok": False, "error": str(e)}

    # Step 5: Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    bc = report.get("bridge_contract", {})
    cc = report.get("compressor_compat", {})
    print(f"Model:             {args.model_id}")
    print(f"Model class:       {report['steps'].get('load', {}).get('model_class', '?')}")
    print(f"Hidden layers:     {report.get('hidden_states', {}).get('count', '?')}")
    print(f"Layer 3 last-tok:  {bc.get('layer3_last_token_shape', '?')}")
    print(f"Expected shape:    {bc.get('expected_shape', '?')}")
    print(f"Width match:       {bc.get('shape_match', '?')}")
    print(f"Compressor:        {cc.get('verdict', '?')}")
    ssm = report.get("ssm_cache", {})
    if ssm.get("ssm_shapes"):
        print(f"SSM state sample:  {ssm['ssm_shapes'][0]}")
    print(f"{'=' * 60}")

    dump_report(report, args)
    return 0


def dump_report(report, args):
    report_json = json.dumps(report, indent=2, default=str)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report_json)
        print(f"\nReport saved to: {args.output}")
    else:
        print(f"\n--- JSON REPORT ---")
        print(report_json)


def main():
    parser = argparse.ArgumentParser(description="Mamba-3 migration probe for MoCoP bridge")
    parser.add_argument("--model-id", required=True, help="HuggingFace model ID to probe")
    parser.add_argument("--device", default="cuda", help="Device (cuda or cpu)")
    parser.add_argument("--output", default=None, help="Output JSON path (default: stdout)")
    args = parser.parse_args()
    sys.exit(probe(args))


if __name__ == "__main__":
    main()
