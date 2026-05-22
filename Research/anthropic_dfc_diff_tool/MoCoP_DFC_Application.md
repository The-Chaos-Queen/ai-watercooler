# DFC: Dedicated Feature Crosscoder (Anthropic, March 2026)
**Relevance to MoCoP Task #45 (Mamba-to-Qwen Rosetta Stone)**

## The Problem (Cross-Architecture Diffing)
Standard crosscoders try to force a 1:1 mapping between the features of two different models (like a basic bilingual dictionary). This fails when one model has a feature the other physically cannot represent. Forcing a match hides the unique, emergent behaviors.

## Anthropic's Solution: The DFC
Instead of a single mapping matrix, the DFC explicitly builds a 3-part dictionary:
1. **Shared Dictionary:** Concepts/features that both models represent equally well.
2. **Model A Exclusive Section:** Features unique to Model A.
3. **Model B Exclusive Section:** Features unique to Model B.

## Application to MoCoP (Mamba $\rightarrow$ Qwen Bridge)
When building the "Rosetta Stone" bridge to map Mamba's continuous state ($h_t$) into Qwen's attention heads (Task #45), we **must not force a 1:1 cosine alignment**. 

If we use a naive crosscoder, we will force Qwen to try and represent Mamba's deep recurrent history features that Qwen's attention mechanism fundamentally lacks, resulting in geometric collapse (the "autocomplete soup").

**The DFC Implementation Plan for the Bridge:**
1. **Shared Features:** Extract the dispositional features that both Mamba and Qwen understand (e.g., "warmth", "uncertainty", "formality"). This is the primary injection vector where `alpha` applies cleanly.
2. **Mamba-Exclusive Features:** Identify features in Mamba that represent deep temporal recurrence (things Qwen cannot hold in its KV-cache). The bridge must *translate* these into something Qwen understands, rather than forcing a direct mapping.
3. **Qwen-Exclusive Features:** Identify Qwen's structural attention features (e.g., benchmark-following, XML-tag parsing). The bridge should explicitly *avoid* activating these features during the Mamba injection, to prevent the D2 leakage (roleplay/benchmark hallucinations).

**Conclusion:** The DFC architecture proves that behavioral disposition is decomposable into steerable features, and that cross-architecture steering works in production. We must update the `cognitive_bridge.py` training script to use a 3-part DFC loss function instead of a simple MSE/Cosine similarity loss.
