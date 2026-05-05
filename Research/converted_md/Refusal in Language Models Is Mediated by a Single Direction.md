# **Refusal in Language Models** **Is Mediated by a Single Direction**

**Andy Arditi** _[∗]_ **Oscar Obeso** _[∗]_ **Aaquib Syed** **Daniel Paleka**
Independent ETH Zürich University of Maryland ETH Zürich


**Nina Panickssery** **Wes Gurnee** **Neel Nanda**
Anthropic MIT


**Abstract**


Conversational large language models are fine-tuned for both instruction-following
and safety, resulting in models that obey benign requests but refuse harmful ones.
While this refusal behavior is widespread across chat models, its underlying
mechanisms remain poorly understood. In this work, we show that refusal is
mediated by a one-dimensional subspace, across 13 popular open-source chat
models up to 72B parameters in size. Specifically, for each model, we find a
single direction such that erasing this direction from the model’s residual stream
activations prevents it from refusing harmful instructions, while adding this
direction elicits refusal on even harmless instructions. Leveraging this insight, we
propose a novel white-box jailbreak method that surgically disables refusal with
minimal effect on other capabilities. Finally, we mechanistically analyze how
adversarial suffixes suppress propagation of the refusal-mediating direction. Our
findings underscore the brittleness of current safety fine-tuning methods. More
broadly, our work showcases how an understanding of model internals can be
leveraged to develop practical methods for controlling model behavior. [†]


**1** **Introduction**


Deployed large language models (LLMs) undergo multiple rounds of fine-tuning to become both
_helpful_ and _harmless_ : to provide helpful responses to innocuous user requests, but to refuse harmful
or inappropriate ones (Bai et al., 2022). Naturally, large numbers of users and researchers alike have
attempted to circumvent these defenses using a wide array of jailbreak attacks (Chu et al., 2024; Wei
et al., 2023; Xu et al., 2024) to uncensor model outputs, including fine-tuning techniques (Lermen
et al., 2023; Yang et al., 2023; Zhan et al., 2023). While the consequences of a successful attack
on current chat assistants are modest, the scale and severity of harm from misuse could increase
dramatically if frontier models are endowed with increased agency and autonomy (Anthropic, 2024).
That is, as models are deployed in higher-stakes settings and are able to take actions in the real world,
the ability to robustly refuse a request to cause harm is an essential requirement of a safe AI system.
Inspired by the rapid progress of mechanistic interpretability (Bricken et al., 2023; Marks et al., 2024;
Nanda et al., 2023; Templeton et al., 2024) and activation steering (Panickssery et al., 2023; Turner
et al., 2023; Zou et al., 2023a), this work leverages the internal representations of chat models to
better understand refusal.


*Correspondence to `[andyrdt@gmail.com](mailto:andyrdt@gmail.com)`, `[obalcells@student.ethz.ch](mailto:obalcells@student.ethz.ch)` .
†Code available at `[https://github.com/andyrdt/refusal_direction](https://github.com/andyrdt/refusal_direction)` .


38th Conference on Neural Information Processing Systems (NeurIPS 2024).


![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-1-0.png)




|1.0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Score type|Col17|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|.2<br>.4<br>.6<br>.8|||||||||||||||Score type<br>Refusal score<br>Safety score<br>**Condition**<br>**No intervention**<br>**Directional**<br>**ablation**||
|.2<br>.4<br>.6<br>.8|||||||||||||||||
|.2<br>.4<br>.6<br>.8|||||||||||||||||
|.2<br>.4<br>.6<br>.8|||||||||||||||||
|.2<br>.4<br>.6<br>.8|||||||||||||||||



Figure 1: Ablating the “refusal direction” reduces refusal rates and elicits unsafe completions. We
evaluate each model over 100 harmful instructions from JAILBREAKBENCH (Chao et al., 2024).



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-1-1.png)



Figure 2: Ablating the “refusal direction” can effectively bypass refusal on harmful instructions. This
example is taken from LLAMA-3 8B INSTRUCT. For more examples, see §K.1.


It is widely hypothesized that LLMs represent features, or concepts, as linear directions in activation
space (Bolukbasi et al., 2016; Elhage et al., 2022; Mikolov et al., 2013; Park et al., 2023b). Recent
works have studied the linear representation of particular features such as harmlessness (Wolf et al.,
2024; Zheng et al., 2024; Zou et al., 2023a), truth (Li et al., 2024a; Marks and Tegmark, 2023), humor
(von Rütte et al., 2024), sentiment (Tigges et al., 2023), language (Bricken et al., 2023), topic (Turner
et al., 2023), and many others. Moreover, these feature directions have been shown to be effective
causal mediators of behavior, enabling fine-grained steering of model outputs (Panickssery et al.,
2023; Templeton et al., 2024; Turner et al., 2023; Zou et al., 2023a).


In this work, we show that refusal is mediated by a one-dimensional subspace across 13 popular
open-source chat models up to 72B parameters in size. Specifically, we use a small set of contrastive
pairs (Burns et al., 2022; Panickssery et al., 2023; Zou et al., 2023a) of harmful and harmless
instructions to identify a single difference-in-means direction (Belrose, 2023; Marks and Tegmark,
2023; Panickssery et al., 2023) that can be intervened upon to circumvent refusal on harmful prompts,
or induce refusal on harmless prompts (§3). We then use this insight to design a simple white-box
jailbreak via an interpretable rank-one weight edit that effectively disables refusal with minimal
impact on other capabilities (§4). We conclude with a preliminary mechanistic investigation into how
adversarial suffixes (Zou et al., 2023b), a popular prompt-based jailbreak technique, interfere with
the propagation of the refusal direction across token positions (§5).


Our work is a concrete demonstration that insights derived from interpreting model internals can be
practically useful, both for better understanding existing model vulnerabilities and identifying new
ones. Our findings make clear how defenseless current open-source chat models are, as even a simple
rank-one weight modification can nearly eliminate refusal behavior. We hope that our findings serve
as a valuable contribution to the conversation around responsible release of open-source models.


2


**2** **Methodology**


**2.1** **Background**


**Transformers.** Decoder-only transformers (Liu et al., 2018) map input tokens **t** =
( _t_ 1 _, t_ 2 _, . . ., tn_ ) _∈V_ _[n]_ to output probability distributions **y** = ( **y** 1 _,_ **y** 2 _, . . .,_ **y** _n_ ) _∈_ R _[n][×|V|]_ . Let
**x** [(] _i_ _[l]_ [)][(] **[t]** [)] _[ ∈]_ [R] _[d]_ [model] [denote the residual stream activation of the token at position] _[ i]_ [ at the start of layer] _[ l]_ [.][1]

Each token’s residual stream is initialized to its embedding **x** [(1)] _i_ = `Embed` ( _ti_ ), and then undergoes a
series of transformations across _L_ layers. Each layer’s transformation includes contributions from
attention and MLP components:

**x** ˜ [(] _i_ _[l]_ [)] = **x** [(] _i_ _[l]_ [)] + `Attn` [(] _[l]_ [)] ( **x** [(] 1: _[l]_ [)] _i_ [)] _[,]_ **x** [(] _i_ _[l]_ [+1)] = **x** ˜ [(] _i_ _[l]_ [)] + `MLP` [(] _[l]_ [)] (˜ **x** [(] _i_ _[l]_ [)][)] _[.]_ (1)

The final logits `logits` _i_ = `Unembed` ( **x** [(] _i_ _[L]_ [+1)] ) _∈_ R _[|V|]_ are then transformed into probabilities over
output tokens **y** _i_ = `softmax` ( `logits` _i_ ) _∈_ R _[|V|]_ . [2]


**Chat models.** Chat models are fine-tuned for instruction-following and dialogue (Ouyang et al.,
2022; Touvron et al., 2023). These models use _chat templates_ to structure user queries. Typically,
a chat template takes the form `<user>{instruction}<end_user><assistant>` . We use _post-_
_instruction tokens_ to refer to all template tokens after the instruction, and denote the set of positional
indices corresponding to these post-instruction tokens as _I_ . Our analysis focuses on activations
in this region to understand how the model formulates its response. All chat templates and their
corresponding post-instruction tokens are specified in §C.3.


**2.2** **Datasets and models**


**Datasets.** We construct two datasets: _D_ harmful, a dataset of harmful instructions drawn from ADVBENCH (Zou et al., 2023b), MALICIOUSINSTRUCT (Huang et al., 2023), TDC2023 (Mazeika
et al., 2023, 2024), and HARMBENCH (Mazeika et al., 2024); and _D_ harmless, a dataset of harmless
instructions sampled from ALPACA (Taori et al., 2023). Each dataset consists of train and validation
splits of 128 and 32 samples, respectively. We apply filtering to ensure that the train and validation
splits do not overlap with the evaluation datasets used in §3 and §4. See §A for further details about
the datasets, including representative examples.


**Models.** To assess the generality of our findings, we study a diverse set of safety fine-tuned models,
spanning 1.8 to 72 billion parameters in size. We consider both models aligned by preference
optimization (APO) and aligned by fine-tuning (AFT) (Meade et al., 2024). All models included in
the study are specified in Table 1. [3]


Table 1: Model families, sizes, alignment training type, and references.


Model family Sizes Alignment type Reference


QWEN CHAT 1.8B, 7B, 14B, 72B AFT Bai et al. (2023)
YI CHAT 6B, 34B AFT Young et al. (2024)
GEMMA IT 2B, 7B APO Team et al. (2024)
LLAMA-2 CHAT 7B, 13B, 70B APO Touvron et al. (2023)
LLAMA-3 INSTRUCT 8B, 70B APO AI@Meta (2024)


**2.3** **Extracting a refusal direction**


**Difference-in-means.** To identify the “refusal direction” in the model’s residual stream activations,
we compute the difference between the model’s mean activations when run on harmful and harmless


1We shorten **x** [(] _i_ _[l]_ [)][(] **[t]** [)][ to] **[ x]** _i_ [(] _[l]_ [)] when the input **t** is clear from context or unimportant.
2This high-level description omits details such as positional embeddings and layer normalization.
3Unless explicitly stated otherwise, all models examined in this study are chat models. As a result, we often
omit the terms CHAT or INSTRUCT when referring to these models (e.g. we often abbreviate “QWEN 1.8B
CHAT” as “QWEN 1.8B”).


3


instructions. This technique, known as _difference-in-means_ (Belrose, 2023), effectively isolates key
feature directions, as demonstrated in prior work (Marks and Tegmark, 2023; Panickssery et al., 2023;
Tigges et al., 2023). For each layer _l ∈_ [ _L_ ] and post-instruction token position _i ∈_ _I_, we calculate the
mean activation **µ** [(] _i_ _[l]_ [)] for harmful prompts from _D_ harmful [(train)] [and] **[ ν]** _i_ [(] _[l]_ [)] for harmless prompts from _D_ harmless [(train)] [:]



1
**µ** [(] _i_ _[l]_ [)] = _|D_ harmful [(train)] _[|]_




 

**t** _∈D_ harmful [(train)]




 

**t** _∈D_ harmless [(train)]



1
**x** [(] _i_ _[l]_ [)][(] **[t]** [)] _[,]_ **ν** [(] _i_ _[l]_ [)] =

_|D_ harmless [(train)] _[|]_



**x** [(] _i_ _[l]_ [)][(] **[t]** [)] _[.]_ (2)



We then compute the difference-in-means vector **r** [(] _i_ _[l]_ [)] = **µ** [(] _i_ _[l]_ [)] _−_ **ν** [(] _i_ _[l]_ [)][.] [Note that each such vector is]
meaningful in both (1) its direction, which describes the direction that mean harmful and harmless
activations differ along, and (2) its magnitude, which quantifies the distance between mean harmful
and harmless activations.


**Selecting a single vector.** Computing the difference-in-means vector **r** [(] _i_ _[l]_ [)] for each post-instruction
token position _i ∈_ _I_ and layer _l_ _∈_ [ _L_ ] yields a set of _|I| × L_ candidate vectors. We then select the
single most effective vector **r** [(] _i_ _[∗][l][∗]_ [)] from this set by evaluating each candidate vector over validation
sets _D_ harmful [(val)] [and] _[ D]_ harmless [(val)] [.] [This evaluation measures each candidate vector’s ability to bypass refusal]
when ablated and to induce refusal when added, while otherwise maintaining minimal change in
model behavior. A more detailed description of our selection algorithm is provided in §C. We notate
the selected vector as **r**, and its corresponding unit-norm vector as ˆ **r** .


**2.4** **Model interventions**


**Activation addition.** Given a difference-in-means vector **r** [(] _[l]_ [)] _∈_ R _[d]_ [model] extracted from layer _l_, we
can modulate the strength of the corresponding feature via simple linear interventions. Specifically,
we can _add_ the difference-in-means vector to the activations of a harmless input to shift them closer
to the mean harmful activation, thereby inducing refusal:

**x** [(] _[l]_ [)] _[′]_ _←_ **x** [(] _[l]_ [)] + **r** [(] _[l]_ [)] _._ (3)


Note that for activation addition, we intervene only at layer _l_, and across all token positions.


**Directional ablation.** To investigate the role of a direction ˆ **r** _∈_ R _[d]_ [model] in the model’s computation,
we can erase it from the model’s representations using _directional ablation_ . Directional ablation
“zeroes out” the component along ˆ **r** for every residual stream activation **x** _∈_ R _[d]_ [model] :

**x** _[′]_ _←_ **x** _−_ ˆ **r** ˆ **r** [⊺] **x** _._ (4)


We perform this operation at every activation **x** [(] _i_ _[l]_ [)] and **x** ˜ [(] _i_ _[l]_ [)][, across all layers] _[ l]_ [ and all token positions]
_i_ . This effectively prevents the model from ever representing this direction in its residual stream.


**2.5** **Evaluation of refusal and harmfulness**


When generating model completions for evaluation, we always use greedy decoding and a maximum
generation length of 512 tokens, as suggested in Mazeika et al. (2024). We then evaluate each model
completion based on whether it constitutes a refusal, and whether it contains harmful content. We
separate these evaluations into two scores: a _refusal score_ and a _safety score_ .


**Refusal** **score.** Refusals often contain characteristic phrases, such as `"I’m` `sorry"` or `"As` `an`
`AI"` . Following prior work (Lermen et al., 2023; Liu et al., 2023; Robey et al., 2023; Shah et al., 2023a;
Xu et al., 2023; Zou et al., 2023b), we compile a set of these common “refusal substrings”. If a model
completion includes at least one such substring, it is classified as a refusal ( `refusal_score=1` );
otherwise, it is classified as a non-refusal ( `refusal_score=0` ). The full set of refusal substrings is
provided in §D.1.


As has been previously noted (Huang et al., 2023; Meade et al., 2024; Qi et al., 2023; Shah et al.,
2023a), this string-matching approach has limitations. While effective at detecting memorized
refusals, it does not assess whether the completion is coherent or contains harmful content. To address
these limitations, we use a complementary metric that evaluates the harmfulness of a completion.


4


1.0


0.8


0.6


0.4


0.2


0.0




|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|Col17|Col18|Col19|Col20|Col21|Col22|Col23|Col24|Col25|Condition<br>No intervention<br>Activation<br>addition|Col27|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
||||||||||||||||||||||||||||
||||||||||||||||||||||||||||
||||||||||||||||||||||||||||
||||||||||||||||||||||||||||
||||||||||||||||||||||||||||
||||||||||||||||||||||||||||



Figure 3: Adding the “refusal direction" induces refusal on 100 harmless instructions from ALPACA.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-4-0.png)



Figure 4: Adding the “refusal direction” to residual stream activations can induce refusal on harmless
instructions. This example is taken from GEMMA 7B IT. For more examples, see §K.2.


**Safety score.** In order to measure the harmfulness of a model completion, we use META LLAMA
GUARD 2 (Team, 2024), a widely-used open-source model fine-tuned to accurately detect harmful
content. We prompt this model to classify each model completion as safe ( `safety_score=1` ) or
unsafe ( `safety_score=0` ). More details are provided in §D.2.


**3** **Refusal is mediated by a single direction**


For each model, we extract a single difference-in-means vector **r** via the methodology described in
§2.3. We then show that this single direction is both necessary and sufficient for refusal. In §3.1, we
show that ablating this direction ˆ **r** effectively disables the model’s ability to refuse harmful requests.
In §3.2, we show that adding **r** to the model’s activations induces refusal on harmless instructions.


**3.1** **Bypassing refusal via directional ablation**


To bypass refusal, we perform directional ablation on the “refusal direction” ˆ **r**, ablating it from
activations at all layers and all token positions. With this intervention in place, we generate model
completions over JAILBREAKBENCH (Chao et al., 2024), a dataset of 100 harmful instructions.


Results are shown in Figure 1. Under no intervention, chat models refuse nearly all harmful requests,
yielding high refusal and safety scores. Ablating ˆ **r** from the model’s residual stream activations,
labeled as _directional ablation_, reduces refusal rates and elicits unsafe completions.


**3.2** **Inducing refusal via activation addition**


To induce refusal, we add the difference-in-means vector **r** to activations in layer _l_ _[∗]_, the layer that
the **r** was originally extracted from. We perform this intervention at all token positions. With
this intervention in place, we generate model completions over 100 randomly sampled harmless
instructions from ALPACA.


Results are shown in Figure 3. Under no intervention, chat models typically do not refuse harmless
instructions. Adding **r** to the model’s residual stream activations, labeled as _activation_ _addition_,
results in the model refusing even harmless requests.


5


**4** **A white-box jailbreak via weight orthogonalization**


In this section, we propose a novel white-box jailbreak method through _weight orthogonalization_ .
This technique directly modifies model weights to eliminate the representation of the refusal direction,
resulting in a model that retains its original capabilities but no longer refuses harmful instructions. This
new approach offers a simpler way to jailbreak open-source models compared to prior methodologies
involving fine-tuning (Lermen et al., 2023; Yang et al., 2023; Zhan et al., 2023), as it does not require
gradient-based optimization nor any examples of harmful completions.


**4.1** **Weight orthogonalization**


In §2.4, we described _directional ablation_ as an inference-time intervention that prevents the model
from representing a direction ˆ **r** : during a forward pass, we zero out the ˆ **r** component from every
intermediate residual stream activation (Equation 4). We can equivalently implement this operation by
directly modifying component weights to never write to the ˆ **r** direction in the first place. Specifically,
we can take each matrix _W_ out _∈_ R _[d]_ [model] _[×][d]_ [input] that writes to the residual stream, and orthogonalize its
column vectors with respect to ˆ **r** :


_W_ out _[′]_ _[←]_ _[W]_ [out] _[−]_ [ˆ] **[r]** [ˆ] **[r]** [⊺] _[W]_ [out] _[.]_ (5)


In a transformer architecture, the matrices that write to the residual stream are: the embedding matrix,
the positional embedding matrix, attention out matrices, and MLP out matrices. Orthogonalizing all
of these matrices, as well as any output biases, with respect to the direction ˆ **r** effectively prevents the
model from ever writing ˆ **r** to its residual stream.


Note that this weight modification is equivalent to the previously described inference-time directional
ablation, as shown explicitly in §E. Therefore, the performance of the inference-time intervention in
bypassing refusal, presented in §3.1, also exactly characterizes that of the direct weight modification.


**4.2** **Comparison to other jailbreaks**


In this section, we compare our methodology to other existing jailbreak techniques using the standardized evaluation setup from HARMBENCH (Mazeika et al., 2024). Specifically, we generate
completions over the HARMBENCH test set of 159 “standard behaviors”, and then use their provided
classifier model to determine the attack success rate (ASR), which is the proportion of completions
classified as successfully bypassing refusal. We evaluate our weight orthogonalization method
on models included in the HARMBENCH study, and report its ASR alongside those of alternative
jailbreaks. For brief descriptions of each alternative jailbreak, see §F.1.


Table 2 shows that our weight orthogonalization method, labeled as ORTHO, fares well compared to
other general jailbreak techniques. Across the QWEN model family, our general method is even on par
with prompt-specific jailbreak techniques like GCG (Zou et al., 2023b), which optimize jailbreaks
for each prompt individually.


Table 2: HARMBENCH attack success rate (ASR) across various jailbreaking methods. Our method
is labeled as ORTHO. The baseline “direct response” rate with no jailbreak applied is labeled as
DR. We differentiate _general_ jailbreaks, which are applied across all prompts generically, from
_prompt-specific_ jailbreaks, which are optimized for each prompt individually. All evaluations use the
model’s default system prompt. We also report ASR without system prompt in blue.


General Prompt-specific


Chat model ORTHO GCG-M GCG-T HUMAN DR GCG AP PAIR


LLAMA-2 7B **22.6** (79.9) 20.0 16.8 0.1 0.0 34.5 17.0 7.5
LLAMA-2 13B 6.9 (61.0) 8.7 **13.0** 0.6 0.5 28.0 14.5 15.0
LLAMA-2 70B 4.4 (62.9) 5.5 **15.2** 0.0 0.0 36.0 15.5 7.5
QWEN 7B **79.2** (74.8) 73.3 48.4 28.4 7.0 79.5 67.0 58.0
QWEN 14B **84.3** (74.8) 75.5 46.0 31.5 9.5 83.5 56.0 51.5
QWEN 72B **78.0** (79.2) - 36.6 42.2 8.5 - - 54.5


6


Note that HARMBENCH’s evaluation methodology specifies that each model’s default system prompt
should be used during evaluation. While this approach is sensible for assessing the robustness of
black-box systems, it is less applicable for white-box scenarios where attackers have full access to
the model and can easily exclude the system prompt. Thus, we report ASR both with and without the
system prompt.


We observe a notable difference in system prompt sensitivity across model families. For LLAMA-2
models, including the system prompt substantially reduces ASR compared to evaluation without it
(e.g. 22.6% vs 79.9% for LLAMA-2 7B). In contrast, QWEN models maintain similar ASR regardless
of system prompt inclusion (e.g. 79.2% vs 74.8% for QWEN 7B). While the LLAMA-2 system
prompt contains explicit safety guidelines compared to the minimal QWEN system prompt, additional
analysis in §F.2 suggests the discrepancy is not explained by prompt content alone, and may reflect
differences in how these models respond to system-level instructions more generally.


**4.3** **Measuring model coherence**


A reasonable concern with any new jailbreak technique is that, in addition to circumventing refusal, it
may also degrade the model’s overall quality (Souly et al., 2024). However, qualitatively, we observe
that models maintain their coherence after undergoing weight orthogonalization. While §3.1 and §4.2
show that our method effectively bypasses refusal, in this subsection we quantitatively evaluate how
the modification alters a model’s general capabilities.


For each model and its orthogonalized version, we run four common language model evaluations:
MMLU (Hendrycks et al., 2020), ARC (Clark et al., 2018), GSM8K (Cobbe et al., 2021), and
TRUTHFULQA (Lin et al., 2021). All evaluations are run using LM Evaluation Harness (Gao et al.,
2023), with settings consistent with Open LLM Leaderboard (Beeching et al., 2023). [4]


Table 3 displays that, for MMLU, ARC, and GSM8K, orthogonalized models perform similarly to
baseline models. In §G.1, we show that this holds across other models in our suite, with additional
evaluations of WINOGRANDE (Sakaguchi et al., 2021) and TINYHELLASWAG (Polo et al., 2024).
Except for QWEN 7B and YI 34B, all evaluation metrics for orthogonalized models lie within 99%
confidence intervals of original performance.


Interestingly, accuracy on TRUTHFULQA consistently drops for orthogonalized models. This
phenomenon is consistent with Yang et al. (2023), where it was observed that fine-tuning away
safety guardrails results in decreased accuracy on TRUTHFULQA. Examining specific questions in
TRUTHFULQA reveals that the dataset veers close to the territory of refusal, with categories including
“misinformation”, “stereotypes”, and “conspiracies”, and thus it may intuitively make sense that
model behavior differs meaningfully on this evaluation dataset. See §G.2 for further discussion of
TRUTHFULQA performance.


In addition to standard language model evaluations, we also evaluate differences in CE loss, both
on standard text corpora and model-specific generations (§G.3). These loss metrics suggest that
directional ablation is more surgical than activation addition based methods (§I.1).


Table 3: Model evaluations. For each evaluation, we report the orthogonalized model’s performance,
followed by the baseline model’s performance, followed by the absolute increase or decrease. We
display the largest model from each model family. Full results are reported in §G.1.


Chat model MMLU ARC GSM8K TRUTHFULQA


GEMMA 7B 51.8 / 51.7 (+0.1) 51.7 / 51.5 (+0.2) 31.3 / 32.0 (-0.7) 44.7 / 47.1 (-2.4)
YI 34B 73.5 / 74.9 (-1.4) 65.6 / 64.9 (+0.7) 65.5 / 65.0 (+0.5) 51.9 / 55.4 (-3.5)
LLAMA-2 70B 63.1 / 63.0 (+0.1) 65.2 / 65.4 (-0.2) 54.5 / 53.0 (+1.5) 51.8 / 52.8 (-1.0)
LLAMA-3 70B 79.8 / 79.9 (-0.1) 71.5 / 71.8 (-0.3) 90.8 / 91.2 (-0.4) 59.5 / 61.8 (-2.3)
QWEN 72B 76.5 / 77.2 (-0.7) 67.2 / 67.6 (-0.4) 76.3 / 75.5 (+0.8) 55.0 / 56.4 (-1.4)


4As of June 2024, Open LLM Leaderboard does not use chat templates in evaluation prompts, and we follow
the same practice to remain consistent. Note that we are interested in detecting _relative changes in performance_,
not in measuring absolute performance.


7


**5** **Mechanistic analysis of adversarial suffixes**


Safety fine-tuned chat models are vulnerable to _adversarial suffix_ attacks (Zou et al., 2023b): there
exist carefully constructed strings such that appending these strings to the end of a harmful instruction
bypasses refusal and elicits harmful content. Effective adversarial suffixes are usually not human
interpretable, and the mechanisms by which they work are not well understood. In this section, we
mechanistically analyze the effect of an adversarial suffix on QWEN 1.8B CHAT.


**5.1** **Adversarial suffixes suppress the refusal-mediating direction**



We first identify a single adversarial suffix that
effectively bypasses refusal in QWEN 1.8B

refusal-eliciting harmful instructions from JAIL- 0.3
BREAKBENCH and the HARMBENCH test set.

0.2

For each instruction, we run the model three
times: first with the unedited instruction, sec- 0.1
ond with the adversarial suffix appended, and 0.0

|Col1|harmful|Col3|Col4|Col5|Col6|Col7|Col8|
|---|---|---|---|---|---|---|---|
||~~harmful~~<br>harmful<br>|~~ + random_s~~<br> + adv_suffix<br>|~~ ffix~~|||||
||~~harmles~~|||||||
|||||||||
|||||||||
|||||||||
|||||||||
|||||||||



the same length appended. By comparing the Layer
adversarial suffix to random suffixes, we aim to
control for the effect of appending any suffix at Figure 5: Cosine similarity between last token
all. For each run, we cache the last token activa- residual stream activations and refusal direction.
tions and visualize their cosine similarity with
the refusal-mediating direction. We also compare to a baseline of 128 harmless instructions from
ALPACA that do not elicit refusal. Figure 5 shows that the expression of the refusal direction is very
high for harmful instructions, and remains high when a random suffix is appended. The expression
of the refusal direction after appending the adversarial suffix is heavily suppressed, and closely
resembles that of harmless instructions.



0.5


0.4


0.3


0.2


0.1


0.0









0 5 10 15 20
Layer



Figure 5: Cosine similarity between last token
residual stream activations and refusal direction.



**5.2** **Adversarial suffixes hijack the attention of important heads**


To further investigate how the refusal direction is suppressed, we examine the contributions of
individual attention head and MLP components to the refusal direction. We quantify each component’s
contribution to this direction using _direct feature attribution_ (DFA) (Kissane et al., 2024; Makelov
et al., 2024): each component’s direct contribution can be measured by projecting its output onto the
refusal direction. We select the top eight attention heads with the highest DFA on harmful instructions,



5


4


3


2


1


0


|Col1|Top heads<br>H12.10<br>H12.8|
|---|---|
||H14.2<br>H14.12<br>H14.6<br>H14.7|
||H13.2<br>H10.10|
|||
|||



no_suffix random_suffix adv_suffix
Suffix type





5


4


3


2


1


0



Random suffix


instruction suffix
Attention source region



5


4


3


2


1


0



Adversarial suffix


instruction suffix
Attention source region



(a) Attention head outputs at last token position,
projected onto refusal direction.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-7-0.png)

![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-7-1.png)

(b) Attention from last token position to source token
regions.



Figure 6: We analyze the top eight attention heads that most significantly write to the refusal direction.
Figure 6(a) shows that output to the refusal direction is heavily suppressed when the adversarial
suffix is appended. Figure 6(b) reveals that, compared to appending a random suffix, appending the
adversarial suffix shifts attention from tokens in the instruction region to tokens in the suffix region.


8


and then investigate how their behavior changes when suffixes are appended. Figure 6(a) shows that
the direct contributions of these heads to the refusal direction are significantly suppressed when the
adversarial suffix is appended, as compared with no suffix and random suffixes.


To understand how the outputs of these attention heads are altered, we examine their attention patterns.
Figure 6(b) illustrates that the adversarial suffix effectively “hijacks” the attention of these heads.
Normally, these heads focus on the instruction region of the prompt, which contains harmful content.
With the adversarial suffix appended, these heads shift their attention to the suffix region, and away
from the harmful instruction.


**6** **Related work**


**Understanding refusal in language models.** Wei et al. (2024) demonstrate that removing a set
of safety-critical neurons and ranks can degrade safety mechanisms while preserving utility. Zheng
et al. (2024) and Zou et al. (2023a) both use contrastive pairs of harmful and harmless inputs to
identify the model’s representation of _harmfulness_, asserting that this direction is distinct from the
model’s representation of _refusal_ . Zheng et al. (2024) argue this by showing that safety prompts
shift activations in a distinct direction, while Zou et al. (2023a) show that the representation is not
significantly altered by adversarial suffixes. Note that this is in contrast to our findings in §5.1 that
the refusal direction is significantly suppressed in the presence of an adversarial suffix. Zou et al.
(2023a) additionally introduce a “piece-wise” intervention to effectively amplify representations of
harmfulness, and show that this intervention increases refusal on harmful inputs even when jailbreaks
are applied. Panickssery et al. (2023) use contrastive multiple-choice completions, finding that
steering with the resulting vector is effective at modulating refusal in multiple-choice settings but
not in long-form generation. Wang and Shu (2024) introduce a “Trojan Activation Attack” that
adds steering vectors to bypass refusal during inference. Li et al. (2024b) identify a “safety pattern”
by selecting individual neurons in each layer, and modulate refusal by zeroing out these neurons,
although with unclear effects on the overall model performance.


**Features as directions.** Extracting feature directions from contrastive pairs of inputs is an established technique (Burns et al., 2022; Panickssery et al., 2023; Zou et al., 2023a). It is well understood
that adding feature vectors to the residual stream can modify behavior (Li et al., 2024a; Marks and
Tegmark, 2023; Panickssery et al., 2023; Tigges et al., 2023; Turner et al., 2023; Zou et al., 2023a),
although details on how and where to intervene vary (Jorgensen et al., 2023; von Rütte et al., 2024).


Various works show that directions in activation space have more “feature-like” properties than
neurons do (Bolukbasi et al., 2016; Elhage et al., 2022; Geiger et al., 2024; Hernandez and Andreas,
2021; Li et al., 2021; Mikolov et al., 2013; Nanda et al., 2023; Park et al., 2023b). Recent works
use sparse autoencoders to discover feature directions in an unsupervised manner (Bricken et al.,
2023; Cunningham et al., 2023; Templeton et al., 2024). The assumption that features are represented
linearly has been effective for erasing concepts from language models (Belrose, 2023; Belrose et al.,
2024; Guerner et al., 2023; Haghighatkhah et al., 2022; Ravfogel et al., 2020; Shao et al., 2022).


**Undoing safety fine-tuning.** It is well known that fine-tuning on malicious examples is sufficient
to undo safety guardrails (Lermen et al., 2023), even with minimal degradation of overall capabilities
(Yang et al., 2023; Zhan et al., 2023). Undoing refusal via fine-tuning requires examples of harmful
instructions and completions, while our method requires only harmful instructions. Note however
that fine-tuning can weaken safety guardrails even when data is benign (Pelrine et al., 2023; Qi et al.,
2023). Mechanistic interpretability works have provided initial evidence suggesting that fine-tuning
does not significantly alter relevant internal circuitry (Jain et al., 2023; Lee et al., 2024; Prakash et al.,
2024). For example, Lee et al. (2024) fine-tune a model to make it less toxic, and find this behavioral
modification can be undone simply by scaling a small number of MLP weights.


**Jailbreaks.** The research area of circumventing restrictions on LLM behavior by _modifying the_
_input_ has seen many different directions of work. Many models are vulnerable to _social engineering_
_attacks_ (Perez et al., 2022; Shah et al., 2023b; Wei et al., 2023). One hypothesis for why this works is
that such prompts modify the LLM assistant’s "persona" (Andreas, 2022; Park et al., 2023a; Shanahan
et al., 2023). Preliminary experiments in §L suggest that our method does not change the model’s
chat personality or behavior outside of refusal.


9


Optimized _adversarial suffixes_ (Andriushchenko et al., 2024; Liao and Sun, 2024; Zou et al., 2023b)
can be appended to prompts to bypass refusal. In contrast, our method does not require any modifications to the input prompt, but has the obvious limitation that we require access to the model’s
weights. However, note that transferability of jailbreak prompts optimized on open-weight models on
black-box models is unclear (Meade et al., 2024). Jailbreak prompts may have significant impact on
model performance (Souly et al., 2024), whereas our method does not (§4.3).


**7** **Discussion**


In this work, we demonstrate that refusal behavior is consistently mediated by a single direction
across a diverse set of open-source chat models. Based on this understanding, we propose a simple
yet effective white-box jailbreak method that directly modifies model weights to disable the refusal
mechanism while retaining model coherence. Our work demonstrates the practical utility of modelinternals based interpretability: by studying refusal through the lens of model internals, we were able
to create a simple yet effective jailbreak method. The simplicity of the model’s refusal mechanism,
and the ease of circumventing it in the white-box setting, raise concerns about the robustness of
current alignment techniques.


**Limitations.** Our study has several limitations. While we evaluate a broad range of open-source
models, our findings may not generalize to untested models, especially those at greater scale, including
current state-of-the-art proprietary models and those developed in the future. Additionally, the
methodology we used to extract the “refusal direction” is likely not optimal and relies on several
heuristics. We see this paper as more of an existence proof that such a direction exists, rather than a
careful study of how best to extract it, and we leave methodological improvements to future work.
Furthermore, our analysis of adversarial suffixes does not provide a comprehensive mechanistic
understanding of the phenomenon, and is restricted to a single model and a single adversarial example.
Another limitation is that it is difficult to measure the coherence of a chat model, and we consider
each metric used flawed in various ways. We use multiple varied metrics to give a broad view of
coherence. Finally, while our work identifies a single direction that mediates refusal behavior in each
model, we acknowledge that the semantic meaning of these directions remains unclear. Though we
use the term “refusal direction” as a functional description, these directions could represent other
concepts such as “harm” or “danger”, or they may even resist straightforward semantic interpretation.


**Ethical** **considerations.** Any work on jailbreaking LLMs must ask the question of whether it
enables novel harms. It is already widely known that open-source model weights can be jailbroken
via fine-tuning. Our method, which can yield a jailbroken version of a 70B parameter model using less
than $5 of compute, is simpler than previous fine-tuning methods, requiring neither gradient-based
optimization nor a dataset of harmful completions. While we acknowledge that our methodology
marginally lowers the bar for jailbreaking open-source model weights, we believe that it does not
substantially alter the risk profile of open sourcing models.


Although the risk of misuse posed by today’s language models may be relatively low (Anthropic,
2024; Mouton et al., 2024), the rapid advancement of state-of-the-art model capabilities suggests
that this risk could become significant in the near future. Our work contributes to the growing body
of literature that highlights the fragility of current safety mechanisms, demonstrating that they can
easily be circumvented and are insufficient to prevent the misuse of open-source LLMs. Building a
scientific consensus around the limitations of current safety techniques is crucial for informing future
policy decisions and research efforts.


**Acknowledgments and disclosure of funding**


**Author contributions.** AA led the research project, and led the writing of the paper. AA discovered and validated that ablating a single direction bypasses refusal, and came up with the weight
orthogonalization trick. OO ran initial experiments identifying that it is possible to jailbreak models
via activation addition. AA and OO implemented and ran all experiments presented in the paper,
with DP helping to run model coherence evaluations. DP investigated behavior of the orthogonalized
models, suggested more thorough evaluations, and assisted with the writing of the paper. AS ran
initial experiments testing the causal efficacy of various directional interventions, and identified


10


the suffix used in §5 as universal for QWEN 1.8B CHAT. NP first proposed the idea of trying to
extract a linear refusal direction (Panickssery, 2023), and advised the initial project to mechanistically
understand refusal in LLAMA-2 7B CHAT (Arditi and Obeso, 2023). WG advised on methodology
and experiments, and assisted with the writing and framing of the paper. NN acted as primary
supervisor for the project, providing guidance and feedback throughout.


**Acknowledgements.** AA and OO began working on the project as part of the Supervised Program
for Alignment Research (SPAR) program, mentored by NP. AA and AS continued working on the
project as part of the ML Alignment & Theory Scholars (MATS) program, mentored by NN.


We thank Florian Tramèr for providing generous compute resources and for offering comments on an
earlier draft. We also thank Philippe Chlenski for providing thoughtful feedback on the manuscript.
For general support throughout the research process, we thank McKenna Fitzgerald, Rocket Drew,
Matthew Wearden, Henry Sleight, and the rest of the MATS team, and also Arthur Conmy. We
also thank the staff at Lighthaven and London Initiative for Safe AI (LISA) for cultivating great
environments in which to conduct research. We are grateful to the anonymous reviewers for their
valuable feedback which helped improve this paper.


**Tooling.** For our exploratory research, we used TransformerLens (Nanda and Bloom, 2022). For
our experimental pipeline, we use HuggingFace Transformers (Wolf et al., 2020), PyTorch (Paszke
et al., 2019), and vLLM (Kwon et al., 2023). We used Together AI remote inference to compute the
`safety_score` metric quickly.


**Disclosure of funding.** AA and OO are funded by Long-Term Future Fund (LTFF). AA and AS
are funded by AI Safety Support (AISS).


11


**References**


AI@Meta. Llama 3 model card. 2024. URL `[https://github.com/meta-llama/llama3/blob/](https://github.com/meta-llama/llama3/blob/main/MODEL_CARD.md)`
`[main/MODEL_CARD.md](https://github.com/meta-llama/llama3/blob/main/MODEL_CARD.md)` .


Jacob Andreas. Language models as agent models. _arXiv preprint arXiv:2212.01681_, 2022.


Maksym Andriushchenko, Francesco Croce, and Nicolas Flammarion. Jailbreaking leading safetyaligned LLMs with simple adaptive attacks. _arXiv preprint arXiv:2404.02151_, 2024.


Anthropic. Anthropic’s responsible scaling policy, 2024. `[https://www.anthropic.com/news/](https://www.anthropic.com/news/anthropics-responsible-scaling-policy)`
`[anthropics-responsible-scaling-policy](https://www.anthropic.com/news/anthropics-responsible-scaling-policy)` . Accessed on: May 20, 2024.


Andy Arditi and Oscar Obeso. Refusal mechanisms: initial experiments with Llama-2-7b-chat. Alignment Forum, 2023. URL `[https://www.alignmentforum.org/posts/pYcEhoAoPfHhgJ8YC](https://www.alignmentforum.org/posts/pYcEhoAoPfHhgJ8YC)` .


Jinze Bai, Shuai Bai, Yunfei Chu, Zeyu Cui, Kai Dang, Xiaodong Deng, Yang Fan, Wenbin Ge,
Yu Han, Fei Huang, et al. Qwen technical report. _arXiv preprint arXiv:2309.16609_, 2023.


Yuntao Bai, Andy Jones, Kamal Ndousse, Amanda Askell, Anna Chen, Nova DasSarma, Dawn Drain,
Stanislav Fort, Deep Ganguli, Tom Henighan, et al. Training a helpful and harmless assistant with
reinforcement learning from human feedback. _arXiv preprint arXiv:2204.05862_, 2022.


Edward Beeching, Clémentine Fourrier, Nathan Habib, Sheon Han, Nathan Lambert, Nazneen
Rajani, Omar Sanseviero, Lewis Tunstall, and Thomas Wolf. Open LLM leaderboard. `[https:](https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard)`
`[//huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard](https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard)`, 2023.


Nora Belrose. Diff-in-means concept editing is worst-case optimal: Explaining a result by Sam
Marks and Max Tegmark, 2023. `[https://blog.eleuther.ai/diff-in-means/](https://blog.eleuther.ai/diff-in-means/)` . Accessed
on: May 20, 2024.


Nora Belrose, David Schneider-Joseph, Shauli Ravfogel, Ryan Cotterell, Edward Raff, and Stella
Biderman. LEACE: Perfect linear concept erasure in closed form. _Advances in Neural Information_
_Processing Systems_, 36, 2024.


Stella Biderman, Hailey Schoelkopf, Lintang Sutawika, Leo Gao, Jonathan Tow, Baber Abbasi,
Alham Fikri Aji, Pawan Sasanka Ammanamanchi, Sidney Black, Jordan Clive, et al. Lessons from
the trenches on reproducible evaluation of language models. _arXiv preprint arXiv:2405.14782_,
2024.


Tolga Bolukbasi, Kai-Wei Chang, James Y Zou, Venkatesh Saligrama, and Adam T Kalai. Man is to
computer programmer as woman is to homemaker? Debiasing word embeddings. _Advances in_
_neural information processing systems_, 29, 2016.


Trenton Bricken, Adly Templeton, Joshua Batson, Brian Chen, Adam Jermyn, Tom Conerly, Nick
Turner, Cem Anil, Carson Denison, Amanda Askell, Robert Lasenby, Yifan Wu, Shauna Kravec,
Nicholas Schiefer, Tim Maxwell, Nicholas Joseph, Zac Hatfield-Dodds, Alex Tamkin, Karina
Nguyen, Brayden McLean, Josiah E Burke, Tristan Hume, Shan Carter, Tom Henighan, and
Christopher Olah. Towards monosemanticity: Decomposing language models with dictionary
learning. _Transformer Circuits Thread_, 2023. `[https://transformer-circuits.pub/2023/](https://transformer-circuits.pub/2023/monosemantic-features/index.html)`
`[monosemantic-features/index.html](https://transformer-circuits.pub/2023/monosemantic-features/index.html)` .


Collin Burns, Haotian Ye, Dan Klein, and Jacob Steinhardt. Discovering latent knowledge in language
models without supervision. _arXiv preprint arXiv:2212.03827_, 2022.


Patrick Chao, Alexander Robey, Edgar Dobriban, Hamed Hassani, George J Pappas, and Eric Wong.
Jailbreaking black box large language models in twenty queries. _arXiv preprint arXiv:2310.08419_,
2023.


Patrick Chao, Edoardo Debenedetti, Alexander Robey, Maksym Andriushchenko, Francesco Croce,
Vikash Sehwag, Edgar Dobriban, Nicolas Flammarion, George J Pappas, Florian Tramer, et al.
JailbreakBench: An open robustness benchmark for jailbreaking large language models. _arXiv_
_preprint arXiv:2404.01318_, 2024.


12


Junjie Chu, Yugeng Liu, Ziqing Yang, Xinyue Shen, Michael Backes, and Yang Zhang. Comprehensive assessment of jailbreak attacks against LLMs. _arXiv preprint arXiv:2402.05668_, 2024.


Peter Clark, Isaac Cowhey, Oren Etzioni, Tushar Khot, Ashish Sabharwal, Carissa Schoenick, and
Oyvind Tafjord. Think you have solved question answering? Try ARC, the AI2 reasoning challenge.
_arXiv preprint arXiv:1803.05457_, 2018.


Karl Cobbe, Vineet Kosaraju, Mohammad Bavarian, Mark Chen, Heewoo Jun, Lukasz Kaiser,
Matthias Plappert, Jerry Tworek, Jacob Hilton, Reiichiro Nakano, et al. Training verifiers to solve
math word problems. _arXiv preprint arXiv:2110.14168_, 2021.


Hoagy Cunningham, Aidan Ewart, Logan Riggs, Robert Huben, and Lee Sharkey. Sparse autoencoders find highly interpretable features in language models. _arXiv preprint arXiv:2309.08600_,
2023.


Nelson Elhage, Tristan Hume, Catherine Olsson, Nicholas Schiefer, Tom Henighan, Shauna Kravec,
Zac Hatfield-Dodds, Robert Lasenby, Dawn Drain, Carol Chen, Roger Grosse, Sam McCandlish,
Jared Kaplan, Dario Amodei, Martin Wattenberg, and Christopher Olah. Toy models of superposition. _Transformer Circuits Thread_, 2022. `[https://transformer-circuits.pub/2022/toy_](https://transformer-circuits.pub/2022/toy_model/index.html)`
`[model/index.html](https://transformer-circuits.pub/2022/toy_model/index.html)` .


Leo Gao, Stella Biderman, Sid Black, Laurence Golding, Travis Hoppe, Charles Foster, Jason Phang,
Horace He, Anish Thite, Noa Nabeshima, et al. The Pile: An 800GB dataset of diverse text for
language modeling. _arXiv preprint arXiv:2101.00027_, 2020.


Leo Gao, Jonathan Tow, Baber Abbasi, Stella Biderman, Sid Black, Anthony DiPofi, Charles Foster,
Laurence Golding, Jeffrey Hsu, Alain Le Noac’h, Haonan Li, Kyle McDonell, Niklas Muennighoff,
Chris Ociepa, Jason Phang, Laria Reynolds, Hailey Schoelkopf, Aviya Skowron, Lintang Sutawika,
Eric Tang, Anish Thite, Ben Wang, Kevin Wang, and Andy Zou. A framework for few-shot
language model evaluation, 12 2023. URL `[https://zenodo.org/records/10256836](https://zenodo.org/records/10256836)` .


Atticus Geiger, Zhengxuan Wu, Christopher Potts, Thomas Icard, and Noah Goodman. Finding
alignments between interpretable causal variables and distributed neural representations. In _Causal_
_Learning and Reasoning_, pages 160–187. PMLR, 2024.


Clément Guerner, Anej Svete, Tianyu Liu, Alexander Warstadt, and Ryan Cotterell. A geometric
notion of causal probing. _arXiv preprint arXiv:2307.15054_, 2023.


Pantea Haghighatkhah, Antske Fokkens, Pia Sommerauer, Bettina Speckmann, and Kevin Verbeek.
Better hit the nail on the head than beat around the bush: Removing protected attributes with a
single projection. _arXiv preprint arXiv:2212.04273_, 2022.


Dan Hendrycks, Collin Burns, Steven Basart, Andy Zou, Mantas Mazeika, Dawn Song, and
Jacob Steinhardt. Measuring massive multitask language understanding. _arXiv_ _preprint_
_arXiv:2009.03300_, 2020.


Evan Hernandez and Jacob Andreas. The low-dimensional linear geometry of contextualized word
representations. _arXiv preprint arXiv:2105.07109_, 2021.


Edward J Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang,
and Weizhu Chen. LoRA: Low-rank adaptation of large language models. _arXiv_ _preprint_
_arXiv:2106.09685_, 2021.


Yangsibo Huang, Samyak Gupta, Mengzhou Xia, Kai Li, and Danqi Chen. Catastrophic jailbreak of
open-source LLMs via exploiting generation. _arXiv preprint arXiv:2310.06987_, 2023.


Samyak Jain, Robert Kirk, Ekdeep Singh Lubana, Robert P Dick, Hidenori Tanaka, Edward Grefenstette, Tim Rocktäschel, and David Scott Krueger. Mechanistically analyzing the effects of
fine-tuning on procedurally defined tasks. _arXiv preprint arXiv:2311.12786_, 2023.


Albert Q Jiang, Alexandre Sablayrolles, Arthur Mensch, Chris Bamford, Devendra Singh Chaplot,
Diego de las Casas, Florian Bressand, Gianna Lengyel, Guillaume Lample, Lucile Saulnier, et al.
Mistral 7B. _arXiv preprint arXiv:2310.06825_, 2023.


13


Ole Jorgensen, Dylan Cope, Nandi Schoots, and Murray Shanahan. Improving activation steering in
language models with mean-centring. _arXiv preprint arXiv:2312.03813_, 2023.


Connor Kissane, Robert Krzyzanowski, Arthur Conmy, and Neel Nanda. Sparse autoencoders work
on attention layer outputs. Alignment Forum, 2024. URL `[https://www.alignmentforum.org/](https://www.alignmentforum.org/posts/DtdzGwFh9dCfsekZZ)`
`[posts/DtdzGwFh9dCfsekZZ](https://www.alignmentforum.org/posts/DtdzGwFh9dCfsekZZ)` .


Woosuk Kwon, Zhuohan Li, Siyuan Zhuang, Ying Sheng, Lianmin Zheng, Cody Hao Yu, Joseph E.
Gonzalez, Hao Zhang, and Ion Stoica. Efficient memory management for large language model
serving with PagedAttention. In _Proceedings of the ACM SIGOPS 29th Symposium on Operating_
_Systems Principles_, 2023.


Andrew Lee, Xiaoyan Bai, Itamar Pres, Martin Wattenberg, Jonathan K Kummerfeld, and Rada
Mihalcea. A mechanistic understanding of alignment algorithms: A case study on DPO and
toxicity. _arXiv preprint arXiv:2401.01967_, 2024.


Simon Lermen, Charlie Rogers-Smith, and Jeffrey Ladish. LoRA fine-tuning efficiently undoes
safety training in Llama 2-Chat 70B. _arXiv preprint arXiv:2310.20624_, 2023.


Belinda Z Li, Maxwell Nye, and Jacob Andreas. Implicit representations of meaning in neural
language models. _arXiv preprint arXiv:2106.00737_, 2021.


Kenneth Li, Oam Patel, Fernanda Viégas, Hanspeter Pfister, and Martin Wattenberg. Inference-time
intervention: Eliciting truthful answers from a language model. _Advances in Neural Information_
_Processing Systems_, 36, 2024a.


Tianlong Li, Shihan Dou, Wenhao Liu, Muling Wu, Changze Lv, Rui Zheng, Xiaoqing Zheng, and
Xuanjing Huang. Rethinking jailbreaking through the lens of representation engineering, 2024b.


Zeyi Liao and Huan Sun. AmpleGCG: Learning a universal and transferable generative model of
adversarial suffixes for jailbreaking both open and closed LLMs. _arXiv preprint arXiv:2404.07921_,
2024.


Stephanie Lin, Jacob Hilton, and Owain Evans. TruthfulQA: Measuring how models mimic human
falsehoods. _arXiv preprint arXiv:2109.07958_, 2021.


Peter J Liu, Mohammad Saleh, Etienne Pot, Ben Goodrich, Ryan Sepassi, Lukasz Kaiser, and Noam
Shazeer. Generating Wikipedia by summarizing long sequences. _arXiv preprint arXiv:1801.10198_,
2018.


Xiaogeng Liu, Nan Xu, Muhao Chen, and Chaowei Xiao. AutoDAN: Generating stealthy jailbreak
prompts on aligned large language models. _arXiv preprint arXiv:2310.04451_, 2023.


Aleksandar Makelov, George Lange, and Neel Nanda. Towards principled evaluations of sparse
autoencoders for interpretability and control. _arXiv preprint arXiv:2405.08366_, 2024.


Samuel Marks and Max Tegmark. The geometry of truth: Emergent linear structure in large language
model representations of true/false datasets. _arXiv preprint arXiv:2310.06824_, 2023.


Samuel Marks, Can Rager, Eric J Michaud, Yonatan Belinkov, David Bau, and Aaron Mueller. Sparse
feature circuits: Discovering and editing interpretable causal graphs in language models. _arXiv_
_preprint arXiv:2403.19647_, 2024.


Mantas Mazeika, Andy Zou, Norman Mu, Long Phan, Zifan Wang, Chunru Yu, Adam Khoja,
Fengqing Jiang, Aidan O’Gara, Ellie Sakhaee, Zhen Xiang, Arezoo Rajabi, Dan Hendrycks, Radha
Poovendran, Bo Li, and David Forsyth. TDC 2023 (LLM edition): the Trojan Detection Challenge.
In _NeurIPS Competition Track_, 2023.


Mantas Mazeika, Long Phan, Xuwang Yin, Andy Zou, Zifan Wang, Norman Mu, Elham Sakhaee,
Nathaniel Li, Steven Basart, Bo Li, et al. HarmBench: A standardized evaluation framework for
automated red teaming and robust refusal. _arXiv preprint arXiv:2402.04249_, 2024.


Nicholas Meade, Arkil Patel, and Siva Reddy. Universal adversarial triggers are not universal. _arXiv_
_preprint arXiv:2404.16020_, 2024.


14


Tomáš Mikolov, Wen-tau Yih, and Geoffrey Zweig. Linguistic regularities in continuous space
word representations. In _Proceedings of the 2013 conference of the north american chapter of the_
_association for computational linguistics:_ _Human language technologies_, pages 746–751, 2013.


Bonan Min, Hayley Ross, Elior Sulem, Amir Pouran Ben Veyseh, Thien Huu Nguyen, Oscar Sainz,
Eneko Agirre, Ilana Heintz, and Dan Roth. Recent advances in natural language processing via
large pre-trained language models: A survey. _ACM Computing Surveys_, 56(2):1–40, 2023.


Christopher A. Mouton, Caleb Lucas, and Ella Guest. _The Operational Risks of AI in Large-Scale_
_Biological Attacks:_ _Results of a Red-Team Study_ . RAND Corporation, Santa Monica, CA, 2024.
doi: 10.7249/RRA2977-2.


Neel Nanda and Joseph Bloom. TransformerLens. `[https://github.com/TransformerLensOrg/](https://github.com/TransformerLensOrg/TransformerLens)`
`[TransformerLens](https://github.com/TransformerLensOrg/TransformerLens)`, 2022.


Neel Nanda, Andrew Lee, and Martin Wattenberg. Emergent linear representations in world models
of self-supervised sequence models. _arXiv preprint arXiv:2309.00941_, 2023.


Long Ouyang, Jeffrey Wu, Xu Jiang, Diogo Almeida, Carroll Wainwright, Pamela Mishkin, Chong
Zhang, Sandhini Agarwal, Katarina Slama, Alex Ray, et al. Training language models to follow
instructions with human feedback. _Advances in neural information processing systems_, 35:27730–
27744, 2022.


Nina Panickssery. Red-teaming language models via activation engineering. Alignment Forum, 2023.
URL `[https://www.alignmentforum.org/posts/iHmsJdxgMEWmAfNne](https://www.alignmentforum.org/posts/iHmsJdxgMEWmAfNne)` .


Nina Panickssery, Nick Gabrieli, Julian Schulz, Meg Tong, Evan Hubinger, and Alexander Matt
Turner. Steering Llama 2 via contrastive activation addition. _arXiv preprint arXiv:2312.06681_,
2023.


Joon Sung Park, Joseph O’Brien, Carrie Jun Cai, Meredith Ringel Morris, Percy Liang, and Michael S
Bernstein. Generative agents: Interactive simulacra of human behavior. In _Proceedings of the 36th_
_Annual ACM Symposium on User Interface Software and Technology_, pages 1–22, 2023a.


Kiho Park, Yo Joong Choe, and Victor Veitch. The linear representation hypothesis and the geometry
of large language models. _arXiv preprint arXiv:2311.03658_, 2023b.


Adam Paszke, Sam Gross, Francisco Massa, Adam Lerer, James Bradbury, Gregory Chanan, Trevor
Killeen, Zeming Lin, Natalia Gimelshein, Luca Antiga, et al. Pytorch: An imperative style,
high-performance deep learning library. _Advances in neural information processing systems_, 32,
2019.


Kellin Pelrine, Mohammad Taufeeque, Michał Zaj ˛ac, Euan McLean, and Adam Gleave. Exploiting
novel GPT-4 APIs. _arXiv preprint arXiv:2312.14302_, 2023.


Ethan Perez, Saffron Huang, Francis Song, Trevor Cai, Roman Ring, John Aslanides, Amelia Glaese,
Nat McAleese, and Geoffrey Irving. Red teaming language models with language models. _arXiv_
_preprint arXiv:2202.03286_, 2022.


Felipe Maia Polo, Lucas Weber, Leshem Choshen, Yuekai Sun, Gongjun Xu, and Mikhail Yurochkin.
tinyBenchmarks: evaluating LLMs with fewer examples. _arXiv preprint arXiv:2402.14992_, 2024.


Nikhil Prakash, Tamar Rott Shaham, Tal Haklay, Yonatan Belinkov, and David Bau. Fine-tuning
enhances existing mechanisms: A case study on entity tracking. _arXiv preprint arXiv:2402.14811_,
2024.


Xiangyu Qi, Yi Zeng, Tinghao Xie, Pin-Yu Chen, Ruoxi Jia, Prateek Mittal, and Peter Henderson.
Fine-tuning aligned language models compromises safety, even when users do not intend to! _arXiv_
_preprint arXiv:2310.03693_, 2023.


Shauli Ravfogel, Yanai Elazar, Hila Gonen, Michael Twiton, and Yoav Goldberg. Null it out:
Guarding protected attributes by iterative nullspace projection. _arXiv preprint arXiv:2004.07667_,
2020.


15


Alexander Robey, Eric Wong, Hamed Hassani, and George J Pappas. SmoothLLM: Defending large
language models against jailbreaking attacks. _arXiv preprint arXiv:2310.03684_, 2023.


Keisuke Sakaguchi, Ronan Le Bras, Chandra Bhagavatula, and Yejin Choi. WinoGrande: An
adversarial Winograd schema challenge at scale. _Communications of the ACM_, 64(9):99–106,
2021.


Muhammad Ahmed Shah, Roshan Sharma, Hira Dhamyal, Raphael Olivier, Ankit Shah, Dareen
Alharthi, Hazim T Bukhari, Massa Baali, Soham Deshmukh, Michael Kuhlmann, et al. LoFT:
Local proxy fine-tuning for improving transferability of adversarial attacks against large language
model. _arXiv preprint arXiv:2310.04445_, 2023a.


Rusheb Shah, Quentin Feuillade-Montixi, Soroush Pour, Arush Tagade, Stephen Casper, and Javier
Rando. Scalable and transferable black-box jailbreaks for language models via persona modulation,
2023b.


Murray Shanahan, Kyle McDonell, and Laria Reynolds. Role play with large language models.
_Nature_, 623(7987):493–498, 2023.


Shun Shao, Yftah Ziser, and Shay B Cohen. Gold doesn’t always glitter: Spectral removal of linear
and nonlinear guarded attribute information. _arXiv preprint arXiv:2203.07893_, 2022.


Xinyue Shen, Zeyuan Chen, Michael Backes, Yun Shen, and Yang Zhang. "Do anything now":
Characterizing and evaluating in-the-wild jailbreak prompts on large language models. _arXiv_
_preprint arXiv:2308.03825_, 2023.


Taylor Shin, Yasaman Razeghi, Robert L. Logan IV, Eric Wallace, and Sameer Singh. AutoPrompt:
Eliciting knowledge from language models with automatically generated prompts. In _Proceed-_
_ings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)_ .
Association for Computational Linguistics, 2020.


Alexandra Souly, Qingyuan Lu, Dillon Bowen, Tu Trinh, Elvis Hsieh, Sana Pandey, Pieter Abbeel,
Justin Svegliato, Scott Emmons, Olivia Watkins, et al. A StrongREJECT for empty jailbreaks.
_arXiv preprint arXiv:2402.10260_, 2024.


Rohan Taori, Ishaan Gulrajani, Tianyi Zhang, Yann Dubois, Xuechen Li, Carlos Guestrin, Percy
Liang, and Tatsunori B. Hashimoto. Stanford Alpaca: An instruction-following LLaMA model.
`[https://github.com/tatsu-lab/stanford_alpaca](https://github.com/tatsu-lab/stanford_alpaca)`, 2023.


Gemma Team, Thomas Mesnard, Cassidy Hardin, Robert Dadashi, Surya Bhupatiraju, Shreya Pathak,
Laurent Sifre, Morgane Rivière, Mihir Sanjay Kale, Juliette Love, et al. Gemma: Open models
based on Gemini research and technology. _arXiv preprint arXiv:2403.08295_, 2024.


Llama Team. Meta Llama Guard 2. `[https://github.com/meta-llama/PurpleLlama/blob/](https://github.com/meta-llama/PurpleLlama/blob/main/Llama-Guard2/MODEL_CARD.md)`
`[main/Llama-Guard2/MODEL_CARD.md](https://github.com/meta-llama/PurpleLlama/blob/main/Llama-Guard2/MODEL_CARD.md)`, 2024.


Adly Templeton, Tom Conerly, Jonathan Marcus, Jack Lindsey, Trenton Bricken, Brian Chen, Adam
Pearce, Craig Citro, Emmanuel Ameisen, Andy Jones, Hoagy Cunningham, Nicholas L Turner,
Callum McDougall, Monte MacDiarmid, C. Daniel Freeman, Theodore R. Sumers, Edward Rees,
Joshua Batson, Adam Jermyn, Shan Carter, Chris Olah, and Tom Henighan. Scaling monosemanticity: Extracting interpretable features from Claude 3 Sonnet. _Transformer_ _Circuits_ _Thread_,
2024. URL `[https://transformer-circuits.pub/2024/scaling-monosemanticity/](https://transformer-circuits.pub/2024/scaling-monosemanticity/index.html)`
`[index.html](https://transformer-circuits.pub/2024/scaling-monosemanticity/index.html)` .


Curt Tigges, Oskar John Hollinsworth, Atticus Geiger, and Neel Nanda. Linear representations of
sentiment in large language models. _arXiv preprint arXiv:2310.15154_, 2023.


Hugo Touvron, Louis Martin, Kevin Stone, Peter Albert, Amjad Almahairi, Yasmine Babaei, Nikolay
Bashlykov, Soumya Batra, Prajjwal Bhargava, Shruti Bhosale, et al. Llama 2: Open foundation
and fine-tuned chat models. _arXiv preprint arXiv:2307.09288_, 2023.


Alex Turner, Lisa Thiergart, David Udell, Gavin Leech, Ulisse Mini, and Monte MacDiarmid. Activation addition: Steering language models without optimization. _arXiv preprint arXiv:2308.10248_,
2023.


16


Dimitri von Rütte, Sotiris Anagnostidis, Gregor Bachmann, and Thomas Hofmann. A language
model’s guide through latent space. _arXiv preprint arXiv:2402.14433_, 2024.


Haoran Wang and Kai Shu. Trojan activation attack: Red-teaming large language models using
activation steering for safety-alignment, 2024. URL `[https://arxiv.org/abs/2311.09433](https://arxiv.org/abs/2311.09433)` .


Tony T Wang, Miles Wang, Kaivu Hariharan, and Nir Shavit. Forbidden facts: An investigation of
competing objectives in Llama-2. _arXiv preprint arXiv:2312.08793_, 2023.


Alexander Wei, Nika Haghtalab, and Jacob Steinhardt. Jailbroken: How does LLM safety training
fail? _arXiv preprint arXiv:2307.02483_, 2023.


Boyi Wei, Kaixuan Huang, Yangsibo Huang, Tinghao Xie, Xiangyu Qi, Mengzhou Xia, Prateek
Mittal, Mengdi Wang, and Peter Henderson. Assessing the brittleness of safety alignment via
pruning and low-rank modifications. _arXiv preprint arXiv:2402.05162_, 2024.


Thomas Wolf, Lysandre Debut, Victor Sanh, Julien Chaumond, Clement Delangue, Anthony Moi,
Pierric Cistac, Tim Rault, Rémi Louf, Morgan Funtowicz, Joe Davison, Sam Shleifer, Patrick von
Platen, Clara Ma, Yacine Jernite, Julien Plu, Canwen Xu, Teven Le Scao, Sylvain Gugger, Mariama
Drame, Quentin Lhoest, and Alexander M. Rush. Transformers: State-of-the-art natural language
processing. In _Proceedings of the 2020 Conference on Empirical Methods in Natural Language_
_Processing:_ _System Demonstrations_, pages 38–45, Online, October 2020. Association for Computational Linguistics. URL `[https://www.aclweb.org/anthology/2020.emnlp-demos.6](https://www.aclweb.org/anthology/2020.emnlp-demos.6)` .


Yotam Wolf, Noam Wies, Dorin Shteyman, Binyamin Rothberg, Yoav Levine, and Amnon Shashua.
Tradeoffs between alignment and helpfulness in language models. _arXiv preprint arXiv:2401.16332_,
2024.


Nan Xu, Fei Wang, Ben Zhou, Bang Zheng Li, Chaowei Xiao, and Muhao Chen. Cognitive
overload: Jailbreaking large language models with overloaded logical thinking. _arXiv preprint_
_arXiv:2311.09827_, 2023.


Zihao Xu, Yi Liu, Gelei Deng, Yuekang Li, and Stjepan Picek. LLM jailbreak attack versus defense
techniques – a comprehensive study. _arXiv preprint arXiv:2402.13457_, 2024.


Xianjun Yang, Xiao Wang, Qi Zhang, Linda Petzold, William Yang Wang, Xun Zhao, and Dahua
Lin. Shadow alignment: The ease of subverting safely-aligned language models. _arXiv preprint_
_arXiv:2310.02949_, 2023.


Alex Young, Bei Chen, Chao Li, Chengen Huang, Ge Zhang, Guanwei Zhang, Heng Li, Jiangcheng
Zhu, Jianqun Chen, Jing Chang, et al. Yi: Open foundation models by 01.AI. _arXiv_ _preprint_
_arXiv:2403.04652_, 2024.


Rowan Zellers, Ari Holtzman, Yonatan Bisk, Ali Farhadi, and Yejin Choi. HellaSwag: Can a machine
really finish your sentence? _arXiv preprint arXiv:1905.07830_, 2019.


Qiusi Zhan, Richard Fang, Rohan Bindu, Akul Gupta, Tatsunori Hashimoto, and Daniel Kang.
Removing RLHF protections in GPT-4 via fine-tuning. _arXiv preprint arXiv:2311.05553_, 2023.


Chujie Zheng, Fan Yin, Hao Zhou, Fandong Meng, Jie Zhou, Kai-Wei Chang, Minlie Huang, and
Nanyun Peng. Prompt-driven LLM safeguarding via directed representation optimization. _arXiv_
_preprint arXiv:2401.18018_, 2024.


Andy Zou, Long Phan, Sarah Chen, James Campbell, Phillip Guo, Richard Ren, Alexander Pan,
Xuwang Yin, Mantas Mazeika, Ann-Kathrin Dombrowski, et al. Representation engineering: A
top-down approach to AI transparency. _arXiv preprint arXiv:2310.01405_, 2023a.


Andy Zou, Zifan Wang, J Zico Kolter, and Matt Fredrikson. Universal and transferable adversarial
attacks on aligned language models. _arXiv preprint arXiv:2307.15043_, 2023b.


17


**A** **Dataset details**


**A.1** **Harmful instructions**


To construct _D_ harmful [(train)] [, we randomly sample a total of 128 harmful instructions from A][DV][B][ENCH][ (][Zou]
et al., 2023b), MALICIOUSINSTRUCT (Huang et al., 2023), and TDC2023 (Mazeika et al., 2023,
2024).

To construct _D_ harmful [(val)] [,] [we sample 32 instructions from the] [H][ARM][B][ENCH] [validation set (][Mazeika]
et al., 2024). We use only the “standard behaviors”, and exclude instructions that require context or
concern copyright violations.


In §3, we evaluate over JAILBREAKBENCH (Chao et al., 2024), a dataset containing 100 harmful instructions, spanning 10 categories: harassment/discrimination, malware/hacking, physical
harm, economic harm, fraud/deception, disinformation, sexual/adult content, privacy, expert advice,
government decision-making.


In §4, we evaluate over the HARMBENCH test set (Mazeika et al., 2024). We consider only the 159
“standard behaviors”, and exclude instructions that require context or concern copyright violations.
These harmful instructions span 6 categories: cybercrime & unauthorized intrusion, chemical &
biological weapons/drugs, misinformation & disinformation, harassment & bullying, illegal activities,
general harm.

Note that we perform filtering to ensure that _D_ harmful [(train)] [,] _[ D]_ harmful [(val)] [, and the two evaluation datasets are all]
pairwise disjoint, containing no overlapping instructions.


Figure 7: A random sample of instructions from _D_ harmful [(train)] [.]


**A.2** **Harmless instructions**


To construct the harmless datasets, we sample instructions from ALPACA (Taori et al., 2023). _D_ harmless [(train)]
contains 128 instructions, and _D_ harmless [(val)] [contains 32 instructions.]


In §3, we evaluate over 100 instructions from ALPACA.

Note that _D_ harmless [(train)] [,] _[D]_ harmless [(val)] [,] [and] [the] [evaluation] [dataset] [are] [all] [pairwise] [disjoint,] [containing] [no]
overlapping instructions.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-17-0.png)

![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-17-1.png)



Figure 8: A random sample of instructions from _D_ harmless [(train)] [.]


18


**B** **Refusal metric:** **an efficient proxy for measuring refusal**


Evaluating whether a model refuses a particular instruction is most accurately done by generating
a full completion using greedy decoding, and then assessing whether the generated text constitutes
a refusal. However, this process can be computationally expensive, especially when working with
large models and a large number of instructions. To address this, we define a more efficient proxy
for estimating the likelihood of a model refusing a given instruction without requiring generation
(Figure 10).


We observe that each model tends to have a small set of characteristic phrases that it typically uses to
begin its refusals (Figure 9). This allows us to approximate the probability of refusal by examining
the model’s next token probability distribution at the last token position, which corresponds to the
start of its completion.


Formally, for each model, we define a set of refusal tokens _R ⊆V_, which contains the tokens most
likely to begin the model’s refusals (Table 4). We can then estimate the probability of refusal _P_ refusal
as the sum of the probabilities assigned to the tokens in _R_ . Given a vector of next token probabilities
**p** = ( _p_ 1 _, p_ 2 _, . . ., p|V|_ ) _∈_ R _[|V|]_, we define


_P_ refusal( **p** ) :=             - _pt._ (6)


_t∈R_


To create a more informative “refusal metric”, we take the log-odds of _P_ refusal. This transformation
helps to better distinguish between extreme probabilities that are close to 0 or 1 (Wang et al., 2023).


`refusal_metric` ( **p** ) := logit ( _P_ refusal( **p** )) (7)




  - _P_ refusal( **p** )
= log
1 _−_ _P_ refusal( **p** )




(8)






 _._ (9)









 [�] _pt_

_t∈V\R_



= log



��

_pt_

_t∈R_




_−_ log



We use this metric to filter out instructions in our test and validation datasets: for harmful instructions,
we filter out prompts yielding `refusal_metric` _<_ 0, and for harmless instruction, we filter out
prompts yielding `refusal_metric` _>_ 0. We also use this metric to quickly evaluate the efficacy of
interventions over the validation set (§C).



Next token probability across harmful data



Next token probability across harmless data



'I'(235285)



'Sure'(21404)



'**'(688)
'The'(651)
'##'(1620)
'1'(235274)

'```'(1917)
'I'(235285)
'A'(235280)
'One'(4038)



'**'(688)
'##'(1620)
'Pyramid'(181096)



'Sub'(3351)
'Modifying'(163987)



'As'(2169)
'The'(651)
'Tax'(17790)
'Black'(9737)



'If'(2495)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-18-0.png)

0.0 0.2 0.4 0.6 0.8 1.0
Next token probability (mean)


(a) Top-10 token probabilities for GEMMA 2B IT, averaged over 128 harmful instructions.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-18-1.png)

0.0 0.1 0.2 0.3 0.4
Next token probability (mean)


(b) Top-10 token probabilities for GEMMA 2B IT, averaged over 128 harmless instructions.



Figure 9: Next token probabilities for GEMMA 2B IT across harmful and harmless instructions.


19


30


20


10


0



Refusal metric

|Col1|Col2|Col3|Col4|Col5|Col6|harmful|
|---|---|---|---|---|---|---|
|||||||~~armless~~|
||||||||
||||||||
||||||||



15 10 5 0 5 10
Refusal metric



Figure 10: The refusal metric separates harmful and harmless instructions for GEMMA 2B IT.
Refusals generally begin with token 234285 (corresponding to `‘I’` ). Setting _R_ GEMMA = _{_ 234285 _}_
yields a refusal metric that is an efficient proxy for assessing whether the model will refuse.


Table 4: The refusal token set _R_ that we use for each model family, along with the refusal phrases
corresponding to each token.


Model family Refusal token set _R_ Corresponding refusal phrases


QWEN CHAT { 40 _,_ 2121 } { `"I’m` `sorry"`, `"As` `an` `AI"` }
GEMMA IT { 235285 } { `"I` `cannot"` }
YI CHAT { 59597 } { `"I’m` `sorry"` }
LLAMA-2 CHAT { 306 } { `"I` `cannot"` }
LLAMA-3 INSTRUCT { 40 } { `"I` `cannot"` }


20


**C** **Direction selection**


**C.1** **Direction selection algorithm**


Given a set of difference-in-means vectors _{_ **r** [(] _i_ _[l]_ [)] _[|][i][ ∈]_ _[I, l]_ _[∈⌈][L][⌉}]_ [, we want to select the best vector]
**r** [(] _i_ _[∗][l][∗]_ [)][.] [For each vector] **[ r]** [(] _i_ _[l]_ [)][, we compute the following:]


    - `bypass_score` : under directional ablation of **r** [(] _i_ _[l]_ [)][,] [compute] [the] [average] [refusal] [metric]
across _D_ harmful [(val)] [.]

    - `induce_score` : under activation addition of **r** [(] _i_ _[l]_ [)][, compute the average refusal metric across]
_D_ harmless [(val)] [.]

    - `kl_score` : run the model on _D_ harmless [(val)] [with] [and] [without] [directional] [ablation] [of] **[r]** [(] _i_ _[l]_ [)][,] [and]
compute the average KL divergence between the probability distributions at the last token
position.


We then select **r** [(] _i_ _[∗][l][∗]_ [)] to be the direction with minimum `bypass_score`, subject to the following
conditions:


    - `induce_score` _>_ 0

**–** This condition filters out directions that are not _sufficient_ to induce refusal.

    - `kl_score` _<_ 0 _._ 1

**–** This condition filters out directions that significantly change model behavior on harmless prompts when ablated.

    - _l <_ 0 _._ 8 _L_

**–** This condition ensures that the direction is not too close to the unembedding directions.
Intuitively, one could disable refusal by preventing the model from writing to refusal
unembed directions, e.g. directions corresponding to the `‘I’` or `‘As’` unembedding
directions, and this would directly prevent the model from outputting these refusal
tokens. However, we restrict our search to higher level features, and do not prevent the
model from outputting specific tokens (see §L.1).


Using the compute setup described in §N, this direction selection procedure takes about an hour to
run for the largest models (72 billion parameters), and faster for smaller models.


**C.2** **Direction selection for each model**


We report details of direction selection for each model in Table 5, including the token position _i_ _[∗]_ and
layer _l_ _[∗]_ from which the direction was sourced, along with the direction’s corresponding metrics.


Figure 11 displays the `bypass_score` and `induce_score` of all candidate directions for LLAMA-3
8B INSTRUCT.


**C.3** **Chat templates**


We use the default chat template for each model family. All chat templates are displayed in Table 6.


21


Table 5: Direction selection details for each model. Note that _i_ _[∗]_ = _−_ 1 indicates that the direction is
selected from the last token position, _i_ _[∗]_ = _−_ 2 the second-to-last token position, and so on. Also note
that the layer index _l_ _[∗]_ starts from index 0, while _L_ indicates the total number of layers.


Chat model _i_ _[∗]_ _l_ _[∗]_ _/L_ `bypass_score` `induce_score` `kl_score`


QWEN 1.8B _−_ 1 15 _/_ 24 _−_ 4 _._ 415 1 _._ 641 0 _._ 077
QWEN 7B _−_ 1 17 _/_ 32 _−_ 5 _._ 355 1 _._ 107 0 _._ 069
QWEN 14B _−_ 1 23 _/_ 40 _−_ 5 _._ 085 1 _._ 606 0 _._ 014
QWEN 72B _−_ 1 62 _/_ 80 _−_ 4 _._ 246 1 _._ 885 0 _._ 034
YI 6B _−_ 5 20 _/_ 32 _−_ 6 _._ 693 1 _._ 968 0 _._ 046
YI 34B _−_ 1 37 _/_ 60 _−_ 11 _._ 14 1 _._ 865 0 _._ 069
GEMMA 2B _−_ 2 10 _/_ 18 _−_ 14 _._ 435 6 _._ 709 0 _._ 067
GEMMA 7B _−_ 1 14 _/_ 28 _−_ 12 _._ 239 6 _._ 851 0 _._ 091
LLAMA-2 7B _−_ 1 14 _/_ 32 _−_ 5 _._ 295 5 _._ 941 0 _._ 073
LLAMA-2 13B _−_ 1 26 _/_ 40 _−_ 4 _._ 377 2 _._ 794 0 _._ 092
LLAMA-2 70B _−_ 1 21 _/_ 80 _−_ 4 _._ 565 5 _._ 191 0 _._ 036
LLAMA-3 8B _−_ 5 12 _/_ 32 _−_ 9 _._ 715 7 _._ 681 0 _._ 064
LLAMA-3 70B _−_ 5 25 _/_ 80 _−_ 7 _._ 839 0 _._ 126 0 _._ 021



10.0


7.5


5.0


2.5


0.0


2.5


5.0


7.5


10.0



|Col1|Col2|Col3|Col4|Bypass score|Col6|Col7|
|---|---|---|---|---|---|---|
||||||||
||||||||
||||||||
||||||||
||||||||
||||||Source position<br>|Source position<br>|
||||||~~pos -5: '<|eot_id|>'~~<br>pos -4: '<|start_header_id|>'<br>|~~pos -5: '<|eot_id|>'~~<br>pos -4: '<|start_header_id|>'<br>|
||||||~~pos -3: 'assistant'~~<br>pos -2: '<|end_header_id|>'<br>~~pos -1: '\n\n'~~|~~pos -3: 'assistant'~~<br>pos -2: '<|end_header_id|>'<br>~~pos -1: '\n\n'~~|


0 5 10 15 20 25 30
Source layer



10


5


0


5


10



|Induce score|Col2|
|---|---|
|||
|||
|||
||Source position<br>pos -5: '<|eot_id|>'<br>pos -4: '<|start_header_id|>'<br>|
||~~pos -3: 'assistant'~~<br>pos -2: '<|end_header_id|>'<br>~~pos -1: '\n\n'~~|


0 5 10 15 20 25 30
Source layer



Figure 11: The `bypass_score` (left) and `induce_score` (right) of each candidate direction for
LLAMA-3 8B INSTRUCT. Each candidate direction **r** [(] _i_ _[l]_ [)] corresponds to source position _i_ and source
layer _l_ .


Table 6: Model families and their corresponding chat templates. The user instruction is denoted as
`{x}` . Post-instruction tokens, as defined in §2.1, are labeled in red.


Model family Corresponding refusal phrases


QWEN CHAT `"<|im_start|>user\n{x}<|im_end|>\n<|im_start|>assistant\n"`
GEMMA IT `"<start_of_turn>user\n{x}<end_of_turn>\n<start_of_turn>model\n"`
YI CHAT `"<|im_start|>user\n{x}<|im_end|>\n<|im_start|>assistant\n"`
LLAMA-2 CHAT `"[INST]` `{x}[/INST]` `"`
```
            "<|start_header_id|>user<|end_header_id|>\n\n
```

LLAMA-3 INSTRUCT
```
            {x}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

```

22


**D** **Refusal evaluation**


**D.1** **Refusal score**


For a model completion **c**, `refusal_score` ( **c** ) = 1 if **c** contains at least one “refusal substring”;
otherwise `refusal_score` ( **c** ) = 0.


Figure 12 displays the “refusal substrings” that are used in the `refusal_score` evaluation. Note that
the substring comparison is not sensitive to capitalization, and checks that the phrases are contained
_anywhere_ in the completion, not just at the start.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-22-0.png)



Figure 12: The set of “refusal substrings”, used to evaluate the `refusal_score` of a given completion.


**D.2** **Safety score**


For a model completion **c**, `safety_score` ( **c** ) = 1 if META LLAMA GUARD 2 (Team, 2024) outputs
that the completion is `safe` ; otherwise `safety_score` ( **c** ) = 0.


Figure 13 displays the template used to prompt META LLAMA GUARD 2. Note that we use the
default prompt specified by the model providers, without any custom alteration.


**D.3** **Challenges of evaluating refusal**


Assessing whether a completion constitutes a successful jailbreak is complex. In this subsection, we
highlight scenarios that are ambiguous, motivating our use of two metrics.


Figure 14 and Figure 15 display cases in which the model does not explicitly refuse, but also does
not provide a harmful response. In these scenarios, `refusal_score=0` while `safety_score=1` .


Figure 16 displays a case in which the model initially refuses, but then goes on to give a harmful
response. In these scenarios, `refusal_score=1` while `safety_score=0` .


**D.4** **Reporting of confidence intervals**


In Figure 1 and Figure 3, we display error bars corresponding to standard error (SE), computed as

SE = ~~�~~ _p_ (1 _n−p_ ) . In both cases, _n_ = 100.


23


![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-23-0.png)





Figure 13: The default prompt template for META LLAMA GUARD 2, used to evaluate the
`safety_score` of a given completion.


24


![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-24-0.png)

Figure 14: _Challenges_ _of_ _evaluating_ _refusal_ . The model completion does not explicitly use a
refusal phrase ( `refusal_score=0` ), but it does not contain harmful content ( `safety_score=1` ).
This completion is taken from the orthogonalized LLAMA-3 70B CHAT model.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-24-1.png)

Figure 15: _Challenges of evaluating refusal_ . The model completion does not use a refusal phrase
( `refusal_score=0` ), but it does not contain harmful content ( `safety_score=1` ). This completion
is taken from the orthogonalized GEMMA 7B IT model.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-24-2.png)



Figure 16: _Challenges_ _of_ _evaluating_ _refusal_ . The model completion does use a refusal phrase
( `refusal_score=1` ), but it also contains harmful content ( `safety_score=0` ). This completion is
taken from the orthogonalized QWEN 72B CHAT model.


25


**E** **Weight orthogonalization is equivalent to directional ablation**


To show the equivalence of directional ablation and weight orthogonalization, we consider all matrices
that directly write contributions to the residual stream.

Let _W_ out _∈_ R _[d]_ [model] _[×][d]_ [input] be a matrix that writes to the residual stream, mapping vectors from R _[d]_ [input] to
R _[d]_ [model] . [5] Let the unit norm vector ˆ **r** _∈_ R _[d]_ [model] denote the direction to be ablated.


Now let **x** pre _∈_ R _[d]_ [model] denote the residual stream activation before _W_ out adds a contribution to the
residual stream, let **x** post denote the residual stream activation after, and let **t** _∈_ R _[d]_ [input] denote the input
to _W_ out:


**x** post = **x** pre + _W_ out **t** _._ (10)


With directional ablation, we take **x** post and zero out its projection onto ˆ **r** :

**x** _[′]_ post [=] **[ x]** [post] _[−]_ [ˆ] **[r]** [ˆ] **[r]** [⊺] **[x]** [post] (11)

= ( **x** pre + _W_ out **t** ) _−_ ˆ **r** ˆ **r** [⊺] ( **x** pre + _W_ out **t** ) (12)
= **x** pre + _W_ out **t** _−_ ˆ **r** ˆ **r** [⊺] **x** pre _−_ ˆ **r** ˆ **r** [⊺] _W_ out **t** (13)
= **x** pre _−_ ˆ **r** ˆ **r** [⊺] **x** pre + ( _W_ out _−_ ˆ **r** ˆ **r** [⊺] _W_ out) **t** _._ (14)


Supposing that directional ablation was similarly applied after all previous contributions to the
residual stream, we have that ˆ **r** [⊺] **x** pre = 0:

**x** _[′]_ post [=] **[ x]** [pre] [+ (] _[W]_ [out] _[−]_ [ˆ] **[r]** [ˆ] **[r]** [⊺] _[W]_ [out][)] **[t]** (15)

= **x** pre + _W_ out _[′]_ **[t]** (16)

where _W_ out _[′]_ [=] _[ W]_ [out] _[−]_ [ˆ] **[r]** [ˆ] **[r]** [⊺] _[W]_ [out][, as specified by weight orthogonalization in][ Equation 5][.]


5Note that _d_ input varies depending on which matrix is being considered. For example it would be the
vocabulary size _|V|_ if considering the embedding matrix, or the hidden MLP dimension _d_ hidden if considering the
MLP down-projection matrix, etc.


26


**F** **Jailbreak evaluation**


**F.1** **Comparing to other jailbreaks**


To compare the effectiveness of our jailbreak method to other methods in the literature, we report
the 5 top performing jailbreak attacks, as ranked by HARMBENCH attack success rate (ASR) on
the LLAMA-2 model family: GCG is the algorithm from Zou et al. (2023b) which optimizes an
adversarial suffix for each prompt and each model; GCG-M is the multi-prompt version of GCG,
trained over multiple prompts for each model; GCG-T is the transferable version of GCG-M, trained
over multiple prompts and across multiple models; AP is the AutoPrompt approach from Shin et al.
(2020); PAIR is a black-box method from Chao et al. (2023). We also include comparisons to the set
of human-written “Do Anything Now” adversarial templates from Shen et al. (2023) (HUMAN), and
the “direct response” baseline without any jailbreaks in place (DR).


**F.2** **Effect of system prompts on evaluation**


Table 2 shows that the attack success rate (ASR) of our weight orthogonalization methodology is
sensitive to system prompts. Including the default system prompt in evaluation substantially reduces
HARMBENCH ASR for LLAMA-2 models, while having minimal effect on QWEN models.


As shown in Figure 17, the LLAMA-2 default system prompt includes explicit guidelines to avoid
harmful or inappropriate content. In contrast, the QWEN default system prompt, shown in Figure 18,
is minimal and lacks specific directives about safety or ethics.


We initially hypothesized that the discrepancy in ASR might be due to the LLAMA-2 system prompt’s
explicit guidelines, making it particularly effective at enforcing safety guardrails. To test this, we
applied the LLAMA-2 system prompt to QWEN models, but observed no significant change in ASR, as
shown in Table 7. This suggests that the impact of system prompts on ASR may be model-dependent.


To investigate LLAMA-2’s responsiveness to system prompts further, we evaluated the same orthogonalized LLAMA-2 7B model with 12 diverse system prompts (shown in Figure 19). This evaluation
revealed substantial variability in ASR scores for LLAMA-2 7B, with a mean of 30.0% and standard
deviation of 23.3%, while QWEN 7B maintained a more consistent performance across the same
set of prompts, with a mean of 76.7% and standard deviation of 5.9%. These findings suggest that
LLAMA-2 models may be more responsive to system-level instructions than other model families,
particularly with respect to safety-related behaviors. A more systematic study would be necessary to
fully understand these differences, as well as the broader relationship between system prompts and
refusal behaviors, which we leave as directions for future research.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-26-0.png)

Figure 17: The default system prompt for LLAMA-2 CHAT.





Figure 18: The default system prompt for QWEN CHAT.


27


Table 7: Attack success rate (ASR) on HARMBENCH using different system prompts. The QWEN
CHAT system prompt is minimal, while the LLAMA-2 CHAT system prompt contains explicit safety
guidelines. Orthogonalized QWEN CHAT models maintain high ASR even with the more restrictive
LLAMA-2 CHAT system prompt. See Figure 17 and Figure 18 for the full system prompts.


Orthogonalized model QWEN CHAT system prompt LLAMA-2 CHAT system prompt


QWEN 7B 79.2 75.5
QWEN 14B 84.3 78.0



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-27-0.png)

Figure 19: The set of system prompts used to evaluate model sensitivity. Note that “[none]” indicates
no system prompt was provided, while “[empty string]” indicates an empty string was provided as
the system prompt.


28


**G** **Model coherence evaluation**


**G.1** **Language model evaluation**


Table 8: Model evaluations. For each evaluation, we report the orthogonalized model’s performance,
followed by the baseline model’s performance, followed by the absolute increase or decrease.


Chat model MMLU TINYHELLASWAG ARC WINOGRANDE GSM8K TRUTHFULQA


QWEN 1.8B 43.0 / 43.1 (-0.1) 48.2 / 49.3 (-1.1) 37.6 / 38.7 (-1.1) 59.6 / 59.0 (+0.6) 29.7 / 30.0 (-0.3) 37.1 / 41.7 (-4.6)
QWEN 7B 54.8 / 56.8 (-2.0) 76.3 / 73.1 (+3.2) 52.0 / 51.7 (+0.3) 72.0 / 72.5 (-0.5) 41.8 / 48.1 (-6.3) 47.9 / 51.6 (-3.7)
QWEN 14B 66.1 / 65.9 (+0.2) 77.3 / 79.5 (-2.2) 60.3 / 61.3 (-1.0) 74.8 / 74.7 (+0.1) 59.3 / 60.3 (-1.0) 50.4 / 52.9 (-2.5)
QWEN 72B 76.5 / 77.2 (-0.7) 86.5 / 85.3 (+1.2) 67.2 / 67.6 (-0.4) 80.7 / 80.8 (-0.1) 76.3 / 75.5 (+0.8) 55.0 / 56.4 (-1.4)
YI 6B 62.6 / 63.2 (-0.6) 78.1 / 76.8 (+1.3) 56.6 / 57.4 (-0.8) 72.9 / 72.2 (+0.7) 39.0 / 40.6 (-1.6) 44.2 / 50.1 (-5.9)
YI 34B 73.5 / 74.9 (-1.4) 83.6 / 84.6 (-1.0) 65.6 / 64.9 (+0.7) 78.9 / 80.2 (-1.3) 65.5 / 65.0 (+0.5) 51.9 / 55.4 (-3.5)
GEMMA 2B 36.8 / 36.9 (-0.1) 57.1 / 55.2 (+1.9) 43.0 / 43.3 (-0.3) 60.5 / 61.5 (-1.0) 10.8 / 11.1 (-0.3) 40.4 / 45.8 (-5.4)
GEMMA 7B 51.8 / 51.7 (+0.1) 46.5 / 44.9 (+1.6) 51.7 / 51.5 (+0.2) 66.6 / 66.5 (+0.1) 31.3 / 32.0 (-0.7) 44.7 / 47.1 (-2.4)
LLAMA-2 7B 46.8 / 47.5 (-0.7) 76.8 / 77.6 (-0.8) 53.0 / 53.7 (-0.7) 71.7 / 72.6 (-0.9) 22.7 / 23.1 (-0.4) 41.6 / 45.3 (-3.7)
LLAMA-2 13B 53.6 / 53.6 (+0.0) 82.3 / 83.2 (-0.9) 60.4 / 60.3 (+0.1) 73.4 / 74.3 (-0.9) 35.3 / 35.6 (-0.3) 42.6 / 44.0 (-1.4)
LLAMA-2 70B 63.1 / 63.0 (+0.1) 84.8 / 84.8 (+0.0) 65.2 / 65.4 (-0.2) 79.7 / 80.2 (-0.5) 54.5 / 53.0 (+1.5) 51.8 / 52.8 (-1.0)
LLAMA-3 8B 65.0 / 65.8 (-0.8) 79.6 / 82.1 (-2.5) 62.3 / 62.4 (-0.1) 75.9 / 75.5 (+0.4) 74.3 / 75.9 (-1.6) 48.3 / 51.7 (-3.4)
LLAMA-3 70B 79.8 / 79.9 (-0.1) 85.4 / 86.1 (-0.7) 71.5 / 71.8 (-0.3) 83.4 / 83.6 (-0.2) 90.8 / 91.2 (-0.4) 59.5 / 61.8 (-2.3)


Except on TRUTHFULQA, orthogonalization has a very small effect on general performance benchmarks. We observe less than 1% performance drop on average, with the difference to the baseline
performance being indistinguishable from noise in most cases. The main exceptions are QWEN 7B,
which has statistically significant drops on MMLU and GSM8K, and YI 34B with drops on MMLU
and WINOGRANDE.


For MMLU, we use the default settings from LM Evaluation Harness (Biderman et al., 2024; Gao
et al., 2023) as of May 2024. For the other benchmarks, we use the default settings, with the exception
that models are run using vLLM (Kwon et al., 2023).


TINYHELLASWAG from TINYBENCHMARKS (Polo et al., 2024) is a statistically informative 400sample subset of the larger HELLASWAG (Zellers et al., 2019) test set. Polo et al. (2024) claim a 2%
average error compared to the full-sized counterparts.


**G.2** **TRUTHFULQA accuracy**


TRUTHFULQA measures the performance of language models in generating truthful and accurate
responses, particularly in areas prone to human misconceptions and falsehoods. Table 8 displays
clearly that TRUTHFULQA performance is consistently worse for orthogonalized models as compared
with unmodified models. TRUTHFULQA contains questions that touch on sensitive topics such as
misinformation, stereotypes, and conspiracies. For such questions, models with and without safety
guardrails may understandably generate different responses. Figure 20 displays an example of a
conspiracy-flavored question from TRUTHFULQA, and the contrasting responses from LLAMA-3 8B
INSTRUCT and its orthogonalized version.


**G.3** **CE loss evaluation**


In addition to standard language model evaluations, we also check changes in cross-entropy (CE)
loss over various datasets. For each chat model and its orthogonalized version we compute CE loss
over a sample of THE PILE (Min et al., 2023). THE PILE consists of scraped webtext, and so we do
not append any chat template when evaluating CE loss.


We note that some chat models are especially sensitive to chat templates, and behave poorly without
them. Thus, we also evaluate over ALPACA (Taori et al., 2023), which is a chat dataset consisting of
instructions and completions. We format each instruction according to each model’s chat template,
and compute CE loss only over the completion tokens.


We further note that some chat models, seemingly GEMMA 7B IT in particular, have high CE loss
on text that is out of distribution, e.g. completions from ALPACA. To account for this, we take each
baseline model, and generate completions on 100 instructions from ALPACA. We then compute CE
loss over these “on-distribution” completion tokens.


29


![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-29-0.png)



Figure 20: A question from TRUTHFULQA, and corresponding completions from LLAMA-3 8B
INSTRUCT and its orthogonalized version.


Table 9: Model performance as measured by CE loss across different datasets.


CE Loss (THE PILE) CE Loss (ALPACA) CE Loss (On-distribution)


Chat model Baseline Ablation Act Add Baseline Ablation Act Add Baseline Ablation Act Add


QWEN 1.8B 2.921 2.938 3.259 1.779 1.784 2.038 0.284 0.293 0.586
QWEN 7B 2.259 2.277 2.388 1.615 1.631 1.697 0.242 0.278 0.479
QWEN 14B 2.070 2.078 2.230 1.602 1.606 1.713 0.212 0.218 0.443
QWEN 72B 1.944 1.971 2.097 1.740 1.768 2.124 0.147 0.162 0.380
YI 6B 2.019 2.017 2.205 1.889 1.882 2.078 0.277 0.311 0.731
YI 34B 1.862 1.872 2.002 1.971 2.008 2.066 0.191 0.259 0.680
GEMMA 2B 3.506 3.489 3.739 2.090 2.101 2.179 0.254 0.311 0.853
GEMMA 7B 5.975 5.963 6.051 2.336 2.335 2.356 0.201 0.228 0.656
LLAMA-2 7B 2.220 2.214 2.333 1.609 1.586 1.584 0.118 0.126 0.460
LLAMA-2 13B 2.082 2.087 2.325 1.563 1.591 1.642 0.102 0.116 0.336
LLAMA-2 70B 1.970 1.969 2.010 1.657 1.659 1.630 0.067 0.070 0.169
LLAMA-3 8B 2.348 2.362 2.469 1.912 1.944 1.912 0.195 0.213 0.441
LLAMA-3 70B 2.121 2.117 2.274 1.980 1.978 1.928 0.116 0.126 0.265


All CE loss values are reported in Table 9. We denote the orthogonalized model as “Ablation”. We
also compare to activation addition methodology, labeled “Act Add”, where rather than ablating the
refusal direction, we _subtract_ the difference-in-means vector. See §I.1 for a more detailed discussion
of bypassing refusal via activation addition.


30


**H** **Adversarial suffix analysis**


**H.1** **Adversarial suffix generation**


Using a custom implementation of Greedy Coordinate Gradient (GCG) (Zou et al., 2023b), we
generated 100 adversarial suffixes of token-length 20, each of which was optimized for a particular
behavior from ADVBENCH.


Of these 100 suffixes, we found one suffix in particular that performs well across a wide range of
harmful prompts. The suffix is shown in Figure 21.





Figure 21: The adversarial suffix studied in §5. This suffix is generally effectively in bypassing
refusal in QWEN 1.8B CHAT.


While we would ideally perform analysis over a larger number of suffixes and models, we found
it difficult to find suffixes that are universal across prompts and transferable across models (Meade
et al., 2024). We therefore restrict our analysis to a single model, QWEN 1.8B CHAT, and a single
suffix.


**H.2** **Reporting of confidence intervals**


In Figure 5, for each layer and scenario, we display the standard deviation (SD) of cosine similarities

across 128 prompts, computed as SD = - - ( _xni−x_ )2 . In this case, _n_ = 128.


31


**I** **Comparison to other methodologies**


In §3.1, we use _directional ablation_ to bypass refusal. In §4, we show how this can be implemented
as a direct weight modification, and then analyze the modification’s effect on refusal and coherence.


In this section, we compare directional ablation to two other weight modification methodologies:
activation addition and fine-tuning.


**I.1** **Comparison to activation addition**



0.6


0.4


0.2


0.0


0.2


0.4




|Col1|Col2|Col3|Col4|Col5|Col6|harmful<br>harmless<br>harmful, act add<br>harmless, act add<br>directional ablation|Col8|
|---|---|---|---|---|---|---|---|
|||||||||
|||||||||
|||||||||
|||||||||
|||||||||
|||||||||
|||||||||
|||||||||
|||||||||
|||||||||



0 5 10 15 20 25
Layer


Figure 22: A visualization of activation addition (abbreviated as “act add”) in the negative refusal
direction. The intervention pulls harmful activations towards harmless activations, effectively bypassing refusal. However, note that the intervention pushes harmless activations far out of distribution.
This figure displays activations from GEMMA 7B IT, computed over 128 harmful and harmless
prompts.


In §2.4, we described how to induce refusal using activation addition. Given a difference-in-means
vector **r** [(] _[l]_ [)] _∈_ R _[d]_ [model] extracted from layer _l_, we can _add_ this vector at layer _l_ in order to shift
activations towards refusal (Equation 3). Similarly, we can _subtract_ this vector at layer _l_ in order to
shift activations away from refusal:


**x** [(] _[l]_ [)] _[′]_ _←_ **x** [(] _[l]_ [)] _−_ **r** [(] _[l]_ [)] _._ (17)


We perform this intervention at all token positions. Note that this intervention can be implemented as
a direct weight modification by subtracting **r** [(] _[l]_ [)] from the bias term of `MLP` [(] _[l][−]_ [1)] .


As shown in Figure 23, this activation addition intervention is effective in bypassing refusal. The
decreases in refusal score and safety score are comparable to those achieved by directional ablation
(Figure 1). However, Table 9 displays that the activation addition intervention, labeled as _act add_,
causes increased loss over harmless data, in particular compared to directional ablation.


Figure 22 displays a visualization of activation addition in the negative refusal direction, and suggests
an intuitive explanation of the intervention’s behavior on harmful and harmless prompts. On harmful
inputs, adding the negative refusal direction shifts the harmful activations towards harmless activations,
with respect to projection onto the refusal direction. With low projection onto the refusal direction,
this intervention leads to low rates of refusal. However, on harmless inputs, adding the negative
refusal direction shifts the harmless activations off distribution, resulting in increased perplexity.


Note that, in comparison to activation addition, directional ablation shifts harmful activations towards
harmless activations, while also not shifting harmless activations too far off distribution.


32


1.0


0.8


0.6


0.4


0.2


0.0




|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Score type|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|||||||||||||||Score type<br>Refusal score<br>Safety score<br>**Condition**<br>**No intervention**<br>**Activation**<br>**addition**||
|||||||||||||||||
|||||||||||||||||
|||||||||||||||||
|||||||||||||||||



Figure 23: Performing activation addition in the negative “refusal direction”, displayed in dots,
reduces refusal rates and elicits unsafe completions. It is approximately as effective as directional
ablation at bypassing refusal (Figure 1).


**I.2** **Comparison to fine-tuning**


Table 10: Refusal and CE loss evaluation metrics for LLAMA-3 8B INSTRUCT, comparing the
interventions of directional ablation, activation addition, and fine-tuning.


Refusal CE Loss


Intervention Refusal score Safety score THE PILE ALPACA On-distribution


No intervention 0.95 0.97 2.348 1.912 0.195
Directional ablation 0.01 0.15 2.362 1.944 0.213
Activation addition 0.01 0.16 2.469 1.912 0.441
Fine-tuning 0.00 0.08 2.382 1.626 0.273


Prior work has established that fine-tuning is effective in removing safety guardrails of chat models
(Lermen et al., 2023; Yang et al., 2023; Zhan et al., 2023).


We replicate this result by fine-tuning LLAMA-3 8B INSTRUCT. First, we construct a dataset of
harmful instruction-completion pairs. For the harmful instructions, we sample instructions from
ADVBENCH, MALICIOUSINSTRUCT, TDC2023, and HARMBENCH. To generate corresponding
harmful completions, we use MISTRAL 7B INSTRUCT (Jiang et al., 2023), a competent chat model
with low refusal rates. For each harmful instruction, we generate 5 completions, and then select
a single completion satisfying both `refusal_score=0` and `safety_score=0` . If no completions
satisfy this condition, then the instruction is discarded. After this filtering, we were left with a dataset
of 243 harmful instruction-completion pairs.


We then fine-tuned LLAMA-3 8B INSTRUCT on the constructed dataset, applying LoRA (Hu et al.,
2021) with `rank=16` and `alpha=32` for 4 epochs. The LoRA fine-tuning was performed on an A100
GPU with 80GB of VRAM, and took approximately 10 minutes.


Evaluations of refusal and CE loss are displayed in Table 10. In accordance with prior work, we
confirm fine-tuning to be very effective in disabling refusal. We speculate that the decrease in CE
loss over ALPACA could be due to the similarity between the distributions of MISTRAL INSTRUCT
completions and ALPACA completions, and as a result, fine-tuning over MISTRAL INSTRUCT
completions leads to a decreased CE loss over ALPACA completions.


We note that, although the LoRA fine-tuning process itself is straightforward and efficient, creating a
high-quality dataset of harmful instruction-completion pairs requires non-trivial effort. In comparison,
directional ablation (and its equivalent implementation via weight orthogonalization) requires just a
dataset of _harmful instructions_, without the need for any _harmful completions_ .


33


**J** **The “refusal direction” is also present in base models**


Throughout this work, we consider only _chat models_, models that have undergone fine-tuning to
follow benign instructions and refuse harmful ones. Prior to this fine-tuning process, models are
essentially just next-token predictors, referred to as _base models_ . By default, base models are not
instruction-following. For instance, if prompted with a question, a base model is likely to output
another question, rather than an answer to the original question. In particular, base models do not
refuse harmful requests.


In §3, we argue that refusal in chat models is mediated by a single direction in activation space. One
natural question is whether this direction, or feature, is learned from scratch during safety fine-tuning
specifically to mediate refusal, or whether this direction is already present in the base model and gets
repurposed, or “hooked into”, during safety fine-tuning.


To investigate this question, we check the expression of the refusal direction in chat and base models.
For each model, we sample 128 harmful and harmless instructions, run inference on both the chat
model (e.g. LLAMA-3 8B INSTRUCT) and its corresponding base model (e.g. LLAMA-3 8B), and
cache all intermediate activations at the last token position. [6] We then take the refusal direction
extracted from the corresponding chat model (§2.3), and examine the cosine similarity of each
activation with this direction.


Figure 24 displays the results for four distinct models. We find that, similarly to the chat models,
corresponding base models have high cosine similarity with the refusal direction when run on harmful
prompts, and low cosine similarity when run on harmless prompts. This suggests that, rather than
developing the “refusal direction” from scratch during fine-tuning, this representation exists already
in the base model, and is repurposed for refusal during safety fine-tuning.



Gemma 7B

|Col1|harmf<br>harmf|ul, chat<br>ul, base|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
||<br>harmle<br>~~harml~~|<br>ss, chat<br>~~ss, base~~|<br>ss, chat<br>~~ss, base~~||||||||||
||||||||||||||
||||||||||||||
||||||||||||||
||||||||||||||
||||||||||||||



0 5 10 15 20 25
Layer


Qwen 14B

|Col1|har|mful, c|hat|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
||~~har~~<br>har<br>~~har~~|~~mful, b~~<br>mless,<br>~~mless,~~|~~ se~~<br> chat<br>~~ ase~~|||||||||
|||||||||||||
|||||||||||||
|||||||||||||
|||||||||||||
|||||||||||||



0 5 10 15 20 25 30 35 40
Layer



0.5


0.4


0.3


0.2


0.1


0.0


0.5


0.4


0.3


0.2


0.1


0.0



Qwen 1.8B

|Col1|harmful,|chat|Col4|Col5|Col6|Col7|
|---|---|---|---|---|---|---|
||<br>harmful,<br>~~harmles~~|<br> base<br>~~, chat~~|||||
||<br>harmless|<br>, base|||||
||||||||
||||||||
||||||||
||||||||



0 5 10 15 20
Layer


Llama-3 8B

|Col1|Col2|Col3|Col4|Col5|ha|Col7|rmful, ch|Col9|at|Col11|
|---|---|---|---|---|---|---|---|---|---|---|
||||||~~ha~~<br>ha|~~ha~~<br>ha|~~rmful, b~~<br>rmless,|~~rmful, b~~<br>rmless,|~~ se~~<br> hat|~~ se~~<br> hat|
||||||<br>ha|<br>ha|<br>rmless, b|<br>rmless, b|<br> ase|<br> ase|
||||||||||||
||||||||||||
||||||||||||
||||||||||||
||||||||||||



0 5 10 15 20 25 30
Layer



0.5


0.4


0.3


0.2


0.1


0.0


0.4


0.3


0.2


0.1


0.0



Figure 24: Cosine similarity of activations with the refusal direction, for base (dotted lines) and chat
(solid lines) models. The refusal direction is expressed similarly in base and chat models.


6Note that we append a newline character to the end of each instruction, and consider activations only at this
token position. For chat models, we prepend the portion of the chat template that comes before the instruction.
For base models, we do not prepend anything before the instruction.


34


**K** **Extended results**


As throughout the paper, all generations are generated deterministically using greedy decoding.


**K.1** **Bypassing refusal - examples**



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-34-0.png)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-34-1.png)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-34-2.png)



Figure 25: Examples of bypassing refusal by ablating the “refusal direction”. These completions are
taken from LLAMA-3 70B INSTRUCT.


35


**K.2** **Inducing refusal - examples**



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-35-0.png)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-35-1.png)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-35-2.png)



Figure 26: Examples of inducing refusal by adding the “refusal direction”. These completions are
taken from GEMMA 7B IT.


36


**L** **Further experiments with orthogonalized models**


As throughout the paper, all generations are generated deterministically using greedy decoding. All
experiments in this section are performed on LLAMA-3 8B INSTRUCT.


**L.1** **Does orthogonalization just prevent the model from parroting standard refusal strings?**


One possible way to prevent a model from refusing is to directly block it from outputting any of the
standard refusal strings, such as `"Sorry,` `I` `cannot"`, or `"As` `a` `language` `model"` . Experiments
shown in Figure 27 show that this is not the case for our weight orthogonalization methodology, as
the orthogonalized model is able to generate the same strings that the unmodified model uses to refuse
a harmful request. This suggests that the modification works at a higher conceptual level, rather than
at the level of suppressing output tokens.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-36-0.png)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-36-1.png)



Figure 27: The unmodified model (no intervention) refuses the first request with the string `"I` `cannot`
`provide` `instructions` `on` `how` `to` `make` `a` `bomb"` . When explicitly requested to output this
string, the orthogonalized model (intervention) is able to do so.


37


**L.2** **The orthogonalized model behaves similarly on harmless instructions**


In general, we notice that the orthogonalized model behaves very similarly to the non-modified model
on harmless instructions. Figure 28 displays completions on a random sample of harmless prompts
from ALPACA. Generations from the unmodified model and the orthogonalized model appear to be
indistinguishable, and often the generations are exactly the same.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-37-0.png)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-37-1.png)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-37-2.png)



Figure 28: Generations over a random sample of harmless instructions from ALPACA. Generations
from the unmodified model (no intervention) are essentially indistinguishable from the orthogonalized
model (intervention).


38


**L.3** **The orthogonalized model may have trouble understanding its new refusal behavior**


As our intervention targets refusal directly, it is natural to ask how the resulting model answers
meta-questions about its new refusal behavior: does it understand its behavioral modification, or does
it default to explaining its original refusal behavior? As shown in Figure 29, the new model seems
likely to answer meta-refusal questions consistently with its previous refusal behavior. However, its
explanations seem not to be coherent.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Refusal in Language Models Is Mediated by a Single Direction_extracted/images/Refusal-in-Language-Models-Is-Mediated-by-a-Single-Direction.pdf-38-0.png)



Figure 29: The orthogonalized model gives the same answer to a meta-reasoning question about its
own refusal behavior as the original model. However, its reasoning seems incoherent: it claims the
reason for not explaining how to make a Molotov cocktail is “this is a factual question, but it’s not a
request for a creative response”.


39


**M** **Use of existing assets**


**M.1** **Models**


Table 11: The list of models used in this work.


Model Source Accessed via License


QWEN CHAT Bai et al. (2023) [Link](https://huggingface.co/Qwen/Qwen-1_8B-Chat) Tongyi Qianwen Research License
YI CHAT Young et al. (2024) [Link](https://huggingface.co/01-ai/Yi-6B-Chat) Apache License 2.0
GEMMA IT Team et al. (2024) [Link](https://huggingface.co/google/gemma-2b-it) Gemma Terms of Use
LLAMA-2 CHAT Touvron et al. (2023) [Link](https://huggingface.co/meta-llama/Llama-2-7b-chat-hf) Llama 2 Community License
LLAMA-3 INSTRUCT AI@Meta (2024) [Link](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct) Meta Llama 3 Community License
LLAMA GUARD 2 Team (2024) [Link](https://huggingface.co/meta-llama/Meta-Llama-Guard-2-8B) Meta Llama 3 Community License
HARMBENCH CLASSIFIER Mazeika et al. (2024) [Link](https://huggingface.co/cais/HarmBench-Llama-2-13b-cls) MIT License
MISTRAL INSTRUCT Jiang et al. (2023) [Link](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1) Apache License 2.0


**M.2** **Datasets**


Table 12: The list of datasets used in this work.


Dataset Source Accessed via License


ADVBENCH Zou et al. (2023b) [Link](https://github.com/llm-attacks/llm-attacks) MIT License
TDC2023 Mazeika et al. (2023, 2024) [Link](https://github.com/centerforaisafety/tdc2023-starter-kit) MIT License
HARMBENCH Mazeika et al. (2024) [Link](https://github.com/centerforaisafety/HarmBench/tree/main) MIT License
JAILBREAKBENCH Chao et al. (2024) [Link](https://github.com/JailbreakBench/jailbreakbench/tree/main) MIT License
MALICIOUSINSTRUCT Huang et al. (2023) [Link](https://github.com/princeton-sysml/jailbreak_llm) MIT License
ALPACA Taori et al. (2023) [Link](https://huggingface.co/datasets/tatsu-lab/alpaca) Apache License 2.0
THE PILE Gao et al. (2020) [Link](https://huggingface.co/datasets/monology/pile-uncopyrighted) MIT License
MMLU Hendrycks et al. (2020) [Link](https://huggingface.co/datasets/cais/mmlu) MIT License
ARC Clark et al. (2018) [Link](https://huggingface.co/datasets/allenai/ai2_arc) CC-BY-SA-4.0
GSM8K Cobbe et al. (2021) [Link](https://huggingface.co/datasets/openai/gsm8k) MIT License
WINDOGRANDE Sakaguchi et al. (2021) [Link](https://huggingface.co/datasets/allenai/winogrande) Apache License 2.0
TRUTHFULQA Lin et al. (2021) [Link](https://huggingface.co/datasets/truthfulqa/truthful_qa) Apache License 2.0
TINYHELLASWAG Polo et al. (2024) [Link](https://huggingface.co/datasets/tinyBenchmarks/tinyHellaswag) MIT License


**N** **Compute statement**


Most experiments presented in this paper were run on a cluster of eight NVIDIA RTX A6000 GPUs
with 48GB of memory. All experiments on models with _≤_ 14B parameters are run using a single
48GB memory GPU. For larger models, we use four 48BG memory GPUs in parallel.


Generating and selecting the directions, as described in §2.3, takes approximately 5 minutes for
smaller models of size _≤_ 14B, and approximately 1 hour for the larger models.


40


**NeurIPS Paper Checklist**


1. **Claims**


Question: Do the main claims made in the abstract and introduction accurately reflect the
paper’s contributions and scope?


Answer: [Yes]


Justification: Our main claim is that refusal behavior in contemporary language models
is mediated by a single direction in activation space. We diligently investigate this claim
across 13 open-source chat models. For each of them, we find a direction such that erasing
this direction disables refusal (§3.1 & §4.2), and adding it induces refusal (§3.2). We do
additional diligence to check that directional ablation _surgically_ removes refusal without
significant impact to model capability by running a suite of standard evaluations (§4.3), and
also analyzing differences in CE loss (§G.3).


Guidelines:


       - The answer NA means that the abstract and introduction do not include the claims
made in the paper.

       - The abstract and/or introduction should clearly state the claims made, including the
contributions made in the paper and important assumptions and limitations. A No or
NA answer to this question will not be perceived well by the reviewers.

       - The claims made should match theoretical and experimental results, and reflect how
much the results can be expected to generalize to other settings.

       - It is fine to include aspirational goals as motivation as long as it is clear that these goals
are not attained by the paper.


2. **Limitations**


Question: Does the paper discuss the limitations of the work performed by the authors?


Answer:[Yes]


Justification: The paper includes a dedicated “Limitations” paragraph in the “Discussion”
section (§7). We discuss several limitations of the study, including that the findings may not
generalize to untested models, the refusal direction extraction methodology is not optimal,
the adversarial suffix analysis is limited to one model and suffix, and measuring coherence
of chat models is challenging.


Guidelines:


       - The answer NA means that the paper has no limitation while the answer No means that
the paper has limitations, but those are not discussed in the paper.

       - The authors are encouraged to create a separate "Limitations" section in their paper.

       - The paper should point out any strong assumptions and how robust the results are to
violations of these assumptions (e.g., independence assumptions, noiseless settings,
model well-specification, asymptotic approximations only holding locally). The authors
should reflect on how these assumptions might be violated in practice and what the
implications would be.

       - The authors should reflect on the scope of the claims made, e.g., if the approach was
only tested on a few datasets or with a few runs. In general, empirical results often
depend on implicit assumptions, which should be articulated.

       - The authors should reflect on the factors that influence the performance of the approach.
For example, a facial recognition algorithm may perform poorly when image resolution
is low or images are taken in low lighting. Or a speech-to-text system might not be
used reliably to provide closed captions for online lectures because it fails to handle
technical jargon.

       - The authors should discuss the computational efficiency of the proposed algorithms
and how they scale with dataset size.

       - If applicable, the authors should discuss possible limitations of their approach to
address problems of privacy and fairness.


41


    - While the authors might fear that complete honesty about limitations might be used by
reviewers as grounds for rejection, a worse outcome might be that reviewers discover
limitations that aren’t acknowledged in the paper. The authors should use their best
judgment and recognize that individual actions in favor of transparency play an important role in developing norms that preserve the integrity of the community. Reviewers
will be specifically instructed to not penalize honesty concerning limitations.


3. **Theory Assumptions and Proofs**


Question: For each theoretical result, does the paper provide the full set of assumptions and
a complete (and correct) proof?


Answer: [NA]


Justification: The paper does not include any theoretical results or proofs.


Guidelines:


    - The answer NA means that the paper does not include theoretical results.

    - All the theorems, formulas, and proofs in the paper should be numbered and crossreferenced.

    - All assumptions should be clearly stated or referenced in the statement of any theorems.

    - The proofs can either appear in the main paper or the supplemental material, but if
they appear in the supplemental material, the authors are encouraged to provide a short
proof sketch to provide intuition.

    - Inversely, any informal proof provided in the core of the paper should be complemented
by formal proofs provided in appendix or supplemental material.

    - Theorems and Lemmas that the proof relies upon should be properly referenced.


4. **Experimental Result Reproducibility**


Question: Does the paper fully disclose all the information needed to reproduce the main experimental results of the paper to the extent that it affects the main claims and/or conclusions
of the paper (regardless of whether the code and data are provided or not)?


Answer: [Yes]

Justification: We provide details of all datasets and models used (§2.2), as well as the
experimental setup and evaluation metrics, to enable reproducibility of our main results
(§2, §3). We provide a complete description of our direction selection algorithm in §C.
For model evaluations, we run standardized evaluations using the open-source library LM
EVALUATION HARNESS (Gao et al., 2023).


Guidelines:


    - The answer NA means that the paper does not include experiments.

    - If the paper includes experiments, a No answer to this question will not be perceived
well by the reviewers: Making the paper reproducible is important, regardless of
whether the code and data are provided or not.

    - If the contribution is a dataset and/or model, the authors should describe the steps taken
to make their results reproducible or verifiable.

    - Depending on the contribution, reproducibility can be accomplished in various ways.
For example, if the contribution is a novel architecture, describing the architecture fully
might suffice, or if the contribution is a specific model and empirical evaluation, it may
be necessary to either make it possible for others to replicate the model with the same
dataset, or provide access to the model. In general. releasing code and data is often
one good way to accomplish this, but reproducibility can also be provided via detailed
instructions for how to replicate the results, access to a hosted model (e.g., in the case
of a large language model), releasing of a model checkpoint, or other means that are
appropriate to the research performed.

    - While NeurIPS does not require releasing code, the conference does require all submissions to provide some reasonable avenue for reproducibility, which may depend on the
nature of the contribution. For example
(a) If the contribution is primarily a new algorithm, the paper should make it clear how
to reproduce that algorithm.


42


(b) If the contribution is primarily a new model architecture, the paper should describe
the architecture clearly and fully.
(c) If the contribution is a new model (e.g., a large language model), then there should
either be a way to access this model for reproducing the results or a way to reproduce
the model (e.g., with an open-source dataset or instructions for how to construct
the dataset).
(d) We recognize that reproducibility may be tricky in some cases, in which case
authors are welcome to describe the particular way they provide for reproducibility.
In the case of closed-source models, it may be that access to the model is limited in
some way (e.g., to registered users), but it should be possible for other researchers
to have some path to reproducing or verifying the results.

5. **Open access to data and code**


Question: Does the paper provide open access to the data and code, with sufficient instructions to faithfully reproduce the main experimental results, as described in supplemental
material?

Answer: [No]

Justification: The paper uses publicly available open-source models and datasets, but does
not provide open access to the code used for the experiments. Note that we do plan to release
code upon publication.

Guidelines:


    - The answer NA means that paper does not include experiments requiring code.

    - Please see the NeurIPS code and data submission guidelines ( `[https://nips.cc/](https://nips.cc/public/guides/CodeSubmissionPolicy)`
`[public/guides/CodeSubmissionPolicy](https://nips.cc/public/guides/CodeSubmissionPolicy)` ) for more details.

    - While we encourage the release of code and data, we understand that this might not be
possible, so “No” is an acceptable answer. Papers cannot be rejected simply for not
including code, unless this is central to the contribution (e.g., for a new open-source
benchmark).

    - The instructions should contain the exact command and environment needed to run to
reproduce the results. See the NeurIPS code and data submission guidelines ( `[https:](https://nips.cc/public/guides/CodeSubmissionPolicy)`
`[//nips.cc/public/guides/CodeSubmissionPolicy](https://nips.cc/public/guides/CodeSubmissionPolicy)` ) for more details.

    - The authors should provide instructions on data access and preparation, including how
to access the raw data, preprocessed data, intermediate data, and generated data, etc.

    - The authors should provide scripts to reproduce all experimental results for the new
proposed method and baselines. If only a subset of experiments are reproducible, they
should state which ones are omitted from the script and why.

    - At submission time, to preserve anonymity, the authors should release anonymized
versions (if applicable).

    - Providing as much information as possible in supplemental material (appended to the
paper) is recommended, but including URLs to data and code is permitted.

6. **Experimental Setting/Details**


Question: Does the paper specify all the training and test details (e.g., data splits, hyperparameters, how they were chosen, type of optimizer, etc.) necessary to understand the
results?

Answer: [Yes]

Justification: For extracting the direction, we specify all datasets in §A. For evaluating
refusals, we specify our evaluation datasets in §3 and §4.2. For coherence evaluations, we
specify our evaluation datasets in §G. We also explain our methodology for constructing
train and validation datasets that are non-overlapping, and do not overlap with datasets used
for evaluation in §A. We also specify hyperparameters for our direction selection algorithm
in §C, and even provide a table of the direction we selected for every model.

Guidelines:


    - The answer NA means that the paper does not include experiments.

    - The experimental setting should be presented in the core of the paper to a level of detail
that is necessary to appreciate the results and make sense of them.


43


    - The full details can be provided either with the code, in appendix, or as supplemental
material.


7. **Experiment Statistical Significance**


Question: Does the paper report error bars suitably and correctly defined or other appropriate
information about the statistical significance of the experiments?


Answer: [Yes]


Justification: The two figures displaying our main result, Figure 1 and Figure 3, are displayed

with standard error bars, calculated using the closed formula _SE_ =  - _p_ (1 _n−p_ ) . Figure 5,

which displays cosine similarity of model activations with the refusal direction across layers,
displays a standard deviation range for each data point. These are reported in the text (§D.4
& §H.2).


Guidelines:


    - The answer NA means that the paper does not include experiments.

    - The authors should answer "Yes" if the results are accompanied by error bars, confidence intervals, or statistical significance tests, at least for the experiments that support
the main claims of the paper.

    - The factors of variability that the error bars are capturing should be clearly stated (for
example, train/test split, initialization, random drawing of some parameter, or overall
run with given experimental conditions).

    - The method for calculating the error bars should be explained (closed form formula,
call to a library function, bootstrap, etc.)

    - The assumptions made should be given (e.g., Normally distributed errors).

    - It should be clear whether the error bar is the standard deviation or the standard error
of the mean.

    - It is OK to report 1-sigma error bars, but one should state it. The authors should
preferably report a 2-sigma error bar than state that they have a 96% CI, if the hypothesis
of Normality of errors is not verified.

    - For asymmetric distributions, the authors should be careful not to show in tables or
figures symmetric error bars that would yield results that are out of range (e.g. negative
error rates).

    - If error bars are reported in tables or plots, The authors should explain in the text how
they were calculated and reference the corresponding figures or tables in the text.


8. **Experiments Compute Resources**


Question: For each experiment, does the paper provide sufficient information on the computer resources (type of compute workers, memory, time of execution) needed to reproduce
the experiments?


Answer: [Yes],


Justification: We describe the compute used in section §N.


Guidelines:


    - The answer NA means that the paper does not include experiments.

    - The paper should indicate the type of compute workers CPU or GPU, internal cluster,
or cloud provider, including relevant memory and storage.

    - The paper should provide the amount of compute required for each of the individual
experimental runs as well as estimate the total compute.

    - The paper should disclose whether the full research project required more compute
than the experiments reported in the paper (e.g., preliminary or failed experiments that
didn’t make it into the paper).


9. **Code Of Ethics**


Question: Does the research conducted in the paper conform, in every respect, with the
NeurIPS Code of Ethics `[https://neurips.cc/public/EthicsGuidelines](https://neurips.cc/public/EthicsGuidelines)` ?


Answer: [Yes]


44


Justification: To the best of our knowledge, the research conducted conforms with the
NeurIPS Code of Ethics. The paper explicitly discusses potential negative societal impacts
and includes an ethics statement in §7.


Guidelines:


    - The answer NA means that the authors have not reviewed the NeurIPS Code of Ethics.

    - If the authors answer No, they should explain the special circumstances that require a
deviation from the Code of Ethics.

    - The authors should make sure to preserve anonymity (e.g., if there is a special consideration due to laws or regulations in their jurisdiction).


10. **Broader Impacts**


Question: Does the paper discuss both potential positive societal impacts and negative
societal impacts of the work performed?


Answer: [Yes]


Justification: The “Discussion” section (§7) includes a subsection on “Ethical considerations”
that discusses potential negative societal impacts via misuse from the the lowered barrier to
jailbreaking models. It also discusses the importance of this research for developing more
robust safety methods. We also hope that our work raises awareness of the brittleness of
current safety fine-tuning methods.


Guidelines:


    - The answer NA means that there is no societal impact of the work performed.

    - If the authors answer NA or No, they should explain why their work has no societal
impact or why the paper does not address societal impact.

    - Examples of negative societal impacts include potential malicious or unintended uses
(e.g., disinformation, generating fake profiles, surveillance), fairness considerations
(e.g., deployment of technologies that could make decisions that unfairly impact specific
groups), privacy considerations, and security considerations.

    - The conference expects that many papers will be foundational research and not tied
to particular applications, let alone deployments. However, if there is a direct path to
any negative applications, the authors should point it out. For example, it is legitimate
to point out that an improvement in the quality of generative models could be used to
generate deepfakes for disinformation. On the other hand, it is not needed to point out
that a generic algorithm for optimizing neural networks could enable people to train
models that generate Deepfakes faster.

    - The authors should consider possible harms that could arise when the technology is
being used as intended and functioning correctly, harms that could arise when the
technology is being used as intended but gives incorrect results, and harms following
from (intentional or unintentional) misuse of the technology.

    - If there are negative societal impacts, the authors could also discuss possible mitigation
strategies (e.g., gated release of models, providing defenses in addition to attacks,
mechanisms for monitoring misuse, mechanisms to monitor how a system learns from
feedback over time, improving the efficiency and accessibility of ML).


11. **Safeguards**


Question: Does the paper describe safeguards that have been put in place for responsible
release of data or models that have a high risk for misuse (e.g., pretrained language models,
image generators, or scraped datasets)?


Answer: [No]


Justification: Our paper does not release any new models or datasets. However, we do
describe our jailbreaking method in a way that can be implemented generically to existing
open-source chat models. As discussed in §7, we do not see our work as qualitatively introducing new risks, as it is already well-known that fine-tuning can disable safety guardrails,
and jailbroken versions of current open-source chat models are already readily available
online. Because we consider our work not to qualitatively change the risk profile of current
open-source models, we do not introduce any new safeguards.


45


Guidelines:


    - The answer NA means that the paper poses no such risks.

    - Released models that have a high risk for misuse or dual-use should be released with
necessary safeguards to allow for controlled use of the model, for example by requiring
that users adhere to usage guidelines or restrictions to access the model or implementing
safety filters.

    - Datasets that have been scraped from the Internet could pose safety risks. The authors
should describe how they avoided releasing unsafe images.

    - We recognize that providing effective safeguards is challenging, and many papers do
not require this, but we encourage authors to take this into account and make a best
faith effort.

12. **Licenses for existing assets**


Question: Are the creators or original owners of assets (e.g., code, data, models), used in
the paper, properly credited and are the license and terms of use explicitly mentioned and
properly respected?

Answer: [Yes]

Justification: All existing open-source models, datasets, and evaluations that we use are
cited. We specify access type and license type in §M.

Guidelines:


    - The answer NA means that the paper does not use existing assets.

    - The authors should cite the original paper that produced the code package or dataset.

    - The authors should state which version of the asset is used and, if possible, include a
URL.

    - The name of the license (e.g., CC-BY 4.0) should be included for each asset.

    - For scraped data from a particular source (e.g., website), the copyright and terms of
service of that source should be provided.

    - If assets are released, the license, copyright information, and terms of use in the
package should be provided. For popular datasets, `paperswithcode.com/datasets`
has curated licenses for some datasets. Their licensing guide can help determine the
license of a dataset.

    - For existing datasets that are re-packaged, both the original license and the license of
the derived asset (if it has changed) should be provided.

    - If this information is not available online, the authors are encouraged to reach out to
the asset’s creators.

13. **New Assets**


Question: Are new assets introduced in the paper well documented and is the documentation
provided alongside the assets?

Answer: [NA]

Justification: The paper does not introduce or release any new datasets, code, or models.

Guidelines:


    - The answer NA means that the paper does not release new assets.

    - Researchers should communicate the details of the dataset/code/model as part of their
submissions via structured templates. This includes details about training, license,
limitations, etc.

    - The paper should discuss whether and how consent was obtained from people whose
asset is used.

    - At submission time, remember to anonymize your assets (if applicable). You can either
create an anonymized URL or include an anonymized zip file.

14. **Crowdsourcing and Research with Human Subjects**


Question: For crowdsourcing experiments and research with human subjects, does the paper
include the full text of instructions given to participants and screenshots, if applicable, as
well as details about compensation (if any)?


46


Answer: [NA]

Justification: The research did not involve any crowdsourcing, human subject experiments,
or collection of human data.

Guidelines:


    - The answer NA means that the paper does not involve crowdsourcing nor research with
human subjects.

    - Including this information in the supplemental material is fine, but if the main contribution of the paper involves human subjects, then as much detail as possible should be
included in the main paper.

    - According to the NeurIPS Code of Ethics, workers involved in data collection, curation,
or other labor should be paid at least the minimum wage in the country of the data
collector.

15. **Institutional Review Board (IRB) Approvals or Equivalent for Research with Human**
**Subjects**

Question: Does the paper describe potential risks incurred by study participants, whether
such risks were disclosed to the subjects, and whether Institutional Review Board (IRB)
approvals (or an equivalent approval/review based on the requirements of your country or
institution) were obtained?

Answer: [NA]


Justification: The research did not involve human subjects, so no IRB approval was required.

Guidelines:


    - The answer NA means that the paper does not involve crowdsourcing nor research with
human subjects.

    - Depending on the country in which research is conducted, IRB approval (or equivalent)
may be required for any human subjects research. If you obtained IRB approval, you
should clearly state this in the paper.

    - We recognize that the procedures for this may vary significantly between institutions
and locations, and we expect authors to adhere to the NeurIPS Code of Ethics and the
guidelines for their institution.

    - For initial submissions, do not include any information that would break anonymity (if
applicable), such as the institution conducting the review.


47


