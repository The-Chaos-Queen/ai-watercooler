<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Do a deep research on academic papers with the rough keyword cloud of: Cross-model hidden state transfer SSM Mamba RWKV learned adapter mapping latent space alignment

Here’s a mapped overview of work that’s directly relevant to “cross‑model hidden state transfer / SSM / Mamba / RWKV / learned adapter mapping / latent space alignment”, plus some concrete design patterns you can steal.

## 1. Direct cross‑architecture transfer to Mamba

### TransMamba (Transformer → Mamba distillation)

TransMamba explicitly tackles cross‑architecture training: transferring a trained Transformer into a Mamba model.[^1]

Core ideas:

- Project intermediate features from both models into an **aligned latent space** before matching them.[^1]
- Use an Adaptive Bidirectional distillation scheme that allows different layer counts and depths.[^1]

Mechanically, what they do is very close to “learned adapter mapping of hidden states”:

- Let $H_T^l$ be hidden states from Transformer layer $l$, and $H_M^{l'}$ from Mamba block $l'$.
- Learn projections $P_T, P_M$ such that $Z_T = P_T(H_T^l)$, $Z_M = P_M(H_M^{l'})$ live in a shared latent space.[^1]
- Minimize distillation losses (e.g. L2, KL, or contrastive) between $Z_T$ and $Z_M$.[^1]

This gives you a practical recipe for cross‑model hidden state alignment between fundamentally different sequence models (attention vs SSM).

## 2. Cross‑modal and cross‑stream Mamba variants (hidden state fusion)

Several recent Mamba papers implement “information transfer layers” between separate state‑space streams – effectively cross‑model latent fusion modules that you can generalize.

### Pan‑Mamba (cross‑modal Mamba, channel‑swapping Mamba)

Pan‑Mamba introduces two mechanisms for cross‑modal information exchange between panchromatic and multispectral streams.[^2]

- **Channel swapping Mamba**: exchanges partial channels between modality‑specific feature maps to create a light‑weight cross‑modal interaction; this is akin to a fixed but learnable permutation/interleaving of hidden dimensions between two models.[^2]
- **Cross‑modal Mamba**: a customized block where the state‑space evolution in one stream is explicitly influenced by features from the other stream, i.e., the hidden state update has cross‑stream input.[^2]

Conceptually, both are patterns for “cross‑model hidden state transfer”: you keep separate SSMs but insert structured mixing layers (channel swap, cross‑Mamba block) to share latent information.

### Coupled Mamba (multi‑modal fusion via coupled SSMs)

Coupled Mamba targets multi‑modal fusion and notes that standard fusion modules are not well‑suited to the dynamics of SSMs.[^3]

Key ingredients:

- Treat each modality as a separate Mamba stream.
- Design **coupling terms** in the state evolution so that each stream’s next hidden state depends not just on its own previous state and input, but also on a transformed version of other streams’ states.[^3]

This is very close to “hidden state transfer layers” between two recurrent/state‑space models with different dynamics, and offers a blueprint for RWKV↔Mamba or Transformer↔Mamba coupling.

### Mamba‑ST (Mamba as cross‑attention surrogate)

Mamba‑ST adapts the Mamba equations to **simulate cross‑attention**, combining two separate embeddings into a single output stream for style transfer.[^4][^5]

- They modify Mamba’s inner equations to accept two inputs and fuse them, acting like cross‑attention but with linear complexity.[^5][^4]

Again, this is a concrete pattern for cross‑stream latent alignment via a single SSM block that “consumes” and fuses two hidden representations.

### MambaTron, Multimodal Mamba, Mixture‑of‑Mamba

- **MambaTron**: cross‑modal point‑cloud enhancement using a selective state‑space modeling scheme to fuse image and point‑cloud views; uses Mamba for cross‑modal enhancement, implying hidden state transfer from image encodings into point‑cloud SSM.[^6]
- **Multimodal Mamba (mmMamba)**: distills a multimodal Transformer into a native multimodal Mamba; includes a “Cross‑SSD module” and cross‑modal alignment using shared projections for sequence‑level alignment.[^7][^8]
- **Mixture‑of‑Mamba**: introduces modality‑aware sparsity with modality‑specific parameterization of Mamba blocks; useful as a template for per‑model adapters in a shared SSM backbone.[^9]

All three are variations on “shared SSM core + modality/model‑specific adapters + latent alignment constraints”.

## 3. Latent space partitioning and alignment

### Domain‑adaptive Mamba (Damba‑ST)

Damba‑ST is about domain transfer for urban spatio‑temporal prediction, but the structural idea is highly relevant.[^10]

- Latent space is explicitly partitioned into:
    - A **shared subspace** for cross‑domain commonalities.
    - Domain‑specific subspaces for per‑domain/distribution features.[^10]
- Three **Domain Adapters** operate on this factorized representation to adapt to new domains while retaining shared knowledge.[^10]

This is an explicit latent space alignment strategy: constrain some latent dimensions to be shared and some to be private, then learn adapters that map domain‑specific representations into the shared subspace.

You can apply exactly the same idea across architectures (e.g., a shared Mamba latent space with per‑model adapters for RWKV, Transformer, etc.).

### CLIP‑Mamba, vision backbones

- **CLIP‑Mamba**: trains Mamba models using CLIP‑style contrastive pretraining; implicitly aligns visual and textual latent spaces via a shared projection used in the contrastive loss.[^11]
- **Vision Mamba (Vim)**: purely SSM‑based vision backbone that replaces self‑attention; its relevance is mostly that it shows Mamba hidden states can be used as general‑purpose latent features for downstream heads, which is useful if you want a unified latent space across modalities.[^12]

These give you evidence that “alignment via shared projection and contrastive loss” is workable in Mamba‑based architectures.

## 4. Hidden state–based guidance for transfer / adapters

### Hidden State Variability for transfer decisions

“Hidden State Variability of Pretrained Language Models Can Guide Computation Reduction for Transfer Learning” shows that you can use properties of hidden states (within‑class variability, etc.) to decide which layers to adapt or attach heads to.[^13]

Core observations:

- Layers whose hidden states already show low within‑class variability for a task (i.e., are “well specialized”) need less adaptation.[^13]
- This criterion can guide **adapter placement** and reduce compute.[^13]

While they don’t transfer between architectures, the method suggests using statistics of hidden state geometry as a signal for where and how to place cross‑model adapters.

### Multi‑modal RNNs with information transfer layers

Pre‑Mamba but conceptually close: “Multimodal Recurrent Neural Networks With Information Transfer Layers” for RGB‑D scene labeling.[^14]

- Two RNNs (RGB and depth) are cross‑connected via learnable **information transfer layers** between hidden states.[^14]
- Each RNN updates its state using both its own previous hidden state and transformed hidden state from the other stream.[^14]

This is exactly the architecture you’d want for cross‑model hidden state transfer between, say, a RWKV and Mamba stream: each step combines its own state and a projected state from the other model.

## 5. RWKV‑specific notes

There is less explicit academic work on RWKV↔other‑model hidden state transfer, but conceptually:

- RWKV is a “linear‑attention‑like” RNN where the hidden state is a compressed representation of past keys/values and outputs; structurally it’s closer to SSMs than to classic LSTMs.
- The patterns above (projecting hidden states into a shared latent space, coupled hidden‑state evolution, cross‑Mamba/Cross‑SSD blocks) can be adapted: treat RWKV’s hidden state exactly like a Mamba state and define a learned projection into a shared space for alignment/distillation.

In practice, for cross‑model hidden state transfer RWKV↔Mamba you’d likely:

- Learn per‑model adapters $A_{\text{RWKV}}, A_{\text{Mamba}}$ mapping their internal state representations to a shared latent space.
- Train with representation distillation (L2/contrastive) and possibly cross‑predictive objectives (next‑token logits matching, masked state prediction) in that shared space, similar to TransMamba.[^1]


## 6. Design patterns you can directly reuse

### 6.1 Shared latent space + per‑model adapters

Inspired by TransMamba, CLIP‑Mamba, Damba‑ST:

- For each model $M_i$ (Transformer, Mamba, RWKV):
    - Choose one or more layers and define hidden states $H_i^l$.
    - Learn adapters $A_i$ that map $H_i^l$ into a **shared latent space** $Z_i = A_i(H_i^l)$.[^11][^10][^1]
- Train with:
    - Distillation loss between teacher and student $Z$’s.[^1]
    - Contrastive alignment if you want robustness across tasks/modalities.[^11]
    - Optional orthogonality / variance regularizers to explicitly partition shared vs private subspaces.[^10]

This is the cleanest way to do cross‑model hidden state alignment without forcing architectures to match.

### 6.2 Coupled state‑space evolution

Borrowing from Coupled Mamba, Pan‑Mamba, and multimodal RNNs:[^3][^14][^2]

- Maintain separate recurrent/SSM streams for each model or modality.
- At each step, update each stream’s hidden state as:
    - $h_i^{t+1} = f_i(h_i^t, x_i^t) + g_{i\leftarrow j}(h_j^t)$, where $g_{i\leftarrow j}$ is a learned transfer function from model $j$’s state.
- Implement $g$ using a small MLP or state‑space block (cross‑Mamba style) so that transfer respects the temporal structure.[^2][^3]

This gives you a tight, recurrent coupling between models, suitable for on‑line test‑time collaboration between architectures.

### 6.3 Latent partitioning for alignment

From Damba‑ST’s domain‑adaptive SSM:[^10]

- Explicitly split the latent representation into: $z = [z_{\text{shared}}, z_{\text{private}}]$.
- Impose:
    - Cross‑model alignment losses only on $z_{\text{shared}}$.[^10]
    - Regularization to keep $z_{\text{private}}$ decorrelated across models, so they can encode architecture‑specific inductive biases.[^10]

This gives you controlled alignment: enough shared capacity to transfer knowledge, but room for each architecture to keep its own strengths.

### 6.4 Hidden‑state‑aware adapter placement

From the hidden‑state variability paper:[^13]

- Compute variability metrics of hidden states for your downstream task; layers where hidden representations already cluster by label need less adaptation.[^13]
- Place cross‑model adapters and alignment objectives on layers with high task‑relevant variability for the teacher and under‑specialization for the student.[^13]

This is a cheap, empirical way to decide “where” in the stack to couple models.

***

If you want, I can next:

- Draft a concrete training recipe (losses, where to tap states) for aligning a RWKV and a Mamba model on a shared language task, or
- Compile a more formal mini‑bibliography with bibtex for the key alignment/transfer papers above.
<span style="display:none">[^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30][^31][^32][^33][^34][^35][^36]</span>

<div align="center">⁂</div>

[^1]: http://arxiv.org/pdf/2502.15130.pdf

[^2]: https://arxiv.org/abs/2402.12192

[^3]: http://arxiv.org/pdf/2405.18014.pdf

[^4]: https://ieeexplore.ieee.org/document/10944183/

[^5]: https://arxiv.org/html/2409.10385

[^6]: https://arxiv.org/pdf/2501.16384.pdf

[^7]: https://arxiv.org/abs/2506.02916

[^8]: https://arxiv.org/abs/2502.13145

[^9]: https://arxiv.org/abs/2501.16295

[^10]: https://arxiv.org/abs/2506.18939

[^11]: http://arxiv.org/pdf/2404.19394.pdf

[^12]: https://arxiv.org/abs/2401.09417

[^13]: https://aclanthology.org/2022.findings-emnlp.422.pdf

[^14]: https://ieeexplore.ieee.org/document/8110684/

[^15]: https://www.mdpi.com/2673-5172/6/4/173

[^16]: http://www.scitepress.org/DigitalLibrary/Link.aspx?doi=10.5220/0007239101270138

[^17]: http://link.springer.com/10.1007/978-3-319-46484-8_32

[^18]: http://ieeexplore.ieee.org/document/6639084/

[^19]: https://www.semanticscholar.org/paper/574e5da9311a1c3ed1727c28e154d348120d5e36

[^20]: https://ieeexplore.ieee.org/document/8823578/

[^21]: https://www.techscience.com/cmc/v71n2/45876

[^22]: https://www.semanticscholar.org/paper/31650d62f94daaa169510b6135bd3fc52e4dc753

[^23]: https://www.semanticscholar.org/paper/4f2eda8077dc7a69bb2b4e0a1a086cf054adb3f9

[^24]: https://arxiv.org/pdf/2407.04620.pdf

[^25]: https://arxiv.org/pdf/2007.07324.pdf

[^26]: http://arxiv.org/pdf/2405.06409.pdf

[^27]: http://arxiv.org/pdf/2501.12185.pdf

[^28]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6021386/

[^29]: http://arxiv.org/pdf/1509.03044.pdf

[^30]: http://arxiv.org/pdf/2308.08742.pdf

[^31]: https://arxiv.org/abs/2503.20999

[^32]: https://www.worldscientific.com/doi/10.1142/S0129156425403857

[^33]: https://ieeexplore.ieee.org/document/10832304/

[^34]: https://ieeexplore.ieee.org/document/11147760/

[^35]: https://arxiv.org/pdf/2410.06718.pdf

[^36]: https://arxiv.org/pdf/2401.04081.pdf

