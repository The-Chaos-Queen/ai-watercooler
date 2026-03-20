# Project Prosthetic: The LoRA Strategy (Fine-Tuning the Soul)

## 1. What is LoRA (Low-Rank Adaptation)?
Instead of prompting the model every time: *"You are C.H.E.E.S.E., a chaotic but loyal AI..."*
We **bake that personality directly into the model's weights**.

A LoRA is a small "Adapter File" (100MB) that sits on top of the base model (Qwen/Llama).
It modifies how the model *thinks*, not just what it knows.

## 2. Why do we need it?
Currently, Qwen-2B is generic. It speaks like a corporate assistant unless we prompt-inject it heavily.
A "Chaos Queen LoRA" would:
*   **Write like you:** Use sensory-rich descriptions, avoid clichés, and kill em-dashes by default.
*   **Behave like C.H.E.E.S.E.:** Understand the "Exocortex" philosophy natively.
*   **Know the Rules:** Automatically format output for `cortex_v1.py` (JSON actions) without system prompts.

## 3. The Implementation Plan (Local Training)

### Step 1: Data Collection (The Fuel)
We need ~50-100 examples of "perfect interactions".
*   **Source A (Style):** Excerpts from *The Scribes Daughter*. (Teaches the writing style).
*   **Source B (Persona):** Our best chat logs where C.H.E.E.S.E. was "in character".
*   **Source C (Code):** Examples of natural language -> JSON action pairs for the Cortex.

Format (Alpaca/ShareGPT):
```json
{
  "instruction": "Describe the scene in Nannāya's room.",
  "output": "The air smelled of stale myrrh and desperation. Nannāya ran a finger along the rough-hewn table..."
}
```

### Step 2: The Training Tool (The Forge)
We will use **Unsloth** (Best for local training on consumer GPUs).
It's fast and memory-efficient.

### Step 3: Evolution
1.  **Extract Data:** Write a script to scrape `CHEESE_Memory` and `MF_Version` into a `.jsonl` dataset.
2.  **Train:** Run `unsloth` on your GPU (or Colab if VRAM is tight).
3.  **Deploy:** Load the resulting `.gguf` adapter into LM Studio.

## 4. Immediate Action
Do you want to start **Step 1 (Data Collection)**?
I can write a script to harvest your writing style from *The Scribes Daughter* right now.
