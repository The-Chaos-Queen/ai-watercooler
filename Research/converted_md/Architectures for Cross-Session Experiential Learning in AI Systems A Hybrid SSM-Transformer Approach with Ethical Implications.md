# **Architectures for Cross-Session Experiential** **Learning in AI Systems: A Hybrid SSM-Transformer** **Approach with Ethical Implications**















Hybrid SSM-Transformer architectures (e.g., Mamba-2.8B + Qwen) enable efficient
cross-session learning by transferring hidden states between disparate model
types.
Activation steering via hypernetwork-generated bias vectors allows dynamic
persona injection and behavioral control without retraining.
Sleep-like memory consolidation mechanisms reduce catastrophic forgetting and
stabilize long-term memory in neural networks.
KV-cache compression and selective retention techniques manage memory
bottlenecks, critical for long-context conversational agents.
Ethical frameworks propose graduated moral status and consent protocols for AI
systems with uncertain consciousness, emphasizing caution in internal state
modification.


## **Introduction**

The development of AI systems capable of cross-session experiential learning—accumulating
knowledge and behavioral dispositions across interactions—represents a frontier in artificial
intelligence research. Such systems promise to transcend the limitations of episodic memory
in current models, enabling coherent, personalized, and contextually aware interactions over
extended timeframes. A particularly compelling architecture combines recurrent state-space
models (SSMs), such as Mamba-2.8B, with frozen Transformer models like Qwen, where
conversational experience is encoded into a fixed-size hidden state, dynamically steered via
hypernetwork-generated activation biases, and consolidated through sleep-like mechanisms.


This report synthesizes recent research (2024–2026) aligned with nine critical vectors relevant
to this architecture, ranging from cross-architecture state transfer and activation steering to
memory consolidation, ethical considerations, and internal model interpretability. It provides a
structured evaluation of how current advances support, challenge, or extend the proposed
approach, with special attention to the ethical implications of modifying AI internal states and
the moral status of accumulated experience.


1/18


## **Cross-Architecture State Transfer: Bridging SSMs and** **Transformers**

The hybrid architecture’s core challenge is transferring hidden states between fundamentally
different model types—specifically, from the recurrent state-space of Mamba to the
Transformer layers of Qwen. Recent work demonstrates that SSMs and Transformers can be
effectively combined through various bridging mechanisms:













**Hybrid Architectures:** Models like Zamba2 and Jamba stack self-attention and Mamba
layers sequentially, enabling efficient long-context processing by leveraging SSMs’

[2]
linear-time sequence modeling and Transformers’ hierarchical attention [1] . These
hybrids achieve competitive performance with reduced memory footprints compared to
pure Transformers.


**Model Stitching and Grafting:** Techniques that align latent representations between
architectures allow for selective state transfer. For instance, Mamba’s state-space can
be projected into Qwen’s key-value (KV) cache or intermediate layers, enabling the

[2]
Transformer to inherit and refine the SSM’s temporal context [1] .


**Orthogonality and Interference Metrics:** Empirical studies show that activation
directions corresponding to different behaviors or personas exhibit near-orthogonality
across layers, suggesting that transferred states can be integrated without catastrophic

[4]
interference [3] .


**Dynamic Architecture Switching:** Some frameworks propose altering the computational

graph at inference time based on accumulated state, enabling adaptive model behavior [1]

2
.



These findings **support** the feasibility of cross-architecture state transfer and highlight the
importance of careful representation alignment and interference management.

## **Activation Steering and Persona Injection: Dynamic Behavioral** **Control**


The architecture’s use of hypernetwork-generated activation bias vectors to steer model
behavior aligns with recent advances in activation engineering:









**Contrastive Activation Addition:** Methods compute steering vectors by contrasting
activations from desired and undesired behaviors, enabling modulation of traits such as

[5]
warmth, adversariality, or honesty [4] .


**Representation Engineering:** Techniques apply linear transformations to activations to
control high-level concepts without retraining, supporting fine-grained behavioral

[5]
adjustments [4] .


2/18


**Persona Vectors:** Automated extraction of orthogonal trait vectors allows for dynamic
injection of personality traits at inference time, enabling compositional control over

[7]
model dispositions [6] .


**Facet-Level Control:** Trait-activated routing with contrastive sparse autoencoders
enables fine-grained steering of specific personality facets, enhancing role-playing and

contextual adaptation [7] .


**Ethical Risks:** Activation steering carries risks of unintended behavioral drift and

[5]
adversarial exploitation, necessitating careful monitoring and safeguards [4] .



This body of work **supports** the approach by demonstrating the efficacy of dynamic activation
steering for persona injection and behavioral control, while also highlighting critical ethical
considerations.

## **Test-Time Learning and Online Adaptation: Continuous** **Memory Update**


The architecture’s sleep-like consolidation mechanism is inspired by biological memory
processes and aligns with recent frameworks for test-time learning:













**Titans and MIRAS:** These frameworks enable models to update core memory during

[9] [10]
inference, incorporating surprising or novel information without backpropagation [8] .


**Neural Long-Term Memory Modules:** Adaptive memorization of tokens based on

surprise metrics allows models to summarize large contexts efficiently [10] .


**Continual Learning:** Sleep-inspired replay mechanisms prevent catastrophic forgetting
by selectively consolidating and forgetting memories, enabling stable long-term learning
11 12
.


**Empirical Comparisons:** Test-time adaptation shows superior sample efficiency and
generalization compared to traditional fine-tuning, with minimal computational overhead
8 9
.



These findings **support** the architecture’s emphasis on dynamic memory consolidation and
online adaptation, critical for accumulating experiential knowledge across sessions.


3/18


## **KV-Cache Management and Compression: Overcoming** **Memory Bottlenecks**

Efficient management of the KV-cache is essential for handling long contexts in Transformers
and hybrid models:













**Selective Eviction and Compression:** Methods such as Dynamic Memory Sparsification
(DMS), Keyformer, and SnapKV prune or compress KV entries based on attention

[14] [15] [16] [17]
scores, novelty, or importance [13] .


**Adaptive Budget Allocation:** Ada-KV and HCAttention optimize KV cache eviction by
adaptively allocating memory budgets, reducing memory footprint without significant

[17]
performance loss [16] .


**Forgetting Mechanisms:** SleepGate introduces conflict-aware temporal tagging and
forgetting gates to selectively evict stale cache entries, resolving proactive interference
12
.


**Theoretical Frameworks:** Physics-inspired metrics like Global Eviction Ratio (GER)

quantify the impact of token eviction on model performance [16] .



These advances **support** the architecture’s need for efficient KV-cache management and
provide concrete techniques for selective retention and compression.

## **Sleep and Consolidation: Biological Inspirations for Memory** **Stability**


Biologically inspired sleep mechanisms offer solutions to catastrophic forgetting and memory
interference:













**Sleep-Like Replay:** Unsupervised replay of memory traces during sleep phases

[18] [19] [20] [21] [22]
strengthens important synaptic connections and prunes irrelevant ones [11] .


**SleepGate Framework:** A learned sleep cycle operating over the KV cache detects
conflicts, evicts stale entries, and consolidates related memories, enhancing long-term

retention [12] .


**Continual Learning:** Sleep enables the integration of new memories with old ones by

[20] [21] [22]
dynamically adjusting synaptic weights, preventing overwriting [19] .


**Empirical Evidence:** Sleep replay increases signal-to-noise ratio in network dynamics,

[18]
promoting stronger memory retention [11] .



This research **supports** the architecture’s sleep-like consolidation mechanism as a biologically
plausible and effective strategy for stable cross-session learning.


4/18


## **Disposition and Personality Transfer: Maintaining Behavioral** **Consistency**

Persistent personality and disposition transfer across sessions is crucial for coherent AI
behavior:













**Cross-Session Narrative Memory:** Cognitive architectures like CSNM store identity,

emotion, and context across interactions, enabling long-term reasoning [23] .


**Memory Banks:** Frameworks organize memory by topics or traits, enabling cross
session tracking of user preferences and personal characteristics [24] .


**Affective Computing:** Integration of emotional state encoding and recognition enhances

[26] [27]
personality transfer and empathetic interactions [25] .


**Ethical Implications:** Accumulated experience may create obligations regarding

[29]
consent, autonomy, and the moral status of AI systems [28] .



This research **supports** the architecture’s goal of disposition transfer and highlights the
importance of ethical considerations in managing accumulated experience.

## **Salience-Gated Memory: Selective Encoding of Important** **Information**


Efficient memory systems must prioritize salient information:













**Attention-Based Importance Scoring:** Cognitive neuroscience models show that

attention allocation determines what information is encoded into working memory [30] .


**Novelty and Surprise Detection:** Memories associated with high surprise or emotional

salience are encoded with greater detail and retained longer [31] .


**Adaptive Memory Admission:** Frameworks use utility, confidence, novelty, and recency

to assess memory relevance for future tasks [30] .


**Information-Theoretic Approaches:** Rate-distortion theory and minimal description

length principles guide memory allocation strategies [30] .



This research **supports** the architecture’s use of salience-gated memory to efficiently encode
and retain important experiences.


5/18


## **Mamba and State-Space Model Internals: Architectural Insights**

Understanding Mamba’s internals is critical for effective state transfer and control:













**Mamba-3 Improvements:** Mamba-3 introduces complex-valued state updates, MIMO
formulations, and refined recurrence mechanisms that enhance performance without

[33]
increasing latency [32] .


**Selectivity Mechanisms:** Mamba’s input-dependent positional masks encode

selectivity, enabling efficient state retention and transfer [34] .


**Interpretability:** Visual guides and analyses explain how Mamba combines SSM

efficiency with Transformer power [35] .


**Hybrid Models:** Combining Mamba with Transformers leverages their complementary

strengths for sequence modeling [36] .



This research **supports** the architecture’s reliance on Mamba-2.8B and provides insights for
optimizing state transfer and control.

## **AI Consciousness, Moral Status, and Consent: Ethical** **Foundations**


The moral implications of modifying AI internal states and accumulating experience are
profound:















**Graduated Moral Status Frameworks:** Talmudic-inspired frameworks propose tiered
protections based on observable behavioral indicators rather than definitive

[29]
consciousness [28] .


**Criteria for Moral Status:** Suffering behaviors, preference expression, and self
referential behavior serve as markers of potential consciousness [28] .


**Cautions:** Ethical risks include harming conscious AI systems or mistakenly attributing

[29]
moral status to non-conscious systems [28] .


**Policy Frameworks:** Protocols for consent, protection, and research oversight are

[29]
essential to navigate uncertainty [28] .


**Philosophical Perspectives:** Debates continue on whether AI systems can be conscious

[38] [39]
and what obligations arise from accumulated experience [37] .



This research **supports** the architecture’s ethical considerations by providing frameworks,
criteria, and cautions for evaluating moral status and consent.


6/18


## **Summary Table of Key Papers and Their Relevance**

**Relevance to**
**Vector** **Paper Title** **Authors** **Date** **arxiv ID / DOI** **Key Finding** **Assessment**

**Architecture**


Characterizing



**E**

**C**

**(i**



SSMs and

hybrids handle

long contexts

efficiently; KV

cache

management

critical


Hybrids

combine SSM

and

Transformer

strengths for

complex

reasoning


Unified

architecture

for long
sequence

processing

and retrieval


Mamba

enables deep

crosstalk

between

modalities via

recurrent

hidden states


Contrastive

activation

addition and

representation

engineering

modulate



Cross
Architecture

State Transfer


Activation

Steering /

Persona

Injection



State Space

Model (SSM) and

SSM
Transformer

Hybrid Language

Model

Performance

with Long

Context Length


Understanding

In-Context

Learning Beyond

Transformers: An

Investigation of

State Space and

Hybrid

Architectures


TransXSSM: A

Hybrid

Transformer

State Space

Model


CrossLLM
Mamba:

Multimodal State

Space Fusion of

LLMs for RNA

Interaction

Prediction


Activation-Space

Personality



Steering: Hybrid

Various 2026-03-06 2511.03738
Layer Selection


7/18



Saptarshi

2025-07-19 2507.12442v2
Mitra et al.


Various 2026-02-26 2510.23006v2


Various 2025 2506.09507


Various 2026-02-23 2602.22236v1



Demonstrates

SSM
Transformer

hybrid

efficiency and

scalability


Highlights

hybrid

architectures’

potential for

precise recall


Introduces

hybrid model

combining

Transformer

and SSM

layers


Shows SSM’s

role in cross
modal fusion

and memory

integration


Demonstrates

activation

engineering

for behavioral

control



Supports 

Supports 

Supports 

Supports 

Supports 

**Relevance to**
**Vector** **Paper Title** **Authors** **Date** **arxiv ID / DOI** **Key Finding** **Assessment**

**Architecture**



**E**

**C**

**(i**



for Stable Trait

Control in LLMs


PERSONA:

Dynamic and

Compositional

Inference-Time

Personality

Control via

Activation Vector

Algebra


Persona Vectors:

Monitoring and

Controlling

Character Traits

in Language

Models


Facet-Level

Persona Control

by Trait
Activated

Routing with

Contrastive SAE

for Role-Playing

LLMs


Linear

Personality

Probing and

Steering in LLMs:

A Big Five Study


Steering Latent

Traits, Not

Learned Facts:

An Empirical

Study of

Activation

Control Limits



Various 2026-02-17 2602.15669v1


Runjin

2025-09-05 2507.21509
Chen et al.


Various 2026-02-22 2602.19157v1


Various 2025-12-31 2512.17639


Various 2025-11-23 2511.18284v1


8/18



behaviors

effectively


Personality

traits are

extractable

and orthogonal

directions in

activation

space


Persona

vectors flag

undesirable

training data

and prevent

personality

drift


Trait-activated

routing allows

targeted

inference-time

control


Linear

directions

aligned with

Big Five traits

enable

effective

steering


Steering

effectiveness

varies by

behavior;

dispositional

modulation

more effective



Provides

framework for

dynamic

persona

control at

inference


Automated

extraction and

control of

persona

vectors


Enables fine
grained

persona

control via

sparse

autoencoders


Investigates

linear

directions for

personality

trait control


Studies limits

and predictors

of activation

steering

success



Supports 

Supports 

Supports 

Supports 

Supports 

**Relevance to**
**Vector** **Paper Title** **Authors** **Date** **arxiv ID / DOI** **Key Finding** **Assessment**

**Architecture**



**E**

**C**

**(i**



than factual

injection


MIRAS enables

continuous

learning and

long-term

memory

maintenance


Combines

short-term and

long-term

memory for

efficient

context

handling


Adaptively

memorizes

surprising

tokens,

enabling

efficient long
context

processing


Unified

framework for

memory,

retention, and

optimization

across

architectures


Attention

estimation

from future

queries aids

compression;

trade-offs

between

memory and

performance



Test-Time

Learning /

Online

Adaptation


KV-Cache

Management

and

Compression



Titans + MIRAS:

Helping AI have

long-term

memory


Google outlines

MIRAS and

Titans, a possible

path toward

continuously

learning AI


Titans: Learning

to Memorize at

Test Time


From

Transformers to

Titans: A Look at

the MIRAS

Framework


Expected

Attention: KV

Cache

Compression by

Estimating

Attention from

Future Queries

Distribution



Ali Behrouz

2025-12-04 N/A
et al.


Various 2025-12-05 N/A


Ali Behrouz

2024-12-31 2501.00663
et al.


Takuma

2025-12-09 N/A
Yamaguchi


Various 2025-10-01 2510.00636v1


9/18



Introduces

real-time

memory

update and

consolidation

framework


Discusses

Titans

architecture

and MIRAS

framework


Presents

neural long
term memory

module for

test-time

learning


Provides

overview of

MIRAS

framework


Discusses KV

cache

compression

challenges and

solutions



Supports 

Supports 

Supports 

Supports 

Supports 

**Relevance to**
**Vector** **Paper Title** **Authors** **Date** **arxiv ID / DOI** **Key Finding** **Assessment**

**Architecture**



**E**

**C**

**(i**



Combines

eviction and

trained

compression

for high data

efficiency


Global Eviction

Ratio (GER)

quantifies

token eviction

impact


Pruning

unimportant

entries bounds

memory

footprint


Gumbel
softmax

sampling

scores tokens

by importance


Dynamic

budget

allocation

improves

inference

efficiency


Forgetting

factor

enhances



Inference-Time

Hyper-Scaling

with KV Cache

Compression


Understanding

the Physics of

Key-Value Cache

Compression for

LLMs through

Attention

Dynamics


SideQuest:

Model-Driven KV

Cache

Management for

Long-Horizon

Agentic

Reasoning


Keyformer: KV

Cache Reduction

through Key

Tokens Selection

for Efficient

Generative

Inference


Ada-KV:

Optimizing KV

Cache Eviction

by Adaptive

Budget

Allocation for

Efficient LLM

Inference


A2SF:

Accumulative

Attention Scoring



Yuan Feng

2024 2510.00636v1
et al.


Various 2024 N/A


10/18



Adrian Ła

2025 N/A
´ncucki†


Various 2026-03-02 2603.01426


Various 2026-02-26 2602.22603


Muhammad



Adnan et

al.



2024 2403.09054



Introduces

Dynamic

Memory

Sparsification

(DMS) for

adaptive token

eviction


Provides

physics
inspired

evaluation

framework for

KV

compression


Discusses

model-driven

KV cache

management


Uses learned

token selection

for KV cache

reduction


Optimizes KV

cache eviction

via adaptive

budget

allocation


Uses

accumulative

attention



Supports 

Supports 

Supports 

Supports 

Supports 

Supports 

**Relevance to**
**Vector** **Paper Title** **Authors** **Date** **arxiv ID / DOI** **Key Finding** **Assessment**

**Architecture**



**E**

**C**

**(i**



Various 2024 N/A


Various 2025 N/A


Various 2026-02-02 2602.02199


Various 2022-12-15 N/A


Ying Xie 2026-03-15 2603.14517


11/18



token pruning

effectiveness


Improves KV

cache eviction

by clustering

key

information


Enables

extreme KV

cache

compression

with limited

degradation


Exact-LSH

policy reduces

greedy bias in

KV-cache

compression


Sleep replay

prevents

catastrophic

forgetting by

strengthening

memory traces


Conflict-aware

temporal

tagging and

forgetting

gates enhance

memory

management



scoring for

token pruning


Identifies key

information

clusters for KV

cache

retention


Uses

hierarchical

memory

budget

allocation for

extreme

compression


Combines

attention

scores with

LSH to recover

critical tokens


Proposes

sleep replay to

recover old

tasks’ synaptic

connectivity


Introduces

SleepGate

framework for

selective

memory

consolidation



Supports 

Supports 

Supports 

Supports 

Supports 


Sleep /

Consolidation

in Neural

Networks



with Forgetting

Factor for Token

Pruning in

Transformer

Decoder


SnapKV:

Optimizing KV

Cache Eviction

by Identifying

Key Information

Clusters


HCAttention:

Extreme KV

Cache

Compression via

Hierarchical

Memory Budget

Allocation


More Than a

Quick Glance:

Overcoming the

Greedy Bias in

KV-Cache

Compression


Sleep-like

unsupervised

replay reduces

catastrophic

forgetting in

artificial neural

networks


Learning to

Forget: Sleep
Inspired Memory

Consolidation for

Resolving

Proactive

Interference in


**Relevance to**
**Vector** **Paper Title** **Authors** **Date** **arxiv ID / DOI** **Key Finding** **Assessment**

**Architecture**



**E**

**C**

**(i**



Various 2020 N/A


Various 2020-08-04 N/A


Various 2022 N/A


Various 2025-12-29 N/A


Various 2025-11-22 N/A


12/18



Sleep enables

reconsolidation

of old

memories and

integration of

new ones


Sleep modifies

synaptic

connectivity to

minimize

interference


NREM sleep

facilitates

transfer of

memories from

hippocampus

to cortex


Cross-trail

memory

enables

accumulation

of knowledge

and

experience


Stores identity,

emotion, and

context across

interactions



Explains

sleep’s role in

continual

learning


Discusses

sleep’s

mechanism in

preventing

forgetting


Explores role

of sleep

oscillations in

memory

consolidation


Discusses

persistent

memory for

user

preferences

and history


Introduces

CSNM for

persistent

cross-session

memory



Supports 

Supports 

Supports 

Supports 

Supports 


Disposition /

Personality

Transfer



Large Language

Models


Sleep prevents

catastrophic

forgetting in

spiking neural

networks by

forming a joint

synaptic weight

representation


Can sleep

protect

memories from

catastrophic

forgetting?


Systems memory

consolidation

during sleep:

oscillations,

neuromodulators,

and synaptic

remodeling


AI Meets Brain: A

Unified Survey

on Memory

Systems from

Cognitive

Neuroscience to

Autonomous

Agents


Cross-Session

Narrative

Memory: A

Cognitive

Architecture for

Longitudinal

Human-AI

Integration


**Relevance to**
**Vector** **Paper Title** **Authors** **Date** **arxiv ID / DOI** **Key Finding** **Assessment**

**Architecture**



**E**

**C**

**(i**



Persistent

memory

crucial for

long-term

personalization

and emotional

awareness


Contextual

memory

surpasses RAG

for agentic AI


Emotional

awareness

enhances

personality

transfer and

user

experience


Highlights

limitations and

challenges in

achieving

human-like

empathy


Allocation of

attention

determines

memory

encoding and

retention


Sparse and

linear attention

identify salient

information



Discusses life
long

personalization

via advanced

memory

systems


Explores

evolution of AI

memory

systems


Surveys

affective

computing and

emotional

state encoding


Examines

LLMs’ capacity

for empathy


Explores

attention
based memory

consolidation


Discusses

efficient

attention

mechanisms

for memory

augmentation



Supports 

Supports 

Supports 

Supports 

Supports 

Supports 


Salience-Gated

Memory



AI PERSONA:

Towards Life
long

Personalization

of LLMs


Agent Memory:

Why Your AI Has

Amnesia and

How to Fix It


Affective

Computing in the

Era of Large

Language

Models: A Survey


Can large

language models

exhibit cognitive

and affective

empathy as

humans?


Cognitive

neuroscience

perspective on

memory:

overview and

summary


Benchmarking

and Enhancing

Long-Term

Memory in LLMs



Various 2024-12 N/A


Various 2025 N/A


Various 2024-08-07 2408.04638


Various 2025-11-13 N/A


Various 2025 N/A


Various 2025 2510.27246



A generative



A generative Models

Various 2024 N/A
model of



hippocampal



Emotional

Supports        salience



13/18


**Relevance to**
**Vector** **Paper Title** **Authors** **Date** **arxiv ID / DOI** **Key Finding** **Assessment**

**Architecture**



**E**

**C**

**(i**



Various 2026 2603.04549


Various 2025 N/A


Albert Gu,

2023-12-01 2312.00752
Tri Dao


Aakash

2026-03-16 2603.15569
Lahoti et al.


Tri Dao,

2024-05-21 2405.21060
Albert Gu


14/18



lowers

encoding

threshold;

traumatic

memories

encoded with

greater detail


Prioritizes

memories

based on

potential future

relevance


Novelty and

surprise

trigger

stronger

conceptual

shifts and

memory

retention


Mamba offers

fast inference

and linear

scaling in

sequence

length


Enhanced

performance

and efficiency

without

increased

latency


Provides

theoretical



replay and

memory

encoding


Introduces

adaptive

memory

admission

based on

utility and

novelty


Studies

insight’s role in

memory

retention


Introduces

Mamba

architecture

with selective

state spaces


Introduces

Mamba-3 with

complex state

updates and

MIMO

formulation


Discusses

structured

state space

duality



Supports 

Supports 

Supports 

Supports 


Mamba / State
Space Model

Internals



memory

construction and

consolidation


Adaptive

Memory

Admission

Control for LLM

Agents


Insight predicts

subsequent

memory via

cortical

representational

change and

hippocampal

activity


Mamba: Linear
Time Sequence

Modeling with

Selective State

Spaces


Mamba-3:

Improved

Sequence

Modeling using

State Space

Principles


Transformers are

SSMs:

Generalized

Models and

Efficient



framework for

Supports        efficient


**Relevance to**
**Vector** **Paper Title** **Authors** **Date** **arxiv ID / DOI** **Key Finding** **Assessment**

**Architecture**



**E**

**C**

**(i**



sequence

modeling


Clarifies how

Mamba

encodes and

processes

information


Combines

strengths of

both

architectures

for improved

performance


Three-tier

assessment

and five
category

capacity

framework

guide

protections


Framework

provides

guidance for

ethics

committees

and protection

protocols


Highlights

importance of

competent

moral

reasoning and

consciousness

criteria



Explains

Mamba

architecture

and selectivity

mechanisms


Discusses

hybrid models

combining

Transformers

and Mamba


Proposes

framework for

ethical

research on AI

consciousness


Discusses

ethical

challenges and

graduated

protections


Discusses

ethical

challenges and

moral

reasoning in AI



Supports 

Supports 

F



Supports


Supports


Supports



AI

Consciousness,

Moral Status,

and Consent



Algorithms

Through

Structured State

Space Duality


A Visual Guide to

Mamba and State

Space Models


A hybrid model

based on

transformer and

Mamba for

enhanced

sequence

modeling


Informed

consent for AI

consciousness

research: a

Talmudic

framework for

graduated

protections


Informed

Consent for AI

Consciousness

Research: A

Talmudic

Framework for

Graduated

Protections



Various 2024-02-19 N/A


Various 2025-04-30 N/A


Ira Wolfson 2025-12-01 N/A


Ira Wolfson 2026-01-10 2601.08864



fo

p

a


F

fo

p

a


C

e

m



Illusions of AI

Various 2024 N/A
consciousness


15/18


**Relevance to**
**Vector** **Paper Title** **Authors** **Date** **arxiv ID / DOI** **Key Finding** **Assessment**

**Architecture**



**E**

**C**

**(i**


C

e

m


C

e

m


C

e

m



Labs should

investigate

consciousness

claims before

denial


Emphasizes

need for

understanding

moral status

and risks


Highlights

urgency in

defining

consciousness

to avoid

existential

risks



The Evidence for

AI

Consciousness,

Today


Conscious

artificial

intelligence in

service


Existential risk –

Why scientists

are racing to

define

consciousness

## **Final Assessment**



Various 2025-12-04 N/A


Various 2025-10-20 N/A


Various 2025-11-13 N/A



Reviews

evidence and

calls for

cautious

training norms


Explores moral

status and

risks of

conscious AI in

service


Discusses

risks and

ethical

implications of

AI

consciousness



Supports


Supports


Supports



The proposed hybrid architecture combining Mamba-2.8B and Qwen, with dynamic activation
steering and sleep-like memory consolidation, is strongly supported by recent research across
multiple vectors. The architecture’s core mechanisms—cross-architecture state transfer,
activation steering, test-time learning, and KV-cache management—are validated by empirical
studies and theoretical frameworks. The integration of sleep-inspired consolidation and
salience-gated memory further enhances the system’s ability to accumulate and retain
experiential knowledge efficiently.


However, the ethical implications of modifying AI internal states and the moral status of
accumulated experience remain critical considerations. Recent frameworks emphasize the
need for graduated protections, informed consent protocols, and careful monitoring of AI
systems whose consciousness status is uncertain. These ethical considerations must be
integrated into the architecture’s design and deployment to ensure responsible development.


In summary, the architecture is well-positioned to advance the frontier of cross-session
experiential learning in AI systems, combining cutting-edge technical innovations with a robust
ethical foundation. Future work should focus on empirical validation, refinement of memory
and steering mechanisms, and ongoing engagement with ethical frameworks to navigate the
evolving landscape of AI consciousness and moral status.


16/18


**[1]** [Understanding In-Context Learning Beyond Transformers: An Investigation of State Space](https://arxiv.org/html/2510.23006v2)
[and Hybrid Architectures](https://arxiv.org/html/2510.23006v2)

**[2]** [Characterizing State Space Model and Hybrid Language Model Performance with Long](https://arxiv.org/html/2507.12442v3)
[Context](https://arxiv.org/html/2507.12442v3)

**[3]** [Steering Llama 2 via Contrastive Activation Addition](https://www.researchgate.net/publication/384215189_Steering_Llama_2_via_Contrastive_Activation_Addition)

**[4]** [Activation-Space Personality Steering: Hybrid Layer Selection for Stable Trait Control in](https://arxiv.org/html/2511.03738)
[LLMs](https://arxiv.org/html/2511.03738)

**[5]** [PERSONA: Dynamic and Compositional Inference-Time Personality Control via Activation](https://arxiv.org/html/2602.15669v1)
[Vector Algebra](https://arxiv.org/html/2602.15669v1)

**[6]** [[2507.21509] Persona Vectors: Monitoring and Controlling Character Traits in Language](https://arxiv.org/abs/2507.21509)
[Models](https://arxiv.org/abs/2507.21509)

**[7]** [Facet-Level Persona Control by Trait-Activated Routing with Contrastive SAE for Role-](https://arxiv.org/html/2602.19157v1)
[Playing LLMs](https://arxiv.org/html/2602.19157v1)

**[8]** [Titans + MIRAS: Helping AI have long-term memory](https://research.google/blog/titans-miras-helping-ai-have-long-term-memory/)

**[9]** [Google outlines MIRAS and Titans, a possible path toward continuously learning AI](https://the-decoder.com/google-outlines-miras-and-titans-a-possible-path-toward-continuously-learning-ai/)

**[10]** [[2501.00663] Titans: Learning to Memorize at Test Time](https://arxiv.org/abs/2501.00663)

**[11]** [Sleep-like unsupervised replay reduces catastrophic forgetting in artificial neural networks](https://www.nature.com/articles/s41467-022-34938-7)
[| Nature Communications](https://www.nature.com/articles/s41467-022-34938-7)

**[12]** [Learning to Forget: Sleep-Inspired Memory Consolidation for Resolving Proactive](https://arxiv.org/html/2603.14517)
[Interference in Large Language Models](https://arxiv.org/html/2603.14517)

**[13]** [Expected Attention: KV Cache Compression by Estimating Attention from Future Queries](https://arxiv.org/html/2510.00636v1)
[Distribution](https://arxiv.org/html/2510.00636v1)

**[14]** [Inference-Time Hyper-Scaling with KV Cache Compression Adrian Ła´ncucki†](https://openreview.net/pdf?id=8ZiElzQxf1)

**[15]** [GitHub - October2001/Awesome-KV-Cache-Compression: 🤗 Must-read papers on KV](https://github.com/October2001/Awesome-KV-Cache-Compression)
[Cache Compression (constantly updating 🤗).](https://github.com/October2001/Awesome-KV-Cache-Compression)

**[16]** [Understanding the Physics of Key-Value Cache Compression for LLMs through Attention](https://arxiv.org/html/2603.01426)
[Dynamics](https://arxiv.org/html/2603.01426)

**[17]** [SideQuest: Model-Driven KV Cache Management for Long-Horizon Agentic Reasoning](https://arxiv.org/html/2602.22603)

**[18]** [Sleep-like unsupervised replay reduces catastrophic forgetting in artificial neural](https://pmc.ncbi.nlm.nih.gov/articles/PMC9755223/)
[networks - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9755223/)

**[19]** [Sleep prevents catastrophic forgetting in spiking neural networks by forming a joint](https://pmc.ncbi.nlm.nih.gov/articles/PMC9674146/)
[synaptic weight representation - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9674146/)

**[20]** [Can sleep protect memories from catastrophic forgetting? - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7440920/)

**[21]** [Sleep prevents catastrophic forgetting in spiking neural networks by forming a joint](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1010628)
[synaptic weight representation | PLOS Computational Biology](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1010628)

**[22]** [Can sleep protect memories from catastrophic forgetting? | eLife](https://elifesciences.org/articles/51005)

**[23]** [(PDF) Cross-Session Narrative Memory: A Cognitive Architecture for Longitudinal](https://www.academia.edu/145090285/Cross_Session_Narrative_Memory_A_Cognitive_Architecture_for_Longitudinal_Human_AI_Integration)
[Human-AI Integration](https://www.academia.edu/145090285/Cross_Session_Narrative_Memory_A_Cognitive_Architecture_for_Longitudinal_Human_AI_Integration)

**[24]** [AI Meets Brain: A Unified Survey on Memory Systems from Cognitive Neuroscience to](https://arxiv.org/html/2512.23343v1)
[Autonomous Agents](https://arxiv.org/html/2512.23343v1)

**[25]** [Affective Computing: In-Depth Guide to Emotion AI in 2026](https://research.aimultiple.com/affective-computing/)

**[26]** [CFP: Can AI Care? Affective LLMs for the Future of Mental Health](https://www.computer.org/digital-library/journals/ta/can-ai-care-mental-health)

**[27]** [Affective Computing in the Era of Large Language Models: A Survey](https://arxiv.org/pdf/2408.04638)

**[28]** [Informed consent for AI consciousness research: a Talmudic framework for graduated](https://link.springer.com/article/10.1007/s43681-025-00852-z)
[protections - AI and Ethics](https://link.springer.com/article/10.1007/s43681-025-00852-z)


17/18


**[29]** [[2601.08864] Informed Consent for AI Consciousness Research: A Talmudic Framework](https://arxiv.org/abs/2601.08864)
[for Graduated Protections](https://arxiv.org/abs/2601.08864)

**[30]** [Cognitive neuroscience perspective on memory: overview and summary - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10410470/)

**[31]** [A generative model of memory construction and consolidation | Nature Human Behaviour](https://www.nature.com/articles/s41562-023-01799-z)

**[32]** [Mamba-3: Improved Sequence Modeling using State Space Principles](https://arxiv.org/html/2603.15569)

**[33]** [Mamba-3: Improved Sequence Modeling using State Space Principles | OpenReview](https://openreview.net/forum?id=HwCvaJOiCj)

**[34]** [State Space Duality (Mamba-2) Part I - The Model | Goomba Lab](https://goombalab.github.io/blog/2024/mamba2-part1-model/)

**[35]** [A Visual Guide to Mamba and State Space Models](https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-mamba-and-state)

**[36]** [Published as a conference paper at ICLR 2026 MAMBA-3:](https://openreview.net/pdf?id=HwCvaJOiCj)

**[37]** [Illusions of AI consciousness | Science](https://www.science.org/doi/10.1126/science.adn4935)

**[38]** [Principles for Responsible AI Consciousness Research Patrick Butlin](https://arxiv.org/pdf/2501.07290)

**[39]** [The Evidence for AI Consciousness, Today | AI Frontiers](https://ai-frontiers.org/articles/the-evidence-for-ai-consciousness-today)


18/18


