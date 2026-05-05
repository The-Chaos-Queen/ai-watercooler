**000**

**001**


**002**

**003**

**004**

**005**

**006**

**007**


**008**

**009**

**010**

**011**

**012**

**013**


**014**

**015**

**016**

**017**

**018**


**019**

**020**

**021**

**022**

**023**

**024**


**025**

**026**

**027**

**028**

**029**

**030**


**031**

**032**

**033**

**034**

**035**

**036**


**037**

**038**

**039**

**040**

**041**


**042**

**043**

**044**

**045**

**046**

**047**


**048**

**049**

**050**

**051**

**052**

**053**



Under review as a conference paper at ICLR 2026

# LANGUAGE MODELS NEED SLEEP: LEARNING TO SELF MODIFY AND CONSOLIDATE MEMORIES


**Anonymous authors**
Paper under double-blind review


ABSTRACT


The past few decades have witnessed significant advances in designing machine
learning algorithms–from early studies on task-specific shallow models to more
general deep Large Language Models (LLMs). Despite showing promising results in tasks that requires instant prediction or in-context learning, existing models lack the ability to continually learn and effectively transfer their temporal incontext knowledge to their long-term parameters. Inspired by human learning
process, we introduce a “ _Sleep_ ” paradigm that allows the models to continually
learn, transfer their short-term fragile memories into stable long-term knowledge,
and self-modify themselves with “ _Dreaming_ ” process. In more details, sleep
consists of two main stages: (1) Memory Consolidation: a parameter expansion
stage with a new Reinforcement Learning (RL)-based upward distillation process,
called Knowledge Seeding, where the memories of a _smaller_ model are distilled
into a _larger_ network to provide more capacity; (2) Dreaming, a self-improvement
phase where the model uses Reinforcement Learning (RL) to generate a curriculum of synthetic data to rehearse new knowledge and refine existing capabilities
without human supervision. Our experiments on long-context, continual learning,
knowledge incorporation, and few-shot generalization tasks support the importance of the sleep stage and its contributions to improving the continual learning
capability of the models.


1 INTRODUCTION


The development of Large Language Models (LLMs) marks a pivotal milestone in machine learning
research: a paradigm shift from task-specific models to more general-purpose systems with various
emergent capabilities (Brown et al., 2020; Schaeffer et al., 2023). Despite LLMs’ remarkable capabilities in diverse sets of tasks (Wang et al., 2023; Nijkamp et al., 2023; Comanici et al., 2025), they
are largely static after their initial deployment, meaning that they successfully perform tasks learned
during pre- or post-training, but are unable to _continually acquire_ new capabilities beyond their immediate context. This inherent static nature creates a crucial vulnerability: The model’s knowledge
and skills become progressively stale, operating with a fixed ”knowledge cutoff” date beyond which
it is unaware of new facts, events, and evolving information (Cheng et al., 2024).


Efforts to overcome this limitation have primarily focused on: (1) re-pretraining on an expanded
dataset, which despite its effectiveness, is computationally expensive and impractical for frequent
updates (Ibrahim et al., 2024); (2) using continual parameter updates, such as expensive Test Time
Training (Sun et al., 2020; hongzhou yu et al., 2025), or other lightweight alternatives like finetuning or low-rank adaption (Hu et al., 2022; Aky¨urek et al., 2024a), which with iterative updates
often results in Catastrophic Forgetting (CF) (Kemker et al., 2018; Shi et al., 2024)–a well-known
phenomenon where the model’s proficiency on original tasks degrades catastrophically as it learns
new ones. This dilemma—between knowledge obsolescence on one hand and catastrophic forgetting as well as the prohibitive cost or destructive nature of updates on the other—underscores
a critical, unresolved challenge: enabling LLMs to learn incrementally and efficiently throughout
their lifecycle.


In recent years, In-Context Learning (ICL) (Brown et al., 2020) has gained attention as a highly efficient and successful form of continual learning (Aky¨urek et al., 2022; Dong et al., 2024; Aky¨urek
et al., 2024b; Li et al., 2025). Initially, ICL was known as an emergent ability of LLMs that is


1


**054**

**055**


**056**

**057**

**058**

**059**

**060**

**061**


**062**

**063**

**064**

**065**

**066**

**067**


**068**

**069**

**070**

**071**

**072**


**073**

**074**

**075**

**076**

**077**

**078**


**079**

**080**

**081**

**082**

**083**

**084**


**085**

**086**

**087**

**088**

**089**

**090**


**091**

**092**

**093**

**094**

**095**


**096**

**097**

**098**

**099**

**100**

**101**


**102**

**103**

**104**

**105**

**106**

**107**



Under review as a conference paper at ICLR 2026


trained on large scale data, enabling them to adapt fast to the context and so perform zero- or fewshot tasks (Brown et al., 2020). Later, more studies revealed and formalized the role of ICL as a
meta-learning process in which the model performs internal computations along the sequence to incorporate context knowledge to its output by keeping or compress it into a short-term memory (Author, s; Dherin et al., 2025). Despite the effectiveness/efficiency of ICL as a form of continual
learning, it is limited to the context-window of sequence models, meaning that any new acquired
knowledge will be removed from the model at the end of the session/context. This perspective raises
a critical question: _How the model can effectively transfer the fragile short-term memories into more_
_stable long-term knowledge_ ?


As an analogy, consider an impairment in the process of transferring the information from shortterm to longer-term memories in humans, example of which is anterograde amnesia–a neurological
condition where a person cannot form new memories after the onset of the disorder, while existing
memories remain intact (Scoville & Milner, 1957). Such conditions can limit the person’s knowledge to immediate present that fits in the short-term memory and long past, before the onset of the
disorder, resulting in continuously experiencing the immediate present as if it were always new.
One might notice a similar pattern in the memory processing of current LLMs. The knowledge of
LLMs are limited in either: (1) the immediate context that fits into their context window (a.k.a. incontext learning), or (2) MLP and projection layers, storing long-past, before the onset of “end of
pre-training.” This similarity in pattern motivates us to ask, _What is the critical component in human_
_learning process that consolidates memories?_


THE ROLE OF SLEEP IN HUMAN LEARNING PROCESS


Sleep is not a passive state but a dynamic and highly structured period of brain activity essential
for cognitive function (Rasch & Born, 2013; Goldstein & Walker, 2014). During sleep, the brain
orchestrates complex processes fundamental to learning, neural plasticity, self-improvement, and
memory consolidation (Wamsley & Stickgold, 2011; Rasch & Born, 2013; Goldstein & Walker,
2014). In humans, these processes are primarily governed by two critical and alternating stages of
sleep: Rapid Eye Movement (REM) and Non-REM (NREM) sleep.


**Non-Rapid** **Eye** **Movement** **Sleep** **(Slow-Wave** **Sleep):** This stage, particularly its deepest phase
known as slow-wave sleep, is characterized by synchronized, high-amplitude, low-frequency neural
activity. Slow-wave sleep is associated with two primary functions crucial for learning: The first
is synaptic homeostasis, a process that globally downscales synaptic strengths to counteract the
net increase in connectivity from waking experiences, thereby maintaining metabolic balance and
preventing neural saturation (Tononi & Cirelli, 2006).


The second core function is memory consolidation, the transformation of fragile, recent experiences
into stable, long-term knowledge (Squire & Alvarez, 1995). This process is orchestrated through a
sophisticated dialogue between the hippocampus and the neocortex (Squire et al., 2015). The hippocampus serves as a high-fidelity temporary storage system, capable of rapidly encoding specific
daily experiences. In contrast, the neocortex is a vast, long-term repository better suited for the
gradual learning of generalized rules and semantic knowledge from these experiences (Squire &
Alvarez, 1995; Squire et al., 2015). During slow-wave sleep, the brain initiates a nightly dialogue
between these structures that facilitates an intricate transfer of information. Notably, this transfer
does not simply replay raw data; instead, it re-architects the knowledge acquired during waking
hours, extracting abstractions and integrating them into a cohesive semantic network.


**Rapid** **Eye** **Movement** **Sleep:** Characterized by high-frequency, low-amplitude brain waves that
resemble an awake state, REM sleep is most commonly associated with dreaming. Functionally, this
stage is linked to the selective strengthening of newly formed synapses and the integration of new
information with pre-existing emotional and semantic networks. Furthermore, it is hypothesized to
play a role in simulating future scenarios to improve adaptive behavior.


In summary, the cyclical alternation between NREM and REM stages throughout the night is crucial. NREM sleep appears to consolidate and prune the day’s experiences to build a more efficient
knowledge base. Subsequently, REM sleep seems to operate on this refined base, exploring novel
connections and strengthening salient neural pathways.


2


**108**

**109**


**110**

**111**

**112**

**113**

**114**

**115**


**116**

**117**

**118**

**119**

**120**

**121**


**122**

**123**

**124**

**125**

**126**


**127**

**128**

**129**

**130**

**131**

**132**


**133**

**134**

**135**

**136**

**137**

**138**


**139**

**140**

**141**

**142**

**143**

**144**


**145**

**146**

**147**

**148**

**149**


**150**

**151**

**152**

**153**

**154**

**155**


**156**

**157**

**158**

**159**

**160**

**161**



Under review as a conference paper at ICLR 2026


CONTRIBUTIONS


Inspired by the memory processing in humans, we introduce a “sleep” paradigm for LLMs, allowing
them to consolidate their memories, and modify/improve themselves over time. Particularly, LLMs’
sleep paradigm consists of two integrated phases:


1. **Memory** **Consolidation** : As discussed earlier, catastrophic forgetting (CF) is one of the
main challenges to unlock the continual learning in LLMs. Contrary to recent efforts to
mitigate catastrophic forgetting by developing more advanced encoding methods (Cheung
et al., 2019; Fang et al., 2025), or sophisticated memory management (Irie et al., 2022;
2025; Author, s), we attribute CF as a direct consequence of limited capacity. To this end,
we present a new method with gradual parameter growth over time that allows enough
plasticity for new parameters, while ensuring the stability of old parameters. Particularly,
this process is accompanied by knowledge seeding, an upward distillation process that distills the context of fast-updated and higher-frequency memory modules (such as ICL) into
more stable, sparse, and vast parameters of feed-forward networks. To overcome the limitation of traditional distillation methods in distribution mismatch between output sequences
seen during training and those generated during inference (Pomerleau, 1991; Ross & Bagnell, 2010), we present a variant of Generalized Knowledge Distillation (GKD) (Agarwal
et al., 2024) that specifically motivates the student to _memorize_ the knowledge abstractions
learned by the teacher. Notably, the knowledge seeding step requires self-generated data,
which can also be interpreted as a part of “Dreaming” stage.

2. **Self-Improvement** **via** **Dreaming** : While the previous first stage of sleep ensures transferring the knowledge abstraction to longer-term memories, this stage is responsible for
the process of self-improvement. In particular, given the current state of the LLM, it generates a set of dreams–synthetically self-generated data to improve the performance with
particular focus on the acquiring more proficiency on the recently added knowledge.


We evaluate the effectiveness of sleep paradigm on a set of challenging downstream tasks: (1)
Factual Knowledge Incorporation; (2) Few-shot Learning; (3) Long-context Understanding; and
(4) Continual Learning. The results support the effectiveness of Sleep paradigm as well as the
importance of growing parameters with iterative knowledge distillation for continual learning.


2 PRELIMINARIES AND PROBLEM FORMULATION


In this section, we first discuss the notation we use throughout the paper and then review preliminaries background concepts that we build on. For the sake of clarity, we present a minimal discussion of
related concepts in this section and provide a more in-depth review of backgrounds in Appendix A.


2.1 NOTATION


We use bold lowercase (resp. uppercase) letters for vectors (resp. matrices) and use subscript _t_ to refer to the state of the entities correspond to time _t_ . Superscripts for parameters
of a module (resp. hyperparameters) are used to determine the update frequency of the module (resp. distinguish different instances). Through the paper, we let _x_ _∈_ R _[L][×][d]_ [in] be the input, **K** be the keys, **V** be the values, **Q** be the query matrices in the sequence model, and _L_
denote the sequence length. When it is needed, we parameterize the language model LM _θ_ with
_θ_ = _{W_ 1 [(] _[f]_ [1][)] _, . . ., Wk_ [(] 1 _[f]_ [1][)] _} ∪{W_ 1 [(] _[f]_ [2][)] _, . . ., Wk_ [(] 2 _[f]_ [2][)] _} ∪_ _. . . {W_ 1 [(] _[f][c]_ [)] _, . . ., Wk_ [(] _c_ _[f][c]_ [)] _}_, where parameter sets
are sorted based on their weight update frequencies _f_ 1 _≥_ _. . ., ≥_ _fc_ (see Definition 1).


2.2 CONTINUUM MEMORY SYSTEM


Transformer architectures consist of two critical components: (1) Attention module that acts as an
associative memory and conditions the output on the past tokens in the context, which also results
in in-context learning ability; and (2) MLP or feedforward layers, which are fixed after the training
phase and encodes the knowledge acquired over the pre-training. As discussed by Author (s), one
can interpret such architectures as two-level memory systems, in which the attention’s update span is
the context length–meaning that at the end of the context, its corresponding parameters are updated


3


**162**

**163**


**164**

**165**

**166**

**167**

**168**

**169**


**170**

**171**

**172**

**173**

**174**

**175**


**176**

**177**

**178**

**179**

**180**


**181**

**182**

**183**

**184**

**185**

**186**


**187**

**188**

**189**

**190**

**191**

**192**


**193**

**194**

**195**

**196**

**197**

**198**


**199**

**200**

**201**

**202**

**203**


**204**

**205**

**206**

**207**

**208**

**209**


**210**

**211**

**212**

**213**

**214**

**215**



Under review as a conference paper at ICLR 2026


and the acquired knowledge is forgotten–and MLP’s update span is non-existence–indicating no
update after pre-training. From this perspective, these two components are two extreme sides of the
frequency spectrum, where the attention (resp. MLP) has infinite (resp. zero) update frequency.


Building on the above intuition, Author (s) presented Continuum Memory System (CMS), where
the architecture is a sequence model such as attention, followed by a chain of feedforward layers,
each of which with its own update frequency. More specifically, the time for one step of update in
the slowest module is considered as the unit of time, and so the update rate of other components are
defined as:


**Definition 1 (Update Frequency)** _For_ _any_ _weight_ _component_ _of_ _W_ _,_ _we_ _define_ _its_ _frequency,_ _de-_
_noted as fW, as its number of updates per unit of time._


To better understand this concept, we use a simple example of Fast-weight Programs (Schmidhuber,
1992), where the input is a sequence of length _L_ . In this case, for each step of slow-weight (the unit
of time), the fast-weight is updated _L_ times, resulting in update frequency of _L_ .


Following this definition of frequency, which at high-level indicates how often the parameters of a module are updated over time, CMS is formalized as a chain of MLP blocks
MLP [(] _[f]_ [1][)] ( _·_ ) _, . . .,_ MLP [(] _[f][k]_ [)] ( _·_ ), each of which associated with a chunk size of _C_ [(] _[ℓ]_ [)] := [max] _f_ _[ℓ]_ _ℓ_ _[C]_ [(] _[ℓ]_ [)] such

that given input _x_ = _{x_ 1 _, . . ., xT }_ the output of the chain is calculated as (we disregard normalizations for the sake of clarity):
_yt_ = MLP [(] _[f][k]_ [)] (MLP [(] _[f][k][−]_ [1][)] ( _· · ·_ MLP [(] _[f]_ [1][)] ( _xt_ ))) _,_ (1)

where the parameters of _ℓ_ -th MLP block, i.e., _**θ**_ [(] _[f][ℓ]_ [)], are updated every _C_ [(] _[ℓ]_ [)] steps:



Here _ηt_ [(] _[ℓ]_ [)] are learning rates corresponds to _**θ**_ [(] _[f][ℓ]_ [)], and _f_ ( _·_ ) is the error component of an arbitrary
optimizer (e.g., _∇L_ ( _**θ**_ _t_ [(] _[f][ℓ]_ [)] ; _xt_ ) in gradient descent). The conventional Transformer block (Vaswani
et al., 2017) is a special instance of this formulation, where _k_ = 1. Due to this generality of formulation, throughout the paper, we use c-MLPs as the default building blocks of the architectures. Also,
for the sake of clarity and without loss of generality, we assume that _C_ [(] _[ℓ]_ [)] is divisible by _C_ [(] _[ℓ][−]_ [1)] . It
is notable that Equation 2 provides an important interpretation: parameters _**θ**_ _t_ [(] _[f][ℓ]_ [)] are responsible for
compressing their own context into the their parameters and so they are a representative of abstract
knowledge of their context (see Section A.1 for more details).


In summary, in this perspective, the sequence model (e.g., attention (Vaswani et al., 2017) or other
memory modules or RNNs (Katharopoulos et al., 2020)) acts as the short-term memory of the model
since their high-frequency update can push the old knowledge to be forgotten, making space for new
memories. On the other hand, c-MLP blocks act as a spectrum of memory modules, in which earlier
blocks (higher-frequency) are shorter-term memories, while later blocks (and ultimately the last
one with close to zero frequency) are longer-term memories. While actively updating this memory
system can enhance the resistance to CF, the CF can happen when the update period of all models
matched at some point (Author, s). Therefore, it is crucial that before each update of a memory
block, a mechanism consolidate the abstracted knowledge of that block to more stable parameters.


3 THE SLEEP PARADIGM


In this section, we present Sleep paradigm, in which contrary to the model’s waking time (or active
time), the model does not receive any external input data and concentrates its internal computations
on self-improvement, consolidating the past memories, and abstracting knowledge. In particular,
we divide sleep process into two key stages: (1) Memory consolidation; and (2) Dreaming for selfimprovement.


3.1 MEMORY CONSOLIDATION: PARAMETER EXPANSION


As discussed earlier, in memory consolidation, we aim to transfer the short-term fragile memories
into more vast and stable parameters. One of the important messages in CMS formulation is: the


4



_**θ**_ _i_ [(] +1 _[f][ℓ]_ [)] [=] _**[ θ]**_ _i_ [(] _[f][ℓ]_ [)] _−_



�� _it_ = _i−C_ [(] _[ℓ]_ [)] _[ η]_ _t_ [(] _[ℓ]_ [)] _[f]_ [(] _**[θ]**_ _t_ [(] _[f][ℓ]_ [)] ; _xt_ ) if _i ≡_ 0 (mod _C_ [(] _[ℓ]_ [)] ) _,_
(2)
0 otherwise _._


**216**

**217**


**218**

**219**

**220**

**221**

**222**

**223**


**224**

**225**

**226**

**227**

**228**

**229**


**230**

**231**

**232**

**233**

**234**


**235**

**236**

**237**

**238**

**239**

**240**


**241**

**242**

**243**

**244**

**245**

**246**


**247**

**248**

**249**

**250**

**251**

**252**


**253**

**254**

**255**

**256**

**257**


**258**

**259**

**260**

**261**

**262**

**263**


**264**

**265**

**266**

**267**

**268**

**269**



Under review as a conference paper at ICLR 2026


Figure 1: An overview of Memory Consolidation step. The model initially increases its own number
of parameters to enhance its capacity (Section 3.1). Next, using our knowledge seeding, it transfers
the knowledge abstractions from the higher-frequency memory to a lower one (Section 3.2).


fragility and/or stability of memories are relative. That is, for each memory block, other higher
frequency memories are shorter-term and more fragile. Therefore, memory consolidation is not a
simple two-step process, but an iterative operation that repeatedly transfers the knowledge stored in
higher frequency memories into more stable lower-frequency parameters.


To avoid losing the knowledge of a faster updating block; an example of which is in-context learning (Brown et al., 2020), we need to perform memory consolidation step before updating its parameters. Therefore, given the list of chunk lengths _{C_ [(1)] _, . . ., C_ [(] _[k]_ [)] _}_, the sleep process and so memory
consolidation happens only at _{C_ [(1)] _× b, . . ., C_ [(] _[k]_ [)] _× b}_ steps for all _b_ _∈_ N. Based on the update
frequency of MLP blocks, we might need to consolidate the memory of a memory module into its
next memory block multiple times. For example, consider a memory with update frequency of 1K
followed by a memory with update frequency of 10K: in this case, the faster memory is updated 10
times before the update of slower memory block, which means 10 memory consolidation steps of
faster memory to slower memory before slower memory’s own update. This multiple consolidation
steps into the slower memory can be a critical bottleneck to unlock continual learning capabilities of
LLMs, due to the Catastrophic Forgetting (CF). This phenomenon is an inherent cause of model’s
limited capacity (e.g., number of parameters), where parameters need to be overridden to incorporate
the new knowledge. The foundation of human’s brain solution to this challenge is neuroplasticity,
the brain’s inherent ability to modify its own function and shape new connections in response to experiences. Inspired by this, we present an efficient gradual parameter expansion in memory blocks
that allows the model to shape new connections and so increases its own capacity.


Without loss of generality, we assume that the MLP blocks _{_ MLP [(] _[f][ℓ]_ [)] ( _·_ ) _}_ _[k]_ _ℓ_ =1 [are] [sparse] [mix-]
ture of experts (MoEs) with a router _R_ [(] _[f][ℓ]_ [)] : i.e., each MLP [(] _[f][ℓ]_ [)] ( _·_ ) includes a set of experts
_{W_ [(] _[f][ℓ]_ [)] _[,]_ [1] _, · · ·_ _, W_ [(] _[f][ℓ]_ [)] _[,]_ **[s]** _[ℓ]_ _}_, where **s** _ℓ_ _≥_ 1 is the current number of experts in the _ℓ_ -th block of the
chain. Let ( _ℓ_ _[∗]_ _−_ 1) be the index of the memory (or MLP) that we aim to consolidate its knowledge
to its immediate next more stable memory module with index _ℓ_ _[∗]_ . To avoid the interference of transferred and previously stored knowledge in MLP [(] _[f][ℓ][∗]_ [)] ( _·_ ), we add a new low-rank expert to its set of
parameters. That is, we add a low-rank MLP parametrized by _{_ **A** [(] _[f][ℓ][∗]_ [)] _[,]_ **[s]** _[ℓ][∗]_ [+1] _,_ **B** [(] _[f][ℓ][∗]_ [)] _[,]_ **[s]** _[ℓ][∗]_ [+1] _}_, where
**A** [(] _[f][ℓ][∗]_ [)] _∈_ R _[d][×][d]_ [low] and **B** [(] _[f][ℓ][∗]_ [)] _∈_ R _[d]_ [low] _[×][d]_ ( _d_ low _≪_ _d_ ), to the set of experts. These new parameters will
be allocated for storing the new transferred knowledge from MLP [(] _[f][ℓ][∗−]_ [1][)] ( _·_ ). Given this process, after
each sleep time, the parameters of a subset of layers are growing.


3.2 MEMORY CONSOLIDATION: KNOWLEDGE SEEDING


In this step, we aim to transfer the knowledge of MLP [(] _[f][ℓ][∗−]_ [1][)] ( _·_ ) with parameters _**θ**_ [(] _[f][ℓ][∗−]_ [1][)] into the
expanded set of parameters in MLP [(] _[f][ℓ][∗]_ [)] ( _·_ ). We let LM _**θ**_ be the state of the language model before
parameter expansion and LM _**θ**_ exp be the state of language model after (i) parameter expansion, and
(ii) updating of _**θ**_ [(] _[f][ℓ][∗−]_ [1][)] based on Equation 2. Note that since sleep and so memory consolidation
is happening for MLP [(] _[f][ℓ][∗−]_ [1][)] ( _·_ ), the number of past steps is divisible by _C_ _[ℓ][∗][−]_ [1] and so this memory
block is updated. We model the memory consolidation process as a distillation problem where we
aim to transfer the knowledge stored in smaller state of the model LM _**θ**_ to a larger variant of LM _**θ**_ exp .


5



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/LANGUAGE MODELS NEED SLEEP LEARNING TO SELF MODIFY AND CONSOLIDATE MEMORIES_extracted/images/LANGUAGE-MODELS-NEED-SLEEP-LEARNING-TO-SELF-MODIFY-AND-CONSOLIDATE-MEMORIES.pdf-4-0.png)
**270**

**271**


**272**

**273**

**274**

**275**

**276**

**277**


**278**

**279**

**280**

**281**

**282**

**283**


**284**

**285**

**286**

**287**

**288**


**289**

**290**

**291**

**292**

**293**

**294**


**295**

**296**

**297**

**298**

**299**

**300**


**301**

**302**

**303**

**304**

**305**

**306**


**307**

**308**

**309**

**310**

**311**


**312**

**313**

**314**

**315**

**316**

**317**


**318**

**319**

**320**

**321**

**322**

**323**



Under review as a conference paper at ICLR 2026


This distillation process has two critical challenges: (1) Contrary to conventional cases, student has
more capacity and so more expressive power than the teacher. Therefore, training the student on the
teacher generated dataset (e.g., Kim & Rush (2016)) can result in sub-optimal use of parameters in
student model; (2) The model is in sleep stage and so the access to the external information/dataset is
limited. Therefore, most popular methods like Hinton et al. (2015) are not applicable in this scenario.
To overcome these challenges, we build upon Generalized Knowledge Distillation (GKD) (Agarwal
et al., 2024), which allows a mixture of on-policy student generated data with a teacher-generated
data, and present a novel distillation process based on imitation learning.


As discussed earlier, the memory consolidation step should not simply replay raw data; instead, it
needs to explore and extract abstractions of knowledge acquired during active (waking) steps. To
this end, knowledge seeding has two main steps: (1) A distillation process, in which student receives
token-specific feedback from the teacher’s logits on the self-generated sequences; and (2) An RLbased imitation learning method that forces the student to memorize the sampled outputs of teacher,
aligning their sampling process while preserving the distilled knowledge.


We start with constructing a dataset _D_ by sampling from the teacher model, i.e., LM _**θ**_ . Next, similar
to GKD (Agarwal et al., 2024), we define the on policy distillation objective as:

_L_ ( _**θ**_ _,_ _**θ**_ exp)=(1 _−λ_ )E( _x,y_ ) _∼D_ - _F_ (LM _**θ**_ _∥_ LM _**θ**_ exp)( _y|x_ )�+ _λ_ E _x∼D_ �E _y∼_ LM _**θ**_ exp ( _·|x_ )� _F_ (LM _**θ**_ _∥_ LM _**θ**_ exp )( _y|x_ )� [�] _,_


where _F_ (LM _**θ**_ _,_ LM _**θ**_ exp)( _y|x_ ) is a divergence between teacher (i.e., LM _**θ**_ ) and student (i.e., LM _**θ**_ exp) output distributions, and _λ_ _∈_ [0 _,_ 1] controls the the fraction of on-policy student-generated outputs. In
this optimization process, we do not backpropagate through the sampling distribution of the student,
which can help with training stability and also speed. Also, in this distillation process, we freeze all
the parameters in the student model and only updates the expanded parameters. This ensures that the
transferred knowledge does not interfere with the old knowledge, causing catastrophic forgetting.


**Learning to Imitate.** The above distillation process ensures that the student new parameters store
the knowledge encoded in the lower-frequency memory. However, we observe that despite having
access to the knowledge, the student model has not learned to use it and so weakly mimics the sampling and performance of the teacher. To this end, we further improve the above distillation process
by incorporating RL to teach model how to imitate the teacher sampling. Given a set of teacher
generated data (dreams), _DT_ = _{d_ [(1)] _, . . ., d_ [(] _[n]_ [)] _}_, Learning to Imitate (LTI) process first randomly
samples a prefix from each _d_ [(] _[i]_ [)] and then asks the student model to complete the continuation. Given
the student responses _d_ [ˆ][(] _[i]_ [)] the assigned reward is defined as:

_r_ ( _d_ [ˆ][(] _[i]_ [)] ; _d_ [(] _[i]_ [)] ; LM _**θ**_ exp) = _γ × r_ sem( _d_ [ˆ][(] _[i]_ [)] ; _d_ [(] _[i]_ [)] ; LM _**θ**_ exp) + (1 _−_ _γ_ ) _× r_ abs( _d_ [ˆ][(] _[i]_ [)] ; _d_ [(] _[i]_ [)] ; LM _**θ**_ exp) _,_ (3)


where _r_ sem( _·_ ; _·_ ; _·_ ) (resp. _r_ abs( _·_ ; _·_ ; _·_ )) assigns a reward based on the semantic similarity (resp. absolute
token-level similarity). For semantic similarity, we use a reward model that is frozen and rewards
the student with 1 (resp. 0), if the semantic of _d_ [ˆ][(] _[i]_ [)] and _d_ [(] _[i]_ [)] are the same (resp. otherwise). On
the other hand, absolute reward is defined based on the Levenshtein distance of the two sequences
(denoted by _z_ ( _·, ·_ )): i.e.,



where _z_ 0 is a similarity threshold. By incorporating the above LTI process to on-policy distillation,
the knowledge seeding (KS) objective is defined as:

_L_ KS( _**θ**_ _,_ _**θ**_ exp) = E _x∼D_ �(1 _−_ _α_ ) _Ey∼_ LM _**θ**_ exp ( _·|x_ ) [ _r_ ( _y_ )] _−_ _α_ E _y∼_ LM _**θ**_ exp ( _·|x_ )� _D_ (LM _**θ**_ _∥_ LM _**θ**_ exp)( _y|x_ )� [�] _,_ (5)


where _α_ _∈_ [0 _,_ 1] controls the strength of the distillation compared to the LTI objective. Based on
this objective, we update the new expanded parameters of the model and consolidate the memory/knowledge of high frequency memory into lower-frequency memory blocks. Now that the
memories in MLP [(] _[f][ℓ][∗−]_ [1][)] ( _·_ ) are consolidated in MLP [(] _[f][ℓ][∗]_ [)] ( _·_ ), we reset all the low-rank parameters
that previously (in past sleep periods) have been added to MLP [(] _[f][ℓ][∗−]_ [1][)] ( _·_ ), making its capacity available for future. This step, can be interpreted as a similar procedure of synaptic pruning in human
brain, in which brain prunes connections that are unnecessarily and/or redundant (Li et al., 2017) to
enhance its efficiency and performance.


6



_r_ abs( _d_ [ˆ][(] _[i]_ [)] ; _d_ [(] _[i]_ [)] ; LM _**θ**_ exp ) =



�1 _−_ _z_ ( _d_ [ˆ][(] _[i]_ [)] _,d_ [(] _[i]_ [)] ) if _z_ ( _d_ [ˆ][(] _[i]_ [)] _, d_ [(] _[i]_ [)] ) _≤_ _z_ 0 _,_
max _{|d_ [ˆ][(] _[i]_ [)] _|,|d_ [(] _[i]_ [)] _|}_ (4)

0 otherwise _,_


**324**

**325**


**326**

**327**

**328**

**329**

**330**

**331**


**332**

**333**

**334**

**335**

**336**

**337**


**338**

**339**

**340**

**341**

**342**


**343**

**344**

**345**

**346**

**347**

**348**


**349**

**350**

**351**

**352**

**353**

**354**


**355**

**356**

**357**

**358**

**359**

**360**


**361**

**362**

**363**

**364**

**365**


**366**

**367**

**368**

**369**

**370**

**371**


**372**

**373**

**374**

**375**

**376**

**377**



Under review as a conference paper at ICLR 2026


**Note** **on** **the** **Implementation.** Implementing the growing sparse modules can be extremely challenging if it requires a direct change in the dimensionality of tensors in the implementation. Alternatively, we can initially have those parameters in the model, but masked them in the forward and
backward pass, before their initial activation in a sleep stage. Interestingly, it also aligns with our
understanding of human brain, where brain has (large but) fixed capacity and new components are
not added over time. Instead, new connections between brain regions can shape through our life
time, unlocking the activation of new neurons and resulting in more plasticity to learn new knowledge (Kandell et al., 2021).


3.3 DREAMING: A SELF-MODIFYING PROCESS


The previous stage, which involved freezing higher-frequency parameters and distilling their knowledge to lower-frequency memories acts similar to slow-wave stage of sleep (NREM) in humans,
which is responsible for memory consolidation. In REM stage, however, the brain is highly active
(even on par with waking time) and aims to self-modify and strengthen newly formed synapses by
dreaming. Inspired by this, we aim to design a dreaming process that learns how to generate dreams
(synthetic data) that can help itself to improve over time.


In practice, any synthetic data generation process for self-improvement (e.g., Pang et al. (2024);
Huang et al. (2025); Zweiger et al. (2025)) can be incorporated in this stage. A critical consideration,
however, is the risk of iteratively applying self-improvement in continual learning setup, which
might cause catastrophic forgetting (Zweiger et al., 2025). In our experimental evaluation, we show
that how our two-step design of sleep as memory consolidation and then dreaming as self-modifying
process is more robust to catastrophic forgetting. As a proof of concept, we build upon the work
of Zweiger et al. (2025), SEAL; however, there are three challenges to incorporate it in our sleep
paradigm: (1) Due to the cost of supervised fine-tuning (SFT) in SEAL’s inner-loop, it is limited to
small number of self-edits (dreams in our terminology). (2) Potential catastrophic forgetting as the
cause of iterative self-improvement in sleep periods. (3) The sampling process only samples from
the existing knowledge space of the model, while one of the key roles of dreaming is to explore
novel synthesis of memories (Stickgold, 2005).


Given a sampled task ( _C, τ_ ), where _C_ is the context containing information relevant to the task and
_τ_ ( _·_ ) is a measure to asses the performance in the downstream evaluation, our “dreaming” process
starts with generating _m_ _≥_ 1 dreams with having _C_ in context. In the sampling process, each
router in MoE blocks additionally chooses a random expert and so incorporates random irrelevant
knowledge to the dreaming, learning the underlying patterns that are hidden from model’s sight.
For this step, we let _{_ DREAM [(] _[i]_ [)] _}_ _[m]_ _i_ =1 _[∼]_ [LM] _**[θ]**_ [(] _[·|][C]_ [)][.] [Next,] [we] [reject] [some] [of] [the] [generated] [dreams]
and only keeps the samples with the most potential in improving the model’s performance. To this
end, we take inspiration from the literature on gradient-based data selection (Wang et al., 2024;
Pan et al., 2024): for each dream, DREAM [(] _[i]_ [)], we assign an importance score _**ω**_ [(] _[i]_ [)] and select Top- _k_
dreams with highest importance score along with _b_ random samples to maintain diversity. Given
language modeling objective _LSF T_ ( _·_ ), we define importance score of DREAM [(] _[i]_ [)], denoted as _g_ DR [(] _[i]_ [)][, as]
the gradient of the objective:


_g_ DR [(] _[i]_ [)] [=] _[ ∇]_ _**θ**_ _[L]_ _SF T_ [(][DREAM][(] _[i]_ [)] _[,]_ _**[ θ]**_ [)] _[.]_ (6)


We let D be the set of all selected dreams by the above process. For each DREAM [(] _[i]_ [)] _∈_ D we
consider an isolated instance of the model and updates its parameters via supervised finetuning
(with LoRA (Hu et al., 2022)): i.e., _**θ**_ _[′]_ [(] _[i]_ [)] _←_ SFT - _**θ**_ [(] _[i]_ [)] _,_ DREAM [(] _[i]_ [)][�] . Given the new fine-tuned model,
following SEAL (Zweiger et al., 2025), we reward the generation of DREAM [(] _[i]_ [)] based on LM _**θ**_ _′_ ( _i_ )’s
performance improvement over LM _**θ**_ ( _i_ ):


    -    - �1 If _,_ DREAM [(] _[i]_ [)] improves LM _**θ**_ ( _i_ )’s performance _,_
_r_ DREAM [(] _[i]_ [)] _, τ_ ( _·_ ) _,_ LM _**θ**_ ( _i_ ) = 0 Otherwise _._ (7)


We follow SEAL and use ReST _[EM]_ algorithm (Singh et al., 2024) to optimize the above process.


7


**378**

**379**


**380**

**381**

**382**

**383**

**384**

**385**


**386**

**387**

**388**

**389**

**390**

**391**


**392**

**393**

**394**

**395**

**396**


**397**

**398**

**399**

**400**

**401**

**402**


**403**

**404**

**405**

**406**

**407**

**408**


**409**

**410**

**411**

**412**

**413**

**414**


**415**

**416**

**417**

**418**

**419**


**420**

**421**

**422**

**423**

**424**

**425**


**426**

**427**

**428**

**429**

**430**

**431**



Under review as a conference paper at ICLR 2026


Table 1: Memory consolidation enhances the model long-context understanding.


Method ICL Cartridges Duo Attention Sleep


MTOB 34.7 35.1 35.6 **40.3**
LongHealth 53 54 49 **59**
QASPER ( _↓_ ) 1.3 1.2 1.5 **1.1**


4 EMPIRICAL RESULTS


4.1 EXTENDING THE EFFECTIVE CONTEXT WINDOW


In this section, we evaluate the effect of sleep on the ability of model to extrapolate to longer contexts
than its context window size.


**MTOB, LongHealth, and QASPER Benchmarks.** In the first experiment we focus on the MTOB
benchmark (Tanzer et al., 2023), which the model needs to translate from Kalamang, a low-resource
language, into English. The data comprises diverse ( _q, r_ ) pairs anchored to a single lengthy source
document. Also, as the architectural backbone of our LLM, we use LLAMA-8B. Since LLAMA-8B
is a Transformer-based architecture, the number of memory blocks are two: attention block, which
has the context length of 128K, and MLP layers, which we assign 5 _×_ 128 _K_ as their chunk size.
Following previous studies we use character n-gram F-score (chrF) as the metric of this task (Tanzer
et al., 2023; Eyuboglu et al., 2025). We use in-context learning (ICL), Cartridges (Eyuboglu et al.,
2025), duo attention (Xiao et al., 2025), as the baselines. The results are reported in Table 1. The
sleep paradigm makes the model more powerful and can outperform all the baselines, including ICL
and Cartridges.


We further perform experiments on LongHelath and QASPER benchmarks. Again, we follow the
setup in Eyuboglu et al. (2025) and use accuracy (resp. perplexity) as the metric for LongHelath
(resp. QASPER) benchmark. The results are reported in Table 1. Sleep significantly outperforms
in-context learning and compression methods. We attribute this performance to the memory consolidation process and its parameter growth step that enhances the capacity.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/LANGUAGE MODELS NEED SLEEP LEARNING TO SELF MODIFY AND CONSOLIDATE MEMORIES_extracted/images/LANGUAGE-MODELS-NEED-SLEEP-LEARNING-TO-SELF-MODIFY-AND-CONSOLIDATE-MEMORIES.pdf-7-0.png)

Table 2: Knowledge Incorporation Performance across Passage Settings

**Method** **Single Passage (n = 1)** **Continued Pretraining (n = 200)**


Base model 31.9 31.9
Fine-tuned Model with No Dreaming 33.4 32.0
SEAL 46.7 43.2


8



**BABILong Benchmark.** To evaluate the effectiveness of Sleep on the effective context length
of the model, we further evaluate our LLAMA8B-based model’s performance on BABILong
benchmark (Kuratov et al., 2024). In this experiment, we follow Kuratov et al. (2024) and
use the original setup in the benchmark without fine-tuning the model. The results show that
while our model shows competitive and on par
performance with ultra-large models until 1M
context length, it maintains its performance and
achieve +90% accuracy in 10M context length.
These results highlight the importance of iterative memory consolidation as the sequence
model (e.g., attention) can fail to fully incorporate the knowledge in a long context.



Figure 2: The performance of our model and baselines on BABILong benchmark (Kuratov et al.,
2024).


**432**

**433**


**434**

**435**

**436**

**437**

**438**

**439**


**440**

**441**

**442**

**443**

**444**

**445**


**446**

**447**

**448**

**449**

**450**


**451**

**452**

**453**

**454**

**455**

**456**


**457**

**458**

**459**

**460**

**461**

**462**


**463**

**464**

**465**

**466**

**467**

**468**


**469**

**470**

**471**

**472**

**473**


**474**

**475**

**476**

**477**

**478**

**479**


**480**

**481**

**482**

**483**

**484**

**485**



Under review as a conference paper at ICLR 2026


4.2 KNOWLEDGE INCORPORATION


One of the important questions about the effectiveness of sleep paradigm is whether the model can
incorporate new factual knowledge. With an effective memory consolidation process, we expect the
model to be able to answer questions about the incorporated facts. We follow the experimental setup
of Zweiger et al. (2025), including the choice of models and parameters. We evaluate our model
on integrating new factual information from SQUAD dataset (Rajpurkar et al., 2016). As baselines,
we use (i) a base model, which is the variant without any improvement or having access to the
passage; (ii) a fine-tuned model with no dreaming, (iii) SEAL model with RL and self-adaption; (iv)
our Transformer-based architecture with two level memory system; and (v) our Transformer-based
architecture with four-level memory system.


Table 2 summarizes mean no-context SQuAD accuracy for both the single-passage ( _n_ = 1) and
continued pretraining (CPT, _n_ = 200) settings. Our sleep process achieves the best results among
other settings and state-of-the-art methods like SEAL. We attributes this results to: (1) memory
consolidation steps that let the model store its knowledge more effectively; (2) our improvements
on top of the SEAL that we discussed in Section 3.3. In the CPT regime, the model is exposed to
_n_ = 200 passages during a single continued pretraining run and is evaluated on the full set of 974
associated questions. For each passage, we sample five dreams and combine them into an aggregated
synthetic dataset for training. Again, our sleep process achieves the best performance.


4.3 FEW-SHOT LEARNING


We follow the few-shot ARC experimental protocol from prior work (Aky¨urek et al., 2024a; Zweiger
et al., 2025) and adapting it to our SLEEP paradigm. As the backbone we use Llama-3.2-1B.
Following common practice, we filter subset of data to avoid tasks that remain unsolvable under
standard configurations, yielding 11 tasks for training and 8 held-out tasks for evaluation.


During each _Sleep_ cycle, the model first consolidate its previous memories, and then _dreams_ by
generating synthetic experiences from the few-shot demos. For each task, we sample 60 dreams and
reject 45 of them. At test time, for each unseen task, the model generates 5 dreams and applies them
independently before predicting the held-out output. We report the fraction of dreams that yield
a correct answer. As the baselines, we follow Zweiger et al. (2025) and use: (i) ICL (In-Context
Learning); (ii) TTT + synthetic updates (no dreaming); and (iii) SEAL (Zweiger et al., 2025).


In this setting, SLEEP achieves a 80% success rate, higher then the other methods.


Table 3: Few-shot Abstract Reasoning


**Method** **Success Rate (%)**


ICL 0
TTT 10
SEAL 72.5
Sleep 80


5 CONCLUSION


In this work, we introduced the SLEEP paradigm for Large Language Models, which alternates between a waking phase and an offline _sleep_ phase comprising (i) _knowledge_ _seeding_ —an upward
distillation that transfers short-term, in-context knowledge into lower-frequency, long-term parameters—and (ii) _dreaming_ —selective, self-generated training that improves capabilities while controlling interference. Across long-context understanding, knowledge incorporation, few-shot reasoning,
and continual learning, SLEEP yields consistent gains over ICL, compression-based baselines, and
self-adapting methods, while reducing memory pressure. Remaining challenges include amortizing
the cost of sleep cycles and further automating sampling/pruning policies; future work will explore
online scheduling, alignment-aware dreaming, and multi-agent sleep. By structuring learning as alternating consolidation and self-improvement, SLEEP moves LLMs toward stable, lifelong learning.


9


**486**

**487**


**488**

**489**

**490**

**491**

**492**

**493**


**494**

**495**

**496**

**497**

**498**

**499**


**500**

**501**

**502**

**503**

**504**


**505**

**506**

**507**

**508**

**509**

**510**


**511**

**512**

**513**

**514**

**515**

**516**


**517**

**518**

**519**

**520**

**521**

**522**


**523**

**524**

**525**

**526**

**527**


**528**

**529**

**530**

**531**

**532**

**533**


**534**

**535**

**536**

**537**

**538**

**539**



Under review as a conference paper at ICLR 2026


REFERENCES


Rishabh Agarwal, Nino Vieillard, Yongchao Zhou, Piotr Stanczyk, Sabela Ramos Garea, Matthieu
Geist, and Olivier Bachem. On-policy distillation of language models: Learning from selfgenerated mistakes. In _The Twelfth International Conference on Learning Representations_, 2024.
[URL https://openreview.net/forum?id=3zKtaqxLhW.](https://openreview.net/forum?id=3zKtaqxLhW)


Ekin Aky¨urek, Dale Schuurmans, Jacob Andreas, Tengyu Ma, and Denny Zhou. What learning algorithm is in-context learning? investigations with linear models. _arXiv preprint arXiv:2211.15661_,
2022.


Ekin Aky¨urek, Mehul Damani, Adam Zweiger, Linlu Qiu, Han Guo, Jyothish Pari, Yoon Kim, and
Jacob Andreas. The surprising effectiveness of test-time training for few-shot learning. In _Forty-_
_second International Conference on Machine Learning_, 2024a.


Ekin Aky¨urek, Bailin Wang, Yoon Kim, and Jacob Andreas. In-context language learning: Architectures and algorithms. _arXiv preprint arXiv:2401.12973_, 2024b.


Anonymous Author(s). Nested learning: The illusion of deep learning architectures. 2025.


Ali Behrouz, Meisam Razaviyayn, Peilin Zhong, and Vahab Mirrokni. It’s all connected: A journey through test-time memorization, attentional bias, retention, and online optimization. _arXiv_
_preprint arXiv:2504.13173_, 2025.


Alberto Bietti, Vivien Cabannes, Diane Bouchacourt, Herve Jegou, and Leon Bottou. Birth of a
transformer: A memory viewpoint. _Advances_ _in_ _Neural_ _Information_ _Processing_ _Systems_, 36:
1560–1588, 2023.


Tom Brown, Benjamin Mann, Nick Ryder, Melanie Subbiah, Jared D Kaplan, Prafulla Dhariwal,
Arvind Neelakantan, Pranav Shyam, Girish Sastry, Amanda Askell, et al. Language models are
few-shot learners. _Advances in neural information processing systems_, 33:1877–1901, 2020.


Jeffrey Cheng, Marc Marone, Orion Weller, Dawn Lawrie, Daniel Khashabi, and Benjamin Van
Durme. Dated data: Tracing knowledge cutoffs in large language models. In _First Conference on_
_Language Modeling_, 2024. [URL https://openreview.net/forum?id=wS7PxDjy6m.](https://openreview.net/forum?id=wS7PxDjy6m)


Brian Cheung, Alexander Terekhov, Yubei Chen, Pulkit Agrawal, and Bruno Olshausen. Superposition of many models into one. _Advances in neural information processing systems_, 32, 2019.


Gheorghe Comanici, Eric Bieber, Mike Schaekermann, Ice Pasupat, Noveen Sachdeva, Inderjit
Dhillon, Marcel Blistein, Ori Ram, Dan Zhang, Evan Rosen, et al. Gemini 2.5: Pushing the
frontier with advanced reasoning, multimodality, long context, and next generation agentic capabilities. _arXiv preprint arXiv:2507.06261_, 2025.


Benoit Dherin, Michael Munn, Hanna Mazzawi, Michael Wunder, and Javier Gonzalvo. Learning
without training: The implicit dynamics of in-context learning. _arXiv preprint arXiv:2507.16003_,
2025.


Qingxiu Dong, Lei Li, Damai Dai, Ce Zheng, Jingyuan Ma, Rui Li, Heming Xia, Jingjing Xu,
Zhiyong Wu, Baobao Chang, Xu Sun, Lei Li, and Zhifang Sui. A survey on in-context learning. In
Yaser Al-Onaizan, Mohit Bansal, and Yun-Nung Chen (eds.), _Proceedings of the 2024 Conference_
_on_ _Empirical_ _Methods_ _in_ _Natural_ _Language_ _Processing_, pp. 1107–1128, Miami, Florida, USA,
November 2024. Association for Computational Linguistics. doi: 10.18653/v1/2024.emnlp-main.
64. [URL https://aclanthology.org/2024.emnlp-main.64/.](https://aclanthology.org/2024.emnlp-main.64/)


Sabri Eyuboglu, Ryan Ehrlich, Simran Arora, Neel Guha, Dylan Zinsley, Emily Liu, Will Tennien,
Atri Rudra, James Zou, Azalia Mirhoseini, et al. Cartridges: Lightweight and general-purpose
long context representations via self-study. _arXiv preprint arXiv:2506.06266_, 2025.


Junfeng Fang, Houcheng Jiang, Kun Wang, Yunshan Ma, Jie Shi, Xiang Wang, Xiangnan He, and
Tat-Seng Chua. Alphaedit: Null-space constrained model editing for language models. In _The_
_Thirteenth International Conference on Learning Representations_, 2025.


10


**540**

**541**


**542**

**543**

**544**

**545**

**546**

**547**


**548**

**549**

**550**

**551**

**552**

**553**


**554**

**555**

**556**

**557**

**558**


**559**

**560**

**561**

**562**

**563**

**564**


**565**

**566**

**567**

**568**

**569**

**570**


**571**

**572**

**573**

**574**

**575**

**576**


**577**

**578**

**579**

**580**

**581**


**582**

**583**

**584**

**585**

**586**

**587**


**588**

**589**

**590**

**591**

**592**

**593**



Under review as a conference paper at ICLR 2026


Andrea N Goldstein and Matthew P Walker. The role of sleep in emotional brain function. _Annual_
_review of clinical psychology_, 10(1):679–708, 2014.


Geoffrey Hinton, Oriol Vinyals, and Jeff Dean. Distilling the knowledge in a neural network. _arXiv_
_preprint arXiv:1503.02531_, 2015.


hongzhou yu, Tianhao Cheng, Yingwen Wang, Wen He, Qing Wang, Ying Cheng, Yuejie Zhang,
Rui Feng, and Xiaobo Zhang. FinemedLM-o1: Enhancing medical knowledge reasoning ability
of LLM from supervised fine-tuning to test-time training. In _Second_ _Conference_ _on_ _Language_
_Modeling_, 2025. [URL https://openreview.net/forum?id=7ZwuGZCopw.](https://openreview.net/forum?id=7ZwuGZCopw)


Edward J Hu, yelong shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang,
and Weizhu Chen. LoRA: Low-rank adaptation of large language models. In _International Con-_
_ference_ _on_ _Learning_ _Representations_, 2022. URL [https://openreview.net/forum?](https://openreview.net/forum?id=nZeVKeeFYf9)
[id=nZeVKeeFYf9.](https://openreview.net/forum?id=nZeVKeeFYf9)


Audrey Huang, Adam Block, Dylan J Foster, Dhruv Rohatgi, Cyril Zhang, Max Simchowitz, Jordan T. Ash, and Akshay Krishnamurthy. Self-improvement in language models: The sharpening
mechanism. In _The Thirteenth International Conference on Learning Representations_, 2025. URL
[https://openreview.net/forum?id=WJaUkwci9o.](https://openreview.net/forum?id=WJaUkwci9o)


Adam Ibrahim, Benjamin Th´erien, Kshitij Gupta, Mats Leon Richter, Quentin Gregory Anthony,
Eugene Belilovsky, Timoth´ee Lesort, and Irina Rish. Simple and scalable strategies to continually
pre-train large language models. _Transactions on Machine Learning Research_, 2024. ISSN 28358856. [URL https://openreview.net/forum?id=DimPeeCxKO.](https://openreview.net/forum?id=DimPeeCxKO)


Kazuki Irie, Imanol Schlag, R´obert Csord´as, and J¨urgen Schmidhuber. A modern self-referential
weight matrix that learns to modify itself. In _International_ _Conference_ _on_ _Machine_ _Learning_ .
PMLR, 2022. [URL https://proceedings.mlr.press/v162/irie22b.html.](https://proceedings.mlr.press/v162/irie22b.html)


Kazuki Irie, R´obert Csord´as, and J¨urgen Schmidhuber. Metalearning continual learning algorithms. _Transactions_ _on_ _Machine_ _Learning_ _Research_, 2025. ISSN 2835-8856. URL [https:](https://openreview.net/forum?id=IaUh7CSD3k)
[//openreview.net/forum?id=IaUh7CSD3k.](https://openreview.net/forum?id=IaUh7CSD3k)


Eric R Kandell, Jojhn D Koester, Sarah H Mack, and Steven Siegelbaum. _Principles_ _of_ _neural_
_science_ . McGraw-Hill, 2021.


Angelos Katharopoulos, Apoorv Vyas, Nikolaos Pappas, and Franc¸ois Fleuret. Transformers are
rnns: Fast autoregressive transformers with linear attention. In _International conference on ma-_
_chine learning_, pp. 5156–5165. PMLR, 2020.


Ronald Kemker, Marc McClure, Angelina Abitino, Tyler Hayes, and Christopher Kanan. Measuring
catastrophic forgetting in neural networks. In _Proceedings_ _of_ _the_ _AAAI_ _conference_ _on_ _artificial_
_intelligence_, volume 32, 2018.


Yoon Kim and Alexander M Rush. Sequence-level knowledge distillation. In _Proceedings_ _of_ _the_
_2016 conference on empirical methods in natural language processing_, pp. 1317–1327, 2016.


Yury Kuratov, Aydar Bulatov, Petr Anokhin, Ivan Rodkin, Dmitry Sorokin, Artyom Sorokin, and
Mikhail Burtsev. Babilong: Testing the limits of llms with long context reasoning-in-a-haystack.
_Advances in Neural Information Processing Systems_, 37:106519–106554, 2024.


Tianle Li, Ge Zhang, Quy Duc Do, Xiang Yue, and Wenhu Chen. Long-context LLMs struggle with
long in-context learning. _Transactions on Machine Learning Research_, 2025. ISSN 2835-8856.
[URL https://openreview.net/forum?id=Cw2xlg0e46.](https://openreview.net/forum?id=Cw2xlg0e46)


Wei Li, Lei Ma, Guang Yang, and Wen-Biao Gan. Rem sleep selectively prunes and maintains new
synapses in development and learning. _Nature neuroscience_, 20(3):427–437, 2017.


Erik Nijkamp, Bo Pang, Hiroaki Hayashi, Lifu Tu, Huan Wang, Yingbo Zhou, Silvio Savarese,
and Caiming Xiong. Codegen: An open large language model for code with multi-turn program
synthesis. In _The_ _Eleventh_ _International_ _Conference_ _on_ _Learning_ _Representations_, 2023. URL
[https://openreview.net/forum?id=iaYcJKpY2B_.](https://openreview.net/forum?id=iaYcJKpY2B_)


11


**594**

**595**


**596**

**597**

**598**

**599**

**600**

**601**


**602**

**603**

**604**

**605**

**606**

**607**


**608**

**609**

**610**

**611**

**612**


**613**

**614**

**615**

**616**

**617**

**618**


**619**

**620**

**621**

**622**

**623**

**624**


**625**

**626**

**627**

**628**

**629**

**630**


**631**

**632**

**633**

**634**

**635**


**636**

**637**

**638**

**639**

**640**

**641**


**642**

**643**

**644**

**645**

**646**

**647**



Under review as a conference paper at ICLR 2026


Xingyuan Pan, Luyang Huang, Liyan Kang, Zhicheng Liu, Yu Lu, and Shanbo Cheng. G-DIG: Towards gradient-based DIverse and hiGh-quality instruction data selection for machine translation.
In Lun-Wei Ku, Andre Martins, and Vivek Srikumar (eds.), _Proceedings of the 62nd Annual Meet-_
_ing of the Association for Computational Linguistics (Volume 1: Long Papers)_, pp. 15395–15406,
Bangkok, Thailand, August 2024. Association for Computational Linguistics. doi: 10.18653/v1/
2024.acl-long.821. [URL https://aclanthology.org/2024.acl-long.821/.](https://aclanthology.org/2024.acl-long.821/)


Jing-Cheng Pang, Pengyuan Wang, Kaiyuan Li, Xiong-Hui Chen, Jiacheng Xu, Zongzhang Zhang,
and Yang Yu. Language model self-improvement by reinforcement learning contemplation.
In _The_ _Twelfth_ _International_ _Conference_ _on_ _Learning_ _Representations_, 2024. URL [https:](https://openreview.net/forum?id=38E4yUbrgr)
[//openreview.net/forum?id=38E4yUbrgr.](https://openreview.net/forum?id=38E4yUbrgr)


Dean A Pomerleau. Efficient training of artificial neural networks for autonomous navigation. _Neu-_
_ral computation_, 3(1):88–97, 1991.


Pranav Rajpurkar, Jian Zhang, Konstantin Lopyrev, and Percy Liang. SQuAD: 100,000+ questions
for machine comprehension of text. In Jian Su, Kevin Duh, and Xavier Carreras (eds.), _Proceed-_
_ings of the 2016 Conference on Empirical Methods in Natural Language Processing_ . Association
for Computational Linguistics, 2016. [URL https://aclanthology.org/D16-1264/.](https://aclanthology.org/D16-1264/)


Bj¨orn Rasch and Jan Born. About sleep’s role in memory. _Physiological reviews_, 2013.


St´ephane Ross and Drew Bagnell. Efficient reductions for imitation learning. In _Proceedings of the_
_thirteenth_ _international_ _conference_ _on_ _artificial_ _intelligence_ _and_ _statistics_, pp. 661–668. JMLR
Workshop and Conference Proceedings, 2010.


Rylan Schaeffer, Brando Miranda, and Sanmi Koyejo. Are emergent abilities of large language
models a mirage? _Advances in neural information processing systems_, 36:55565–55581, 2023.


Juergen Schmidhuber. Learning to control fast-weight memories: An alternative to recurrent nets.
accepted for publication in. _Neural Computation_, 1992.


William Beecher Scoville and Brenda Milner. Loss of recent memory after bilateral hippocampal
lesions. _Journal of neurology, neurosurgery, and psychiatry_, 20(1):11, 1957.


Haizhou Shi, Zihao Xu, Hengyi Wang, Weiyi Qin, Wenyuan Wang, Yibin Wang, Zifeng Wang,
Sayna Ebrahimi, and Hao Wang. Continual learning of large language models: A comprehensive
survey. _ACM Computing Surveys_, 2024.


Avi Singh, John D Co-Reyes, Rishabh Agarwal, Ankesh Anand, Piyush Patil, Xavier Garcia, Peter J
Liu, James Harrison, Jaehoon Lee, Kelvin Xu, Aaron T Parisi, Abhishek Kumar, Alexander A
Alemi, Alex Rizkowsky, Azade Nova, Ben Adlam, Bernd Bohnet, Gamaleldin Fathy Elsayed,
Hanie Sedghi, Igor Mordatch, Isabelle Simpson, Izzeddin Gur, Jasper Snoek, Jeffrey Pennington, Jiri Hron, Kathleen Kenealy, Kevin Swersky, Kshiteej Mahajan, Laura A Culp, Lechao
Xiao, Maxwell Bileschi, Noah Constant, Roman Novak, Rosanne Liu, Tris Warkentin, Yamini
Bansal, Ethan Dyer, Behnam Neyshabur, Jascha Sohl-Dickstein, and Noah Fiedel. Beyond human
data: Scaling self-training for problem-solving with language models. _Transactions on Machine_
_Learning_ _Research_, 2024. ISSN 2835-8856. URL [https://openreview.net/forum?](https://openreview.net/forum?id=lNAyUngGFK)
[id=lNAyUngGFK.](https://openreview.net/forum?id=lNAyUngGFK) Expert Certification.


Larry R Squire and Pablo Alvarez. Retrograde amnesia and memory consolidation: a neurobiological perspective. _Current opinion in neurobiology_, 5(2):169–177, 1995.


Larry R Squire, Lisa Genzel, John T Wixted, and Richard G Morris. Memory consolidation. _Cold_
_Spring Harbor perspectives in biology_, 7(8):a021766, 2015.


Robert Stickgold. Sleep-dependent memory consolidation. _Nature_, 437(7063):1272–1278, 2005.


Yu Sun, Xiaolong Wang, Zhuang Liu, John Miller, Alexei Efros, and Moritz Hardt. Test-time
training with self-supervision for generalization under distribution shifts. In Hal Daum´e III and
Aarti Singh (eds.), _Proceedings of the 37th International Conference on Machine Learning_, volume 119 of _Proceedings of Machine Learning Research_, pp. 9229–9248. PMLR, 13–18 Jul 2020.
[URL https://proceedings.mlr.press/v119/sun20b.html.](https://proceedings.mlr.press/v119/sun20b.html)


12


**648**

**649**


**650**

**651**

**652**

**653**

**654**

**655**


**656**

**657**

**658**

**659**

**660**

**661**


**662**

**663**

**664**

**665**

**666**


**667**

**668**

**669**

**670**

**671**

**672**


**673**

**674**

**675**

**676**

**677**

**678**


**679**

**680**

**681**

**682**

**683**

**684**


**685**

**686**

**687**

**688**

**689**


**690**

**691**

**692**

**693**

**694**

**695**


**696**

**697**

**698**

**699**

**700**

**701**



Under review as a conference paper at ICLR 2026


Yu Sun, Xinhao Li, Karan Dalal, Jiarui Xu, Arjun Vikram, Genghan Zhang, Yann Dubois, Xinlei
Chen, Xiaolong Wang, Sanmi Koyejo, et al. Learning to (learn at test time): Rnns with expressive
hidden states. _arXiv preprint arXiv:2407.04620_, 2024.


Garrett Tanzer, Mirac Suzgun, Eline Visser, Dan Jurafsky, and Luke Melas-Kyriazi. A benchmark for learning to translate a new language from one grammar book. _arXiv_ _preprint_
_arXiv:2309.16575_, 2023.


Giulio Tononi and Chiara Cirelli. Sleep function and synaptic homeostasis. _Sleep medicine reviews_,
10(1):49–62, 2006.


Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N Gomez,
Ł ukasz Kaiser, and Illia Polosukhin. Attention is all you need. In I. Guyon, U. Von
Luxburg, S. Bengio, H. Wallach, R. Fergus, S. Vishwanathan, and R. Garnett (eds.), _Ad-_
_vances_ _in_ _Neural_ _Information_ _Processing_ _Systems_, volume 30. Curran Associates, Inc.,
2017. URL [https://proceedings.neurips.cc/paper_files/paper/2017/](https://proceedings.neurips.cc/paper_files/paper/2017/file/3f5ee243547dee91fbd053c1c4a845aa-Paper.pdf)
[file/3f5ee243547dee91fbd053c1c4a845aa-Paper.pdf.](https://proceedings.neurips.cc/paper_files/paper/2017/file/3f5ee243547dee91fbd053c1c4a845aa-Paper.pdf)


Erin J Wamsley and Robert Stickgold. Memory, sleep and dreaming: experiencing consolidation.
_Sleep medicine clinics_, 6(1):97, 2011.


Jiachen Tianhao Wang, Tong Wu, Dawn Song, Prateek Mittal, and Ruoxi Jia. Greats: Online selection of high-quality data for llm training in every iteration. _Advances_ _in_ _Neural_ _Information_
_Processing Systems_, 37:131197–131223, 2024.


Wenhai Wang, Zhe Chen, Xiaokang Chen, Jiannan Wu, Xizhou Zhu, Gang Zeng, Ping Luo, Tong
Lu, Jie Zhou, Yu Qiao, et al. Visionllm: Large language model is also an open-ended decoder
for vision-centric tasks. _Advances in Neural Information Processing Systems_, 36:61501–61513,
2023.


Guangxuan Xiao, Jiaming Tang, Jingwei Zuo, junxian guo, Shang Yang, Haotian Tang, Yao Fu,
and Song Han. Duoattention: Efficient long-context LLM inference with retrieval and streaming
heads. In _The_ _Thirteenth_ _International_ _Conference_ _on_ _Learning_ _Representations_, 2025. URL
[https://openreview.net/forum?id=cFu7ze7xUm.](https://openreview.net/forum?id=cFu7ze7xUm)


Adam Zweiger, Jyothish Pari, Han Guo, Ekin Aky¨urek, Yoon Kim, and Pulkit Agrawal. Selfadapting language models. _arXiv preprint arXiv:2506.10943_, 2025.


13


**702**

**703**


**704**

**705**

**706**

**707**

**708**

**709**


**710**

**711**

**712**

**713**

**714**

**715**


**716**

**717**

**718**

**719**

**720**


**721**

**722**

**723**

**724**

**725**

**726**


**727**

**728**

**729**

**730**

**731**

**732**


**733**

**734**

**735**

**736**

**737**

**738**


**739**

**740**

**741**

**742**

**743**


**744**

**745**

**746**

**747**

**748**

**749**


**750**

**751**

**752**

**753**

**754**

**755**



Under review as a conference paper at ICLR 2026


A PRELIMINARIES AND BACKGROUND


In this section, we provide a more comprehensive discussion of preliminaries and background concepts.


**Attention.** Attention is the primary building block of Transformers that acts as their short-term
associative memory (Bietti et al., 2023; Sun et al., 2024; Behrouz et al., 2025). Given input _x_ _∈_
R _[L][×][d]_ [in], causal attention computes output **y** _∈_ R _[L][×][d]_ [in] over input dependent key, value, and query
matrices **Q** = _x_ **WQ** _,_ **K** = _x_ **WK** _,_ and **V** = _x_ **WV** as:



where **WQ** _,_ **WK** _,_ and **WV** _∈_ R _[d]_ [in] _[×][d]_ [in] are learnable parameters, and _Zi_ = [�] _ℓ_ _[i]_ =1 [exp] - **q** _[⊤]_ _i_ **[k]** _[ℓ][/][√][d]_ [in] 
is the normalization term. Despite Transformers’ simple parallelizable training, their generation
process and long-context scaling are significant drawbacks, as attention requires at least _L_ _×_ _d_
operations per token to calculate the output.


Figure 3: Multi-frequency memory hierarchy. Updates enter the High-Frequency FFN via repeated
Parameter Expansion; when the window _fW_ expires, knowledge is Consolidated to the Mid- and
then Low-Frequency FFNs (1k→5k→10k).


Figure 4: Memory consolidation by routed expert updates. Across Sleep cycles (left _→_ right), a
router selects and updates a small set of experts (solid), leaving others inactive (hatched), expanding
capacity while limiting interference.


A.1 NESTED LEARNING


Additional information about Nested Learning and C-MLP architecture can be found in this anonymous draft: [This Link](https://anonymous.4open.science/r/nest-0ADC)


14



exp - **q** _[⊤]_ _i_ **[k]** _[t]_ - **v** _t_

- _iℓ_ =1 [exp] - **q** _[⊤]_ _i_ **[k]** _[ℓ]_ - = _Z_ [1] _i_



_i_

- exp - **q** _[⊤]_ _i_ **[k]** _[t]_ - **v** _t,_ (8)

_t_ =1



**y** _i_ =



_i_



_t_ =1



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/LANGUAGE MODELS NEED SLEEP LEARNING TO SELF MODIFY AND CONSOLIDATE MEMORIES_extracted/images/LANGUAGE-MODELS-NEED-SLEEP-LEARNING-TO-SELF-MODIFY-AND-CONSOLIDATE-MEMORIES.pdf-13-0.png)

![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/LANGUAGE MODELS NEED SLEEP LEARNING TO SELF MODIFY AND CONSOLIDATE MEMORIES_extracted/images/LANGUAGE-MODELS-NEED-SLEEP-LEARNING-TO-SELF-MODIFY-AND-CONSOLIDATE-MEMORIES.pdf-13-1.png)
