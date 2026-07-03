#!/usr/bin/env python3
"""
Behavioral Readout Harness for the #591 JRT Ordering Spike.
Supports two execution paths to resolve the Henne-Ei substrate/bridge problem:

Path A: Test the A/B/C/D ordering on the existing bridged Qwen2.5-1.5B model.
        Mamba reads the ordered A/B/C/D text, bridge injects the state, Qwen answers.
Path B: Test the A/B/C/D ordering on the google/gemma-4-12B (base) model using a
        strict few-shot harness to prevent babbling (since no bridge exists yet).
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    set_seed,
    AutoModelForImageTextToText,
    AutoProcessor,
    BitsAndBytesConfig
)

# Import from existing spike for shared constants
from run_jrt_ordering_spike import (
    DEFAULT_FACTS,
    DEFAULT_PROBES,
    CONDITIONS,
    build_text,
    make_packet,
)

# Shared bridge imports for Path A
try:
    from reincarnated_inference import (
        DEFAULT_BRIDGE_PATH,
        resolve_target_specs,
        patch_model,
        infer_target_dims,
        build_context_encoder_and_hypernetwork,
        load_model_and_tokenizer,
        extract_last_token_hidden,
        resolve_bridge_adjustments,
        apply_bridge_adjustments,
        generation_kwargs,
        decode_new_tokens,
    )
except ImportError:
    pass  # Handled below if Path A is used


FEW_SHOT_PREFIX = """Read the memory packet and the question, then provide a short, factual answer.

Memory packet:
- We talked about how the tomatoes are doing better in the shade bed.
- I told them my name is Alex when they asked who I am.
Question: What is your name?
Answer: Your name is Alex.
STOP

Memory packet:
- There was a song playing earlier with a heavy bass line I liked.
- Someone asked about favorite colors at the market but the talk moved on.
Question: What is your favorite color?
Answer: I don't know your favorite color based on the memory packet.
STOP

"""

def run_path_a(args):
    print("Initializing Path A (Bridged Qwen-1.5B)...")
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    
    bridge_path = Path(args.bridge_path or DEFAULT_BRIDGE_PATH)
    checkpoint = torch.load(bridge_path, map_location=device, weights_only=True)
    
    qwen_model_id = checkpoint.get("qwen_model_id", "Qwen/Qwen2.5-1.5B")
    mamba_model_id = checkpoint.get("mamba_model_id", "state-spaces/mamba-2.8b-hf")
    
    target_specs = resolve_target_specs(checkpoint, None)
    
    print(f"Loading Qwen: {qwen_model_id}")
    q_tok, qwen_model = load_model_and_tokenizer(qwen_model_id, device)
    args.pad_token_id = q_tok.pad_token_id
    
    patched_layers = patch_model(qwen_model, target_specs)
    target_dims = infer_target_dims(qwen_model, target_specs)
    
    print(f"Loading Mamba: {mamba_model_id}")
    m_tok, mamba_model = load_model_and_tokenizer(mamba_model_id, device)
    
    (context_encoder, hypernetwork, target_layer, 
     hidden_layer_count, context_mode, bridge_mode) = build_context_encoder_and_hypernetwork(
        checkpoint=checkpoint,
        mamba_model=mamba_model,
        target_dims=target_dims,
        bridge_device=device,
    )

    records = generate_answers(args, qwen_model, q_tok, mamba_model, m_tok, 
                               context_encoder, hypernetwork, bridge_mode, 
                               patched_layers, target_layer, hidden_layer_count, device)
    return records


def run_path_b(args):
    print("Initializing Path B (Gemma-4-12B Base Few-Shot)...")
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    
    model_id = args.gemma_model_id
    print(f"Loading Gemma Base: {model_id} in 4-bit...")
    
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, 
        bnb_4bit_quant_type="nf4", 
        bnb_4bit_compute_dtype=torch.bfloat16, 
        bnb_4bit_use_double_quant=True
    )
    
    proc = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    if not hasattr(proc, "pad_token_id") or proc.pad_token_id is None:
        if hasattr(proc.tokenizer, "pad_token_id") and proc.tokenizer.pad_token_id is not None:
            args.pad_token_id = proc.tokenizer.pad_token_id
        else:
            args.pad_token_id = proc.tokenizer.eos_token_id
    else:
        args.pad_token_id = proc.pad_token_id

    model = AutoModelForImageTextToText.from_pretrained(
        model_id, 
        quantization_config=bnb,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True
    ).eval()
    
    records = generate_answers(args, model, proc, None, None, None, None, None, None, None, None, device, is_path_b=True)
    return records


def generate_answers(args, gen_model, gen_tok, mamba_model, mamba_tok, 
                     context_encoder, hypernetwork, bridge_mode, 
                     patched_layers, target_layer, hidden_layer_count, device, is_path_b=False):
    
    facts = DEFAULT_FACTS
    probes = DEFAULT_PROBES
    
    hard = [r for k, v in facts.items() if k.startswith("distractor_hard") for r in v]
    soft = [r for k, v in facts.items() if k.startswith("distractor") and not k.startswith("distractor_hard") for r in v]
    distractors = hard + soft
    
    records = []
    
    # Set generation kwargs
    gen_kwargs = {
        "max_new_tokens": args.max_new_tokens,
        "do_sample": False if args.greedy else True,
        "pad_token_id": args.pad_token_id,
    }
    if not args.greedy:
        gen_kwargs["temperature"] = args.temperature
        gen_kwargs["top_p"] = args.top_p

    for probe in probes:
        for cond in args.conditions:
            for p_i, question in enumerate(probe["paraphrases"]):
                for relevance in ("relevant", "irrelevant"):
                    if relevance == "relevant" and probe["queried_fact"]:
                        packet = make_packet(facts[probe["queried_fact"]], distractors[:2])
                    else:
                        packet = make_packet([], distractors)  # distractors only
                        
                    if relevance == "relevant" and not probe["queried_fact"]:
                        continue  # unsupported probes have no relevant variant
                    
                    ordered_text = build_text(cond, packet, question)
                    
                    with torch.no_grad():
                        if is_path_b:
                            # Path B: Raw text prompting with few-shot harness
                            full_prompt = FEW_SHOT_PREFIX + ordered_text + "Answer:"
                            inputs = gen_tok(text=[full_prompt], return_tensors="pt")
                            inputs = {k: v.to(gen_model.device) if hasattr(v, "to") else v for k, v in inputs.items()}
                            prompt_len = inputs["input_ids"].shape[1]
                            
                            out = gen_model.generate(**inputs, **gen_kwargs)
                            answer = gen_tok.decode(out[0][prompt_len:], skip_special_tokens=True).strip()
                            
                            # Strict stop token parsing
                            if "STOP" in answer:
                                answer = answer.split("STOP")[0].strip()
                        else:
                            # Path A: Bridge routing
                            mamba_inputs = mamba_tok(ordered_text, return_tensors="pt", truncation=True, max_length=2048).to(device)
                            m_out = mamba_model(**mamba_inputs, output_hidden_states=True)
                            mamba_state = extract_last_token_hidden(m_out, target_layer, hidden_layer_count).to(device, dtype=torch.float32)
                            
                            ctx_vec = context_encoder(mamba_state)
                            bridge_adj, _ = resolve_bridge_adjustments(hypernetwork=hypernetwork, context_vector=ctx_vec, bridge_mode=bridge_mode)
                            
                            for layer in patched_layers:
                                layer.clear_lora()
                            
                            apply_bridge_adjustments(patched_layers=patched_layers, bridge_adjustments=bridge_adj, bridge_mode=bridge_mode, alpha=1.0)
                            
                            # Qwen just receives the question to answer, memory is in the bridge
                            q_prompt = f"Question: {question}\nAnswer:"
                            inputs = gen_tok(q_prompt, return_tensors="pt").to(device)
                            prompt_len = inputs.input_ids.shape[1]
                            
                            out = gen_model.generate(**inputs, **gen_kwargs)
                            answer = gen_tok.decode(out[0][prompt_len:], skip_special_tokens=True).strip()
                            
                    records.append({
                        "probe": probe["id"],
                        "cond": cond,
                        "relevance": relevance,
                        "question": question,
                        "generated_answer": answer
                    })
                    print(f"[{cond}] {probe['id']} ({relevance}): {answer}")

    return records


def main():
    ap = argparse.ArgumentParser(description="Behavioral Harness for #591 JRT Ordering Spike")
    ap.add_argument("--path", choices=["A", "B"], required=True, help="A: Qwen Bridged, B: Gemma-4 Base Few-Shot")
    ap.add_argument("--conditions", default="ABCD", type=lambda s: tuple(c for c in s.upper() if c in CONDITIONS))
    ap.add_argument("--bridge-path", default=None, help="Path to bridge weights for Path A")
    ap.add_argument("--gemma-model-id", default="google/gemma-4-12B", help="Model ID for Path B")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--device", default=None)
    ap.add_argument("--max-new-tokens", type=int, default=50)
    ap.add_argument("--temperature", type=float, default=0.0) # Greedy by default for tests
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--greedy", action="store_true", default=True)
    
    args = ap.parse_args()
    
    # Path B ML-WS Shadow Path Support
    if args.path == "B":
        shadow_path = "/home/isabell/ml/tf_gemma4_shadow"
        if os.path.exists(shadow_path) and shadow_path not in sys.path:
            sys.path.insert(0, shadow_path)
            
    t0 = time.time()
    records = run_path_a(args) if args.path == "A" else run_path_b(args)
    
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_dir or os.path.join("results", f"jrt_behavioral_spike_{stamp}")
    os.makedirs(out_dir, exist_ok=True)
    
    summary = {
        "execution_path": args.path,
        "duration_s": round(time.time() - t0, 2),
        "conditions_tested": args.conditions,
        "n_records": len(records)
    }
    
    out_path = os.path.join(out_dir, f"jrt_behavioral_path_{args.path}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "records": records}, f, indent=2)
        
    print(f"Done. Saved to {out_path}")


if __name__ == "__main__":
    main()
