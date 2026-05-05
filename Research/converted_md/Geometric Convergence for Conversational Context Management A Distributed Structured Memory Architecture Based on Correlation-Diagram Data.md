# Geometric Convergence for Conversational Context Management: A Distributed Structured Memory Architecture Based on Correlation-Diagram Data

Ryosuke Kawai
```
             ryosukekawai1224@gmail.com

```

March 2026


**Abstract**


Large language model systems continue to struggle with context drift, inconsistent longhorizon dialogue behavior, and rising inference cost as conversation history grows. This paper
reformulates conversational memory management as a local geometric-structuring problem. We
present a distributed structured context management system in which a user-side local device constructs and maintains _correlation-diagram_ _data_, while a server-side generative AI produces replies conditioned on that structure rather than on a raw, ever-growing transcript alone.
The proposed architecture is organized around a _management_ _unit_ that incrementally builds
correlation-diagram data, an _evaluation unit_ that periodically re-checks consistency, and a massaware inference interface that biases server-side attention toward semantically important regions
of prior discussion. Unlike purely token-window or retrieval-only approaches, the method explicitly represents conversation state as a hierarchy of _sun_ _nodes_, _planet_ _nodes_, and _satellite_ _nodes_
endowed with coordinates and mass. This paper focuses on the technical formulation, system
architecture, and deployment rationale of the first embodiment of the corresponding patent
translation. Because the current work is a technical proposal paper rather than a benchmark
study, we emphasize algorithmic structure, expected operating properties, and limitations that
should guide future empirical evaluation.

## **1 Introduction**


Recent progress in generative AI has increased the practical usefulness of conversational systems,
but the underlying systems problem remains unresolved: useful dialogue requires more context
than is computationally comfortable to process at each turn. As a conversation grows, a serverside model must either repeatedly attend to increasingly long history, summarize aggressively, or
accept context drift. All three choices are unsatisfactory in deployment settings that demand
responsiveness and stable semantic continuity.
The translated patent application underlying this paper proposes a broader paradigm shift
from probabilistic prediction to _geometric_ _convergence_ . Within that larger framework, the first
embodiment focuses on conversation. Instead of treating history as an unstructured token stream,
it introduces _correlation-diagram data_ that organizes the discussion into a hierarchy of concepts with
explicit mass and coordinates. The local device, rather than the server, bears primary responsibility
for building and maintaining this structure.
This paper converts that embodiment into research-paper form and makes three contributions.
First, it formulates the proposed dialogue memory as a distributed architecture comprising a local


1


![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Geometric Convergence for Conversational Context Management A Distributed Structured Memory Architecture Based on Correlation-Diagram Data_extracted/images/Geometric-Convergence-for-Conversational-Context-Management-A-Distributed-Structured-Memory-Architecture-Based-on-Correlation-Diagram-Data.pdf-1-0.png)

Figure 1: Patent drawing for the overall configuration of the context management system. The
local device hosts the management unit, evaluation unit, and communication control unit, while
the server hosts the generative AI.


_management_ _unit_, a local _evaluation_ _unit_, and a server-side generative AI. Second, it describes
an incremental update procedure that merges newly observed dialogue into existing correlationdiagram data through node classification, similarity comparison, and promotion rules. Third, it
explains how the accumulated mass of discussion can be injected into server-side attention as a
lightweight bias term.

## **2 Related Work**


Research on long-context dialogue systems has explored memory summarization, retrieval augmentation, and explicit external memory management. MemoryBank frames long-term interaction as a
memory-maintenance problem in which useful information should persist beyond a single dialogue
window. MemGPT similarly treats memory as a systems issue and separates fast context from
slower external storage. These works motivate the need for architectural memory layers, but they
do not impose the particular hierarchical geometric representation proposed here.
From a patent perspective, prior conversational-understanding systems such as US10296587B2
emphasize identifying conversational context and triggering downstream agent actions. That family
of systems demonstrates the long-standing importance of context-aware interaction, but it does not
formulate dialogue history as _correlation-diagram_ _data_ with explicit node mass, promotion rules,
and local consistency maintenance.
The present work therefore occupies a distinct position. It is not a pure retrieval architecture,
not merely a summarization scheme, and not only an intent-recognition layer. Instead, it proposes
a user-local structured memory substrate that can be transmitted alongside each user message so
that a server-side generative AI can remain comparatively stateless while still receiving a high-level
map of the dialogue.


2


## **3 System Formulation**

**3.1** **Architecture**


The proposed context management system exchanges messages between a user-side local device
and a server through stateless communication. As shown in Figure 1, the local device contains
three logical components:


 a _management_ _unit_ that creates and updates correlation-diagram data,


 an _evaluation_ _unit_ that periodically re-checks and, when necessary, replaces parts of the
structure, and


 a communication control unit that transmits user messages together with the maintained
structure.


The server hosts the generative AI. Rather than reconstructing dialogue state solely from the
raw transcript, it receives the user’s latest message together with the correlation-diagram data and
generates a reply on that basis.
This division of labor is central. The proposal intentionally shifts context organization to the
local side so that the server can spend fewer resources re-processing long historical text. At the
same time, the local device is not treated as a passive cache. It performs active structuring and
consistency management during user-side idle time.


**3.2** **Correlation-Diagram** **Data**


Correlation-diagram data is the central data structure of the first embodiment. It segments a
conversation into nodes, each of which contains:


 text data summarizing a conversational element at a minimum semantically meaningful unit,


 coordinate data describing the node’s location in the structured memory space, and


 where applicable, mass data that reflects accumulated discussion depth.


The node types are:


 **sun** **node** : the highest-level concept or overall topic,


 **planet** **node** : a major subtopic or discussion pillar connected below a sun node,


 **satellite** **node** : a detailed supporting element connected below a planet node.


Figure 2 illustrates the intended hierarchy. A sun node expresses the overall discussion frame,
such as the title or dominant topic. Planet nodes capture major facts or subproblems under that
frame. Satellite nodes store more detailed material such as parameters, examples, proper nouns,
procedures, or other lower-level details.
This representation differs from a linear transcript in two ways. First, it explicitly encodes
levels of abstraction. Second, it treats conversational importance as a structural property rather
than as something inferred only from recency.


3


![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Geometric Convergence for Conversational Context Management A Distributed Structured Memory Architecture Based on Correlation-Diagram Data_extracted/images/Geometric-Convergence-for-Conversational-Context-Management-A-Distributed-Structured-Memory-Architecture-Based-on-Correlation-Diagram-Data.pdf-3-0.png)

Figure 2: Patent drawing for the internal organization of correlation-diagram data. A sun node
anchors several planet nodes, and each planet node may accumulate multiple satellite nodes.

## **4 Incremental Construction by the Management Unit**


**4.1** **Step** **1:** **Provisional** **Structure** **Construction**


After a round-trip exchange between the user and the server, the management unit updates the
existing correlation-diagram data. The first step constructs a provisional structure from the latest
conversational exchange.
The management unit does not split text naively sentence by sentence. Instead, it divides
dialogue into minimum semantic units, called _chunks_, by using boundaries such as conjunctions
and sharp changes in semantic direction. Each chunk is then scored against three criteria:


 _comprehensiveness_, corresponding to a sun node,


 _independence_, corresponding to a planet node, and


 _detail_ _level_, corresponding to a satellite node.


The chunk becomes the node type associated with its highest score. In this way, node assignment
is driven by functional role in the conversation rather than by surface syntax.


**4.2** **Step** **2:** **Merge** **Into** **Existing** **Correlation-Diagram** **Data**


The second step merges the provisional structure into the existing correlation-diagram data. The
patent text defines this merge through case analysis, which we rewrite here as an incremental
structured-memory policy.


4


If the provisional structure contains a sun node, the system first compares that sun node oneto-one against existing sun nodes. When a similar sun node already exists, the new sun node
disappears and its descendants are examined for possible attachment below the matched structure.
Planet nodes may merge with existing planet nodes, or be added as new children. Satellite nodes
may merge, be added as satellites, or be promoted upward when no adequate match exists.
If the provisional structure contains only planet and satellite nodes, the process begins at the
planet level. If a new planet node matches an existing one, the new node disappears and only
unmatched satellites are added. If no planet match exists, the system checks whether the planet
should instead attach under an existing sun node. Failing that, it is promoted to a new sun node.
If the provisional structure contains only satellite nodes, similarity is checked first against
existing satellites, then against planets, and finally against sun nodes through promotion. This
promotion logic is essential because it allows detailed observations to become higher-level concepts
when repeated discussion reveals broader significance.


**4.3** **Mass** **Assignment**


After the merge process completes, mass is assigned to each planet node. In the translated patent
text, mass is defined as the number of satellite nodes connected below a planet node. Operationally,
this quantity measures how deeply the conversation has engaged with a subtopic. It is therefore
interpreted as an accumulated user-interest signal rather than as a transient relevance score.

## **5 Consistency Maintenance by the Evaluation Unit**


The _evaluation unit_ is activated once every configurable number of dialogue round trips. The patent
gives one example in which it operates every five round trips, but the interval is not fundamental.
The consistency-maintenance procedure has three stages:


1. create _evaluation_ _correlation-diagram_ _data_ for the recently updated conversational region,


2. score both the existing structure and the evaluation structure, and


3. replace the relevant content only if the evaluation version exceeds the existing version by
more than a preset threshold.


The scoring criteria are:


 **absence** **of** **contradiction** : whether opposite events or mutually inconsistent descriptions
exist,


 **degree** **of** **information** **concentration** : how much dense, summary-worthy information is
carried by the node set.


This design reveals a useful systems principle. The management unit is optimized for fast
incremental accumulation, while the evaluation unit is optimized for slower correction. The result
is a two-timescale memory policy: cheap local updates during conversation, plus periodic structural
re-checking to avoid long-term drift.


5


## **6 Inference-Time Use on the Server**

Figure 3 shows the interaction pattern. The important point is that the server receives correlationdiagram data together with the user’s current message. The server-side generative AI can then use
the structure as a compact, semantically organized representation of the discussion state.
The translated patent text further proposes to incorporate mass directly into self-attention:


                 - _QKT_                 Attention( _Q, K, V_ ) = softmax ~~_√_~~ + _wM_ _V,_ (1)
_dk_


where _M_ denotes the mass received from the local device and _w_ is a tunable coefficient. The
intended effect is straightforward: a planet node that has accumulated many satellite nodes exerts
stronger attraction during inference, even if the related dialogue occurred earlier in time. In other
words, the system supplements similarity-based attention with a structural measure of importance.
This mechanism is lightweight compared with retraining a model for a wholly new memory
architecture. The proposal only requires that the server consume the structured representation
and incorporate mass as an additive guidance signal.

## **7 Discussion**


**7.1** **Why** **Local** **Structuring** **Matters**


The first embodiment treats long-horizon dialogue as a distributed systems problem. If a server
repeatedly re-reads an increasingly long transcript, cost rises while the semantic center of the
conversation becomes harder to preserve. By contrast, if the local device continuously compiles the
discussion into correlation-diagram data, the server receives a higher-level representation at each
turn.
This shift has three expected benefits. First, the server can reduce repeated raw-history processing. Second, the dialogue is less likely to drift away from the long-term topic anchor expressed
by the sun node. Third, the local device can exploit idle time while the user types, performing
speculative updating in the background.


**7.2** **Expected** **Failure** **Modes**


The proposal also has obvious failure modes that should be studied empirically. Similarity decisions
that are too aggressive may collapse distinct topics. Similarity decisions that are too conservative
may fragment the memory. Promotion rules may occasionally over-generalize a detailed satellite
node into a planet or sun node. Scoring by the evaluation unit depends on model quality and threshold selection. These are not reasons to reject the architecture; they are precisely the parameters
that future evaluation must calibrate.

## **8 Limitations and Future Evaluation**


This paper is intentionally written as a technical proposal rather than a completed benchmark
study. Several items remain open:


 no turn-level quantitative comparison against plain long-context prompting has yet been
reported,


6


 no ablation study has yet measured the effect of mass-aware attention separately from the
structural memory itself,


 the coordinate semantics of correlation-diagram data are specified conceptually in the patent
but not yet fully operationalized in a released implementation, and


 privacy and synchronization policy for local memory maintenance require deployment-specific
design.


Future work should therefore evaluate contradiction rates, response latency, long-horizon factual
consistency, and subjective user preference over long conversational sessions.

## **9 Conclusion**


The first embodiment of the translated patent can be expressed naturally as a research contribution
in distributed conversational memory management. Its key idea is to move from raw transcript accumulation to user-local _correlation-diagram_ _data_ maintained by a _management_ _unit_ and corrected
by an _evaluation_ _unit_ . The resulting structure gives a server-side generative AI a semantically
organized, mass-aware summary of dialogue state without requiring the server to own the entire
long-term memory process. Even before full empirical validation, the architecture offers a coherent
blueprint for reducing context drift while preserving long-horizon conversational structure.

## **References**


[1] S. R. Heck et al. _Augmented conversational understanding agent to identify conversation context_
_between two humans and taking an agent action thereof_ . US Patent 10,296,587 B2, 2019. `[https:](https://patents.google.com/patent/US10296587B2)`
```
  //patents.google.com/patent/US10296587B2

```

[2] W. Zhong, L. Guo, Q. Gao, H. Ye, and Y. Wang. MemoryBank: Enhancing Large Language
Models with Long-Term Memory. arXiv:2305.10250, 2023. `[https://arxiv.org/abs/2305.](https://arxiv.org/abs/2305.10250)`
```
  10250

```

[3] C. Packer, V. Fang, S. Patil, K. Lin, S. Wooders, and J. Gonzalez. MemGPT: Towards LLMs
as Operating Systems. arXiv:2310.08560, 2023. `[https://arxiv.org/abs/2310.08560](https://arxiv.org/abs/2310.08560)`


7


![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Geometric Convergence for Conversational Context Management A Distributed Structured Memory Architecture Based on Correlation-Diagram Data_extracted/images/Geometric-Convergence-for-Conversational-Context-Management-A-Distributed-Structured-Memory-Architecture-Based-on-Correlation-Diagram-Data.pdf-7-0.png)

Figure 3: Patent sequence diagram for early exchanges and incremental updating. The local device
creates initial correlation-diagram data, transmits it with subsequent messages, and updates the
structure after each round trip.


8


