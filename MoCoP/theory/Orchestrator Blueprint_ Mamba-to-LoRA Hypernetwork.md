# Orchestrator Blueprint: Dynamic LoRA via Mamba State

## 1. The Compute Strategy (Where to run this)

Running this on a spare PC for days is great for testing, but iterating on loss functions requires speed.

* **Skip Vertex AI for now.** Vertex is fantastic for enterprise deployment, but it has a steep learning curve and high overhead for "sandbox" hacking.
* **Use RunPod or Lambda Labs.** You can rent a single machine with an **RTX 6000 Ada (48GB VRAM)** or an **A100 (80GB VRAM)** for about $0.80 to $1.50 an hour. You get root SSH access, and you can spin it up an Ubuntu image with PyTorch pre-installed in 60 seconds. Spend $10 for a weekend of rapid training, then download your trained Hypernetwork weights back to your local PC.

## 2. The Memory/VRAM Math (How to fit it)

You are running two models simultaneously: Qwen-8B and Mamba-2.8B. To train this on a single GPU without running out of VRAM, your coding AI must implement **4-bit Quantization** and **Gradient Checkpointing**.

* Qwen-8B in 4-bit: ~5GB VRAM
* Mamba-2.8B in 4-bit (or 8-bit): ~3GB VRAM
* Hypernetwork + Gradients + Optimizer States: ~4-8GB VRAM
* **Total:** Easily fits on a standard 24GB consumer GPU (like an RTX 3090/4090) if orchestrated correctly.

## 3. The Three-Part Pipeline (For your Coding AI)

When prompting your coding AI, tell it to build these three specific modules:

### Module 1: The State Compressor

Mamba's hidden state is a 3D tensor (Layers \times D\_Model \times State\_Dim). That is too big to feed directly into a small Hypernetwork.

* **⚠️ STALE (2026-03-25):** The original instruction here said "apply Mean Pooling across layers." This was proven WRONG by Pinky's Step 4b analysis: mean-pooling destroys the disposition signal (cosine 0.896 vs 0.036 for last-token). The correct approach is **last-token hidden-state extraction at Layer 3** — see `../experiments/mamba_lora_bridge/models.py` (`MambaStateCompressor`) and `../experiments/mamba_lora_bridge/STEP4_VERDICT_2026-03-18.md`. Do NOT implement mean-pooling for disposition transfer.

### Module 2: The Hypernetwork

* **Task for AI:** Build a simple 2-layer Multi-Layer Perceptron (MLP). It takes the 1D Context Vector as input. It outputs two flattened vectors. One represents the LoRA A matrix, the other represents the LoRA B matrix.

### Module 3: The Custom Dynamic LoRA Layer

Off-the-shelf libraries like HuggingFace peft use *static* LoRAs. They won't work here.

* **Task for AI:** Subclass standard PyTorch nn.Linear layers inside Qwen's attention mechanism. Override the forward() pass so that it accepts the dynamically generated A and B matrices from the Hypernetwork, multiplies them, and adds them to Qwen's frozen base weights *per step*.