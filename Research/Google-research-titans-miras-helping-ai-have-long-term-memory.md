Titans + MIRAS: Helping AI have long-term memory

The Transformer architecture revolutionized sequence modeling with its introduction of attention, a mechanism by which models look back at earlier inputs to prioritize relevant input data. However, computational cost increases drastically with sequence length, which limits the ability to scale Transformer-based models to extremely long contexts, such as those required for full-document understanding or genomic analysis.

The research community explored various approaches for solutions, such as efficient linear recurrent neural networks (RNNs) and state space models (SSMs) like Mamba-2. These models offer fast, linear scaling by compressing context into a fixed-size. However, this fixed-size compression cannot adequately capture the rich information in very long sequences.

In two new papers, Titans and MIRAS, we introduce an architecture and theoretical blueprint that combine the speed of RNNs with the accuracy of transformers. Titans is the specific architecture (the tool), and MIRAS is the theoretical framework (the blueprint) for generalizing these approaches. Together, they advance the concept of test-time memorization, the ability of an AI model to maintain long-term memory by incorporating more powerful “surprise” metrics (i.e., unexpected pieces of information) while the model is running and without dedicated offline retraining.

The MIRAS framework, as demonstrated by Titans, introduces a meaningful shift toward real-time adaptation. Instead of compressing information into a static state, this architecture actively learns and updates its own parameters as data streams in. This crucial mechanism enables the model to incorporate new, specific details into its core knowledge instantly.

Titans: Learning new context on the fly
An effective learning system requires distinct yet interconnected memory modules, mirroring the human brain's separation of short-term and long-term memory.

While attention mechanisms excel for precise, short-term memory, Titans introduces a novel neural long-term memory module, that, unlike the fixed-size vector or matrix memory in traditional RNNs, acts as a deep neural network (specifically, a multi-layer perceptron). This memory module provides significantly higher expressive power, allowing the model to summarize large volumes of information without losing important context. The model isn't simply taking notes; it's understanding and synthesizing the entire story.

Crucially, Titans doesn’t just passively store data. It actively learns how to recognize and retain important relationships and conceptual themes that connect tokens across the entire input. A key aspect of this ability is what we call the “surprise metric”. In human psychology, we know we quickly and easily forget routine, expected events but remember things that break the pattern — unexpected, surprising, or highly emotional events.

In the context of Titans, the "surprise metric" is the model detecting a large difference between what it currently remembers and what the new input is telling it.

Low surprise: If the new word is "cat" and the model's memory state already expects an animal word, the gradient (surprise) is low. It can safely skip memorizing the word "cat" in its permanent long-term state.
High surprise: If the model's memory state is summarizing a serious financial report, and the new input is a picture of a banana peel (the unexpected event), the gradient (surprise) will be very high. This signals that the new input is important or anomalous, and it must be prioritized for permanent storage in the long-term memory module.
The model uses this internal error signal (the gradient) as a mathematical equivalent of saying, "This is unexpected and important!" This allows the Titans architecture to selectively update its long-term memory only with the most novel and context-breaking information, keeping the overall process fast and efficient.

Titans refines this mechanism by incorporating two critical elements:

Momentum: The model considers both "momentary surprise" (the current input) and "past surprise" (the recent context flow). This ensures relevant subsequent information is also captured, even if those tokens are not individually surprising.
Forgetting (weight decay): To manage the finite capacity of the memory when dealing with extremely long sequences, Titans employ an adaptive weight decay mechanism. This acts as a forgetting gate, allowing the model to discard information that is no longer needed.
MIRAS: A unified view of sequence modeling
Every major breakthrough in sequence modeling — from modern transformers to the new, lightning-fast linear RNNs — is essentially the same thing under the hood: a highly complex associative memory module.

Accordingly, what makes MIRAS both unique and practical is the way it views AI modeling. Instead of seeing diverse architectures, it sees different methods of solving the same problem: efficiently combining new information with old memories without letting the essential concepts be forgotten.

MIRAS defines a sequence model through four key design choices:

Memory architecture: The structure that stores information (e.g., a vector, matrix, or a deep multi-layer perceptron, like in Titans).
Attentional bias: The internal learning objective the model optimizes that determines what it prioritizes.
Retention gate: The memory regularizer. MIRAS reinterprets "forgetting mechanisms" as specific forms of regularization that balance new learning against retaining past knowledge.
Memory algorithm: The optimization algorithm used to update the memory.
Transcending the mean squared error paradigm
Virtually all successful existing sequence models rely on mean squared error (MSE) or dot-product similarity for both their bias and retention. This reliance can make models sensitive to outliers and limit their expressive power.

MIRAS transcends this limitation by providing a generative framework to explore a more rich design space informed by the literature in optimization and statistics. This allows for the creation of novel architectures with non-Euclidean objectives and regularization.

Using MIRAS, we created three specific attention-free models:

YAAD: We designed this MIRAS variant to be less sensitive to major errors or "outliers" (like a single typo in a large document). It uses a gentler math penalty (Huber loss) for mistakes, so it doesn't overreact to one-off issues. This makes the model more robust when the input data is messy or inconsistent.
MONETA: This model explores the use of more complex and strict mathematical penalties (called generalized norms). It investigates whether using these more disciplined rules for both what the model attends to and what it forgets can lead to a more powerful and stable long-term memory system overall.
MEMORA: This model focuses on achieving the best possible memory stability by forcing its memory to act like a strict probability map. By using this constraint, it ensures that every time the memory state is updated, the changes are controlled and balanced. This guarantees a clean, stable process for integrating new information.Virtually all successful existing sequence models rely on mean squared error (MSE) or dot-product similarity for both their bias and retention. This reliance can make models sensitive to outliers and limit their expressive power.
Experiments and results
We rigorously compared Titans along with MIRAS variants (YAAD, MONETA, MEMORA) against leading architectures, including Transformer++, Mamba-2, and Gated DeltaNet. We further validated versatility by testing Titans on genomic modeling (DNA) and time-series forecasting, proving the architecture generalizes effectively beyond text.

Across both standard language modeling datasets (C4, WikiText) and zero-shot reasoning tasks (HellaSwag, PIQA), our models consistently demonstrated higher accuracy and perplexity (a measure of how surprised an LLM is when looking at a piece of text).

The power of deep memory
Ablation studies clearly show that the depth of the memory architecture is crucial. When comparing long-term memory modules of the same size but different depths, modules with deeper memories consistently achieve lower perplexity in language modeling. Furthermore, they exhibit better scaling properties, maintaining performance as the sequence length increases significantly.

Language modeling and efficiency
In language modeling and commonsense reasoning tasks, Titans architectures outperform state-of-the-art linear recurrent models (such as Mamba-2 and Gated DeltaNet) and Transformer++ baselines of comparable sizes. The novel MIRAS variants (MONETA, YAAD, MEMORA) also achieve improved performance compared to these baselines, validating the benefit of exploring robust, non-MSE optimization mechanisms. Importantly, these models maintain efficient, parallelizable training and fast linear inference speeds.

Extreme long-context recall
The most significant advantage of these new architectures is their ability to handle extremely long contexts. This is highlighted in the BABILong benchmark, a task requiring reasoning across facts distributed in extremely long documents. In this challenging setting, Titans outperforms all baselines, including extremely large models like GPT-4, despite having many fewer parameters. Titans further demonstrates the capability to scale effectively to context window sizes larger than 2 million tokens.

Conclusion
The introduction of Titans and the MIRAS framework marks a significant advancement in sequence modeling. By employing deep neural networks as memory modules that learn to memorize as data is coming in, these approaches overcome the limitations of fixed-size recurrent states. Furthermore, MIRAS provides a powerful theoretical unification, revealing the connection between online optimization, associative memory, and architectural design. By moving beyond the standard Euclidean paradigm, this research opens the door to a new generation of sequence models that combine the efficiency of RNNs with the expressive power needed for the era of long-context AI.

We introduce the Titans architecture and the MIRAS framework, which allow AI models to work much faster and handle massive contexts by updating their core memory while it's actively running.