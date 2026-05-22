# SAS (Sequential Adaptive Steering) Integration Design

## 1. Objective
To address the "dispositional overwhelm" and factual collapse observed in the Step 5 browser probe. This document outlines a plan to evolve the Adrenaline Bridge from a single, raw disposition injection mechanism into a multi-dimensional, controllable "personality slider" system, based on the findings of the peer review and the "Personality Sliders" paper (Hoppe et al., 2026).

The primary goal is to produce a persona that is coherent and "feels good in its own skin," balancing a distinct personality with the base model's factual capabilities.

## 2. Core Concepts from Hoppe et al. (2026)

Our implementation will be based on two key innovations from the SAS paper:

*   **Sequential Orthogonalization:** To prevent different personality vectors from interfering with each other (representation collapse), they are trained sequentially. The steering vector for `trait_B` is trained on activations already steered by `trait_A`, forcing it to learn an orthogonal direction.
*   **Fisher Ratio for Layer Selection:** Instead of manually choosing injection layers, a data-driven metric (Fisher Ratio) is used to automatically identify the optimal intervention layer for each specific personality trait, maximizing the signal-to-noise ratio for that trait.

## 3. Proposed Architectural Changes

### 3.1. Hypernetwork Modification (`cognitive_bridge.py`)

The `ActivationBiasHypernetwork` will be redesigned.
*   **Current:** Outputs a list of raw, high-dimensional bias vectors.
*   **Proposed:** Outputs a set of scalar **alpha coefficients**, one for each target personality trait (e.g., `{'openness': 0.7, 'conscientiousness': -0.4, ...}`). The Mamba state will now determine the *intensity* of pre-defined traits, not the entire steering direction from scratch.

### 3.2. Steering Vector Store

We will create a library of pre-computed, orthogonal **basis vectors**.
*   These vectors will represent the core personality traits (e.g., the Big Five: Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism).
*   They will be trained offline, once, using the sequential orthogonalization method.
*   They will be stored as standalone `.pt` files (e.g., `sas_vectors_qwen1.5b_layer8.pt`).

### 3.3. New Injection Logic (`cognitive_bridge.py`)

The inference-time injection logic will be updated to perform the following steps:
1.  Load the pre-computed orthogonal basis vectors for the target injection layer.
2.  Pass the Mamba state through the (retrained) hypernetwork to get the alpha coefficients for the current disposition.
3.  Calculate the final bias vector by taking a weighted sum: `final_bias = (alpha_1 * basis_vector_1) + (alpha_2 * basis_vector_2) + ...`
4.  Inject this `final_bias` into the target Qwen layer(s).

## 4. New Scripts Required

To support this new architecture, two new scripts will be necessary:

1.  **`probe_layers.py`**: An implementation of the Fisher Ratio probe to identify the optimal injection layer for each of the Big Five traits on our target Qwen models.
2.  **`train_sas_vectors.py`**: A script to perform the one-time, sequential training process that generates the orthogonal basis vectors.

## 5. Proposed "Step 6" Experiment Ladder

This new architecture leads to a clear, sequential plan to supersede the current Step 5.

*   **Step 6a (Probing):** Run `probe_layers.py` to identify the best injection layers (e.g., likely in the 6-11 range) for the Big Five traits on Qwen-1.5B.
*   **Step 6b (Vector Training):** Use `train_sas_vectors.py` to generate and save the orthogonal basis vectors for the layers identified in Step 6a.
*   **Step 6c (Bridge Retraining):** Re-train the Adrenaline Bridge. The Mamba state from the CHEESE episodes will be mapped to the target *alpha coefficients* that best represent that episode's personality, rather than to raw activation vectors.
*   **Step 6d (Evaluation):** Re-run the qualitative evaluation (ideally with the "clean" chat UI). We will experiment with manually adjusting the alpha sliders at inference time to test our ability to "tune" the persona, finding a balance between disposition and factual recall.

This design provides a clear path toward a more stable, interpretable, and controllable implementation of the MoCoP architecture.
