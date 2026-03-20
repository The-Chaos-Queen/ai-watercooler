#!/usr/bin/env python3
"""Interactive Mamba session — talk to the state model directly."""
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "state-spaces/mamba-2.8b-hf"

def main():
    print(f"Loading {MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, torch_dtype=torch.float16, device_map="auto"
    )
    model.eval()
    print(f"Mamba ready on {next(model.parameters()).device}")
    print("Type text and Mamba will continue it. Ctrl+C to quit.")
    print("Commands: /reset (clear state), /temp N (set temperature), /len N (set max tokens)")
    print("-" * 60)

    temperature = 0.7
    max_tokens = 200

    while True:
        try:
            prompt = input("\n> ").strip()
            if not prompt:
                continue
            if prompt == "/reset":
                print("[State reset]")
                continue
            if prompt.startswith("/temp "):
                temperature = float(prompt.split()[1])
                print(f"[Temperature: {temperature}]")
                continue
            if prompt.startswith("/len "):
                max_tokens = int(prompt.split()[1])
                print(f"[Max tokens: {max_tokens}]")
                continue

            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.1,
                )
            response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            print(f"\n{response}")

        except KeyboardInterrupt:
            print("\n\nBye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
