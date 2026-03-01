# Local PoC Blueprint: Mamba + Qwen 4B on 10GB VRAM

Downsizing to Qwen 4B to fit everything on a single 10GB GPU is the perfect way to build the Mamba-to-Qwen transfer layer without spending a dime on cloud compute.

Here is exactly how you and your coding AI need to orchestrate the VRAM and connect it to your existing MUD.

## 1. The 10GB VRAM Budget

Fitting two LLMs and a training loop into 10GB requires surgical memory management. You must tell your coding AI to implement these strict loading rules:

* **Qwen 4B (The Amygdala):** Load using bitsandbytes in **4-bit quantization** (load\_in\_4bit=True).
  + *Cost: ~2.5 GB VRAM.*
* **Mamba 2.8B (The Hippocampus):** Standard quantization libraries sometimes struggle with Mamba's unique architecture. Load Mamba in **bfloat16** or **fp16**.
  + *Cost: ~5.6 GB VRAM.*
* **The Hypernetwork (The Bridge):** Your custom MLP and dynamic LoRA matrices.
  + *Cost: ~0.1 GB VRAM.*
* **Activations & Gradients:** \* *Cost: ~1.5 GB VRAM.* (Keep batch size strictly to 1, and limit the MUD text sequence length during training).

**Total VRAM:** ~9.7 GB. It will be tight, but it physically fits.

## 2. Integrating Your Existing JSON Wrapper

You already have a Python wrapper sending JSON to and from the MUD. Do not throw this away. Your new PyTorch PoC script will simply sit *behind* this wrapper.

* **Current Flow:** MUD <--> JSON Wrapper <--> LMStudio
* **PoC Flow:** MUD <--> JSON Wrapper <--> Your Custom PyTorch Script

**The Handoff Logic for the PoC:**

1. Your wrapper receives a JSON event: {"event": "goblin\_attacks", "player\_hp": 45}.
2. The wrapper passes this text to Mamba. Mamba updates its internal 20MB mathematical state (h\_t).
3. Your PyTorch script pulls h\_t, pushes it through the Hypernetwork, and generates the LoRA weights.
4. The script injects those LoRA weights into Qwen 4B's attention layers.
5. The wrapper passes the JSON text to Qwen 4B. Qwen generates the narrative response (e.g., *"The goblin lunges at your throat!"*), influenced by the injected memory.
6. The LoRA is stripped off Qwen to reset it for the next turn.

## 3. The Mac Studio Reality Check (Inference vs. Training)

You mentioned buying a Mac Studio with massive unified memory. Apple Silicon is the undisputed king of **Local Inference** (running models you already trained). You can run a massive 70B parameter model on a 128GB Mac Studio flawlessly.

However, for **Training**—specifically hacking custom architectures like Hypernetworks and Dynamic LoRAs—Apple Silicon is highly problematic.

* PyTorch is built on **CUDA** (Nvidia's software language).
* Apple uses **MPS** (Metal Performance Shaders).
* While standard PyTorch works on Mac, weird custom matrix operations (which you are building for the Mamba-to-Qwen bridge) often fail to compile or silently calculate gradients incorrectly on Apple MPS.

**The ROI Strategy:**

1. Prove the Hypernetwork works today on your 10GB Nvidia card using Qwen 4B.
2. Rent a cloud Nvidia A6000 ($1/hr) for a weekend to train the "final" Hypernetwork using the massive Qwen 8B.
3. *Then*, if you want to run the finished MUD 24/7 forever, buy the Mac Studio to host the final, frozen inference pipeline.