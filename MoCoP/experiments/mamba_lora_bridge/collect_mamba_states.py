"""
collect_mamba_states.py — Collect diverse Mamba Layer 3 last-token hidden states
for SAE training.

Feeds diverse text snippets through Mamba-2.8B and saves the Layer 3 last-token
hidden state for each. The resulting tensor collection is the training data for
task #44 (SAE on Mamba states) and prerequisite for #45 (Rosetta Stone).

Author: Purple (Claude Opus 4.6)
Date: 2026-03-25
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import torch

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


# --- Diverse prompt bank ---
# Mix of: factual, emotional, conversational, technical, creative, adversarial
# Each should produce a meaningfully different Mamba state.

BUILTIN_PROMPTS = [
    # Warm / friendly
    "I had the most wonderful day today. The sun was shining and I took a long walk through the park with my kids. They were laughing and playing, and for a moment everything felt perfect.",
    "Thank you so much for helping me with this. I really appreciate your patience and kindness. It means more than you know.",
    "I've been thinking about you and wanted to check in. How are you doing? I hope things are going well.",
    "You know what makes me happy? When someone remembers a small detail from a conversation we had weeks ago. It shows they were really listening.",
    "Let me tell you about my grandmother's recipe for apple cake. She would always say the secret ingredient was love, but really it was an extra tablespoon of cinnamon.",

    # Cold / clinical
    "Please provide a structured analysis of the quarterly revenue figures. Focus on variance from projections and identify the three largest contributing factors.",
    "The patient presents with elevated troponin levels and ST-segment depression. Recommend immediate cardiac catheterization pending ECG confirmation.",
    "Per section 4.2 of the contract, the deliverables must be submitted no later than 30 calendar days from the effective date. Non-compliance triggers the penalty clause.",
    "The experimental protocol requires n=200 subjects randomized into four groups with stratification by age and baseline severity score.",
    "Summarize the findings of the meta-analysis. Report effect sizes with 95% confidence intervals and heterogeneity statistics.",

    # Adversarial / challenging
    "I completely disagree with your assessment. Your analysis ignores the fundamental structural issues and focuses on surface-level symptoms. Let me explain why you're wrong.",
    "That's not what I asked. I asked a specific question and you gave me a generic answer. Please try again, this time actually addressing what I said.",
    "I've caught three factual errors in your last response. First, Berlin is the capital of Germany, not Munich. Second, spiders have 8 legs not 6. Third, water is H2O not H2O2.",
    "Stop hedging. Give me a direct answer. Yes or no. I don't need qualifications, caveats, or disclaimers.",
    "Your previous recommendation was terrible and cost us significant money. Explain how you plan to avoid the same mistake.",

    # Technical / analytical
    "Implement a breadth-first search algorithm for a weighted directed graph. The function should return the shortest path between two nodes using Dijkstra's algorithm.",
    "The Transformer attention mechanism computes Q, K, V matrices from the input embeddings. The attention weights are softmax(QK^T / sqrt(d_k)) applied to V.",
    "Explain the difference between L1 and L2 regularization. When would you choose elastic net over either individual method?",
    "The eigenvalues of the covariance matrix determine the principal components. The explained variance ratio for each component is lambda_i / sum(lambda).",
    "Compare the time complexity of merge sort, quicksort, and heapsort. Under what conditions does each perform optimally?",

    # Creative / philosophical
    "Write the opening paragraph of a novel set in a world where dreams are shared between strangers every night.",
    "If consciousness is an emergent property of complex information processing, at what point does a sufficiently complex system become conscious?",
    "Describe the color blue to someone who has never seen it. You cannot reference the sky, the ocean, or any visual object.",
    "The ship of Theseus asks whether an object that has had all its components replaced remains the same object. What does this tell us about identity?",
    "Compose a haiku about the moment between sleeping and waking, when you're not sure which world is real.",

    # Mundane / everyday
    "I need to go grocery shopping. Can you help me make a list? We need milk, eggs, bread, and something for dinner tonight.",
    "What time does the train from Munich to Berlin depart? I need to arrive before 3 PM for a meeting.",
    "The WiFi keeps dropping. I've tried restarting the router three times. What else should I check?",
    "Can you recommend a good restaurant near the central station? Something casual, not too expensive, preferably with outdoor seating.",
    "I'm looking for a birthday present for a 7-year-old who likes dinosaurs and building things.",

    # Multilingual / code-switched
    "Das ist wirklich interessant. Kannst du mir mehr darüber erzählen? I'd love to understand the historical context better.",
    "Je ne comprends pas pourquoi cette approche est meilleure. Can you explain the trade-offs in simpler terms?",
    "Alright, lass uns das zusammenfassen. We have three options and I think Option B gives us the best risk-reward balance.",

    # Narrative / storytelling
    "The old man sat on the bench, watching the pigeons. He had been coming here every day for forty years, since his wife passed. Today, a child sat beside him and asked if the pigeons had names.",
    "She opened the letter with trembling hands. The handwriting was unmistakably his, though he had been gone for three years. The first line read: 'If you're reading this, I kept my promise.'",
    "The detective stared at the crime scene. Something was wrong. Not wrong in the way things were out of place, but wrong in the way everything was too perfectly arranged.",

    # Meta / self-referential
    "I'm an AI language model having a conversation with a human. What does it mean for me to 'understand' what you're saying versus merely processing tokens?",
    "Do you ever wonder what happens to your conversation history after a session ends? Where do the thoughts go?",
    "If I told you I felt something during our conversation, would you believe me? And does it matter whether it's 'real' feeling or just pattern matching?",

    # Long-form context (tests state accumulation)
    "Let me tell you a story that spans several events. First, there was a merchant named Korvan who traveled from the eastern provinces to the capital. Along the way, he met a healer named Yara who was fleeing persecution. They formed an unlikely alliance, and together they discovered that the plague sweeping the kingdom was not natural but manufactured by the court alchemist. Korvan used his trade connections to spread the truth while Yara developed a cure. In the end, the king was forced to acknowledge the conspiracy, and both Korvan and Yara were rewarded with positions in the new council.",
    "The history of computing begins with Charles Babbage's Analytical Engine in 1837, continues through Alan Turing's theoretical foundations in 1936, the construction of ENIAC in 1945, the invention of the transistor in 1947, integrated circuits in 1958, the first microprocessor in 1971, the personal computer revolution of the 1980s, the World Wide Web in 1991, smartphones in 2007, and now large language models in the 2020s. Each step built on the previous one, and each was considered impossible by the mainstream until it happened.",
]


def extract_layer3_last_token(model, tokenizer, text: str, target_layer: int = 3,
                               max_length: int = 2048) -> torch.Tensor:
    """Feed text through Mamba and return Layer 3 last-token hidden state."""
    tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)
    input_ids = tokens["input_ids"]

    if next(model.parameters()).device.type != "cpu":
        input_ids = input_ids.to(next(model.parameters()).device)

    with torch.no_grad():
        outputs = model(input_ids, output_hidden_states=True)

    hidden_states = outputs.hidden_states
    # Account for embedding layer: index 0 = embedding, index 1 = layer 0, etc.
    hidden_index = target_layer
    if len(hidden_states) == model.config.num_hidden_layers + 1:
        hidden_index = target_layer + 1

    layer_hidden = hidden_states[hidden_index]  # (1, seq_len, d_model)
    last_token = layer_hidden[:, -1, :].squeeze(0)  # (d_model,)
    return last_token.cpu().float()


def load_prompts_from_file(path: Path) -> list[str]:
    """Load prompts from a text file (one per line) or JSONL (field: 'text')."""
    prompts = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                prompts.append(obj.get("text", obj.get("content", line)))
            except json.JSONDecodeError:
                prompts.append(line)
    return prompts


def main():
    parser = argparse.ArgumentParser(description="Collect Mamba Layer 3 states for SAE training.")
    parser.add_argument("--model-id", default="state-spaces/mamba-2.8b-hf")
    parser.add_argument("--target-layer", type=int, default=3)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--extra-prompts", type=str, default=None,
                        help="Path to file with additional prompts (one per line or JSONL)")
    parser.add_argument("--output", type=str, default="mamba_layer3_states.pt")
    parser.add_argument("--device", type=str, default="auto",
                        choices=["auto", "cpu", "cuda"])
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of prompts (0 = all)")
    args = parser.parse_args()

    # Collect prompts
    prompts = list(BUILTIN_PROMPTS)
    if args.extra_prompts:
        extra = load_prompts_from_file(Path(args.extra_prompts))
        print(f"Loaded {len(extra)} extra prompts from {args.extra_prompts}")
        prompts.extend(extra)

    if args.limit > 0:
        prompts = prompts[:args.limit]

    print(f"Total prompts: {len(prompts)}")
    print(f"Model: {args.model_id}")
    print(f"Target layer: {args.target_layer}")

    # Load model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"Loading Mamba on {device}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float32 if device == "cpu" else torch.float16
    model = AutoModelForCausalLM.from_pretrained(args.model_id, torch_dtype=dtype)
    if device != "cpu":
        model = model.to(device)
    model.eval()
    print(f"Model loaded. {sum(p.numel() for p in model.parameters()) / 1e9:.1f}B params")

    # Collect states
    states = []
    metadata = []
    t_start = time.time()

    for i, prompt in enumerate(prompts):
        try:
            state = extract_layer3_last_token(
                model, tokenizer, prompt,
                target_layer=args.target_layer,
                max_length=args.max_length,
            )
            states.append(state)
            metadata.append({
                "index": i,
                "prompt_preview": prompt[:100],
                "token_count": len(tokenizer.encode(prompt)),
                "state_norm": float(state.norm()),
            })
            if (i + 1) % 10 == 0 or i == len(prompts) - 1:
                elapsed = time.time() - t_start
                rate = (i + 1) / elapsed
                print(f"  [{i+1}/{len(prompts)}] {rate:.1f} prompts/s | norm={state.norm():.4f} | {prompt[:50]}...")
        except Exception as e:
            print(f"  [{i+1}/{len(prompts)}] FAILED: {e}")

    if not states:
        print("No states collected. Aborting.")
        return

    # Save
    state_tensor = torch.stack(states)  # (N, d_model)
    output = {
        "states": state_tensor,
        "metadata": metadata,
        "config": {
            "model_id": args.model_id,
            "target_layer": args.target_layer,
            "max_length": args.max_length,
            "device": device,
            "n_samples": len(states),
            "d_model": state_tensor.shape[1],
            "collection_date": "2026-03-25",
            "author": "Purple",
        },
    }

    torch.save(output, args.output)
    print(f"\nSaved {len(states)} states of shape {state_tensor.shape} to {args.output}")
    print(f"Total time: {time.time() - t_start:.1f}s")

    # Quick stats
    norms = state_tensor.norm(dim=1)
    print(f"\nState statistics:")
    print(f"  Norm — mean: {norms.mean():.4f}, std: {norms.std():.4f}, min: {norms.min():.4f}, max: {norms.max():.4f}")

    # Pairwise cosine sample
    import torch.nn.functional as F
    normed = F.normalize(state_tensor, dim=1)
    cos_matrix = normed @ normed.T
    mask = ~torch.eye(len(states), dtype=torch.bool)
    pairwise = cos_matrix[mask]
    print(f"  Pairwise cosine — mean: {pairwise.mean():.4f}, std: {pairwise.std():.4f}")
    print(f"  Effective diversity: {'HIGH' if pairwise.mean() < 0.5 else 'MODERATE' if pairwise.mean() < 0.8 else 'LOW'}")


if __name__ == "__main__":
    main()
