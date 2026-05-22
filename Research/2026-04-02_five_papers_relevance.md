# MoCoP Relevance Digest: Anthropic & Interpretability Papers
**Date:** April 2, 2026

The five newly extracted papers provide critical theoretical backing and methodological tools for the MoCoP (Memory of Conversational Partners) project, particularly for understanding how the Qwen transformer processes the Mamba activation biases.

### 1. Circuit Tracing & Attribution Graphs (Biology & Methods)
* **Papers:** "On the Biology of a Large Language Model" & "Circuit Tracing: Revealing Computational Graphs in Language Models" (Anthropic)
* **Relevance to MoCoP:** These papers introduce cross-layer transcoders and attribution graphs. MoCoP relies on injecting state (from Mamba) into a frozen Qwen model (at layers 12-15 `v_proj`). Anthropic's method of tracing how specific features causally influence downstream layers is exactly the framework we need to understand *how* the Mamba injection alters Qwen's internal computational graphs and leads to the "disposition shifts" (e.g., the "Rabbit Hole of Subjectivity").

### 2. Tracing Attention Computation (Attention QK)
* **Paper:** "Tracing Attention Computation Through Feature Interactions" (Anthropic)
* **Relevance to MoCoP:** This piece explores how features interact across the query-key (QK) mechanism to drive attention. In MoCoP, when we recall a memory from Qdrant, we want to know how Qwen attends to that memory. Understanding QK attributions can help us verify if Qwen is genuinely attending to the injected Mamba state/memory anchors or if it's relying on shallow heuristics.

### 3. The Logit Lens
* **Paper:** "Interpreting GPT: the logit lens" (nostalgebraist, LessWrong)
* **Relevance to MoCoP:** The logit lens involves decoding intermediate transformer layers directly to the vocabulary. This is a brilliant, lightweight diagnostic tool for the MoCoP bridge. We can apply the logit lens to Qwen's residual stream right *before* and right *after* the Mamba activation bias injection (Layer 12-15) to see in real-time how the injection shifts Qwen's internal "beliefs" or token predictions.

### 4. Scaling Monosemanticity
* **Paper:** "Scaling Monosemanticity: Extracting Interpretable Features from Claude 3 Sonnet" (Anthropic)
* **Relevance to MoCoP:** This is the foundational paper on Sparse Autoencoders (SAEs) scaling to production models. It proves that complex behaviors (like emotional states, deception, sycophancy) are mediated by linear feature directions. This validates our core hypothesis: MoCoP's activation bias bridge works because Mamba is essentially acting as a dynamic feature-steering vector, shifting Qwen's monosemantic feature activations along relational or emotional dimensions.
