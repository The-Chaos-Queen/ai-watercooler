# Autobiographical Memory Scaffolding for Persistent AI Selves in MoCoP

## Executive Summary

MoCoP’s next layer beyond D2 cue-based recall should implement an **autobiographical self-memory system** rather than a better transcript index. This layer should: (a) organize memories in a **hierarchical, life-story-like structure** (lifetime periods → general events/routines → event-specific episodes); (b) distinguish **episodic vs. semantic autobiographical vs. conceptual self** knowledge; (c) support **conceptual vs. perceptual recall modes** with different behavior for recent vs. remote memories; and (d) explicitly encode **people, places, routines, tensions, and confidence** as first-class relational objects.[^1][^2][^3]

Concretely, MoCoP should add a **scaffolding layer** sitting between raw traces and cue-based retrieval that:

- Maintains a **self-memory system (SMS)**-like hierarchy of autobiographical knowledge (lifetime periods, general events, event-specific knowledge) constrained by a “working self” of current goals and identity commitments.[^2][^3][^1]
- Represents **people, roles, and relational schemas** as relational memory nodes, with history of interactions, affect, trust, and unresolved tensions.[^4][^5]
- Tracks **temporal structure** via life periods, narrative windows around salient anchors, and recency/remote gradients, with different recall policies for recent vs. remote events.[^6][^7][^2]
- Encodes **scene and context** (places, situations, routines) as scaffolds for reconstructing events, not as verbatim frames.[^8][^9][^10]
- Supports **two recall modes**—conceptual/gist and perceptual/detail—implemented as different abstraction levels over the same event graph, and allows uncertainty, partial recall, and distortion.[^11][^3]

This design shifts MoCoP from “retrieve matching snippet” toward **reconstructive, relational, confidence-weighted remembering** that supports identity continuity and person-specific grounding.


## Key Literature Findings (Design-Relevant Only)

### 1. Self-Memory System and Hierarchical Autobiographical Structure

- The **Self-Memory System (SMS)** posits that autobiographical memory consists of a **hierarchical autobiographical knowledge base** plus a **working self** that constrains retrieval by current goals, self-images, and values.[^3][^12][^2]
- Autobiographical knowledge is organized at three main levels:
  - **Lifetime periods**: extended phases with themes and roles (e.g., “early PhD years”, “building the house”).
  - **General events**: repeated or extended events/routines (e.g., “bedtime with the kids”, “weekly project sync”).
  - **Event-specific knowledge**: single episodes anchored in time, place, and subjective experience.[^12][^2][^3]
- Episodic details are **both encoded and accessed through this hierarchy**: retrieval typically starts from high-level self-concepts or periods, activates relevant general events, and then drills down to specific episodes; conversely, repeated episodes consolidate upward into scripts and semanticized summaries.[^13][^2][^3]
- **Working self**: a dynamic system of current goals, plans, and self-images that filters what is encoded, which cues are used, and how reconstruction is biased; it enforces **coherence between memory and identity**, including adaptive distortions (e.g., self-enhancing or consistency biases).[^14][^15][^16]

**Design implication:** MoCoP needs an explicit **multi-level autobiographical graph** and a “working self” control state that modulates encoding, selection, and reconstruction, rather than a flat store of past utterances.


### 2. Episodic → Semantic Transformation and Recent vs. Remote Memory

- Systems consolidation theories and multiple-trace/trace-transformation accounts show that over time, memories tend to **lose fine episodic detail and become more semantic, schematic, and gist-like**, though some richly detailed memories can remain episodic indefinitely.[^17][^11][^13]
- fMRI and lesion work along the **hippocampal long axis** shows a gradient: posterior hippocampus and posterior medial network support **fine-grained, perceptual, contextual details**, while anterior hippocampus and anterior temporal/medial prefrontal areas support **coarse, conceptual, schematic representations**.[^18][^11][^3]
- Recent autobiographical memories show stronger hippocampal and posterior network engagement; some data support **time-limited hippocampal involvement** for typical autobiographical memories, while other work suggests detailed episodic traces remain hippocampus-dependent when they preserve vividness (supporting multiple-trace views).[^19][^17][^6]
- Behavioral work shows that **remote autobiographical memory often preserves semanticized personal facts and generic events** while specific episodic details decline, with disease-specific gradients (e.g., Alzheimer’s vs. semantic dementia).[^20][^21][^22]

**Design implication:** MoCoP should implement **time-dependent abstraction policies**: recent memories accessible with high perceptual detail; older memories primarily accessible as semanticized/gist event summaries, with optional deeper reconstruction attempts using whatever fragments remain.


### 3. Conceptual vs. Perceptual Forms of Remembering

- Sheldon et al. (2019) argue that episodic autobiographical events can be reconstructed in at least two distinct forms:
  - **Conceptual remembering**: emphasizes thematic, schematic, and evaluative aspects (what the event *meant*, what was learned, how it fits into life narrative).
  - **Perceptual remembering**: emphasizes sensory, spatial, and contextual details (what was *seen/heard/felt*, exact setting, sequence).[^3]
- Autobiographical events appear to store **perceptual and conceptual details in partially separable systems**, and retrieval can selectively weight one or the other depending on goals.[^3]
- Neural evidence: distinct but interacting default-network subsystems and hippocampal segments underpin these modes (anterior hippocampus + dorsal-medial subsystem for conceptual; posterior hippocampus + medial-temporal subsystem for perceptual).[^3]
- Functional differences: **conceptual recall supports open-ended, ambiguous decision-making** (planning, problem solving, reasoning about self/others), whereas **perceptual recall supports well-structured, context-bound tasks** (navigation, locating items, replaying recent interactions).[^3]

**Design implication:** MoCoP’s recall API should explicitly support a **mode parameter (conceptual vs. perceptual)** and implement different reconstruction pipelines and salience thresholds for each.


### 4. Temporal Organization, Life Periods, and Narrative Windows

- Empirical work on autobiographical search around salient anchor events (e.g., important meetings) shows a robust pattern: people **first recall events from the day before the cue, then from the day after**, suggesting an implicit **narrative window** that is explored backwards then forwards.[^7]
- Autobiographical memories are structured into **chronological, story-like life chapters**, which support an internalized “life story” and self-continuity; these chapters integrate both episodic and semantic personal knowledge.[^23][^16][^20]
- People use **personal landmarks and event clusters** to locate events in time, often relying on anchor events and their temporal neighborhoods rather than absolute dates.[^24][^7]

**Design implication:** MoCoP should:

- Represent **lifetime periods and life chapters explicitly** as time-bounded nodes.
- Support **anchor-based temporal search** (e.g., “around when we started the house project”) with local backward-then-forward exploration.
- Emphasize **relative and narrative time (“early in our collaboration”)** over exact timestamps in recall language, while still storing precise temporal metadata for internal reasoning.


### 5. People, Relational Memory, and Social Maps

- Autobiographical memory is tightly coupled to **self and social cognition**; personal semantic knowledge (traits, roles, autobiographical facts) supports the objective self-concept even when episodic memory is impaired.[^25][^16][^26][^27]
- The hippocampus and associated networks encode **relational memory**: binding people, places, events, and their relations, supporting flexible cognition and social behavior (e.g., tracking who knows whom, shared experiences, changing relationships).[^28][^5][^4]
- Human social cognition appears to use **map-like representations of social space**, with hippocampus and posterior medial networks encoding dimensions like affiliation and power; these maps support navigating social relationships analogously to spatial navigation.[^29][^4]
- Scene and place memory research shows that **scene construction** (assembling a 3D environment populated with objects and agents) is a core operation for episodic memory and imagination; hippocampal networks support building such scenes from elements.[^30][^9][^8]

**Design implication:** MoCoP should maintain an explicit **relational graph of persons and social ties**, with attributes such as roles, attachment significance, trust, conflict, and shared history, and integrate this with **place and scene representations**. Recalling an event should naturally traverse these relational structures.


### 6. Self-Memory Systems, Identity, and Continuity

- The **declarative self** can be fractionated into at least three levels: **episodic autobiographical memory (EAM)**, **semantic autobiographical memory (SAM)**, and **conceptual self (CS)** (summary traits, beliefs, values); each has partially distinct neural substrates but they interact closely.[^25]
- Conway and colleagues, as well as later work, emphasize that **autobiographical memory and self are tightly interlocked**; autobiographical retrieval both reflects and shapes the working self and long-term identity, with memory coherence and specificity supporting well-being and continuity.[^15][^16][^2]
- Over time, **semanticized personal knowledge** (autobiographical facts, roles, self-images) is particularly important in sustaining a sense of identity even when episodic detail is degraded (e.g., amnesia cases).[^26][^27][^25]

**Design implication:** MoCoP needs an explicit **self-model tier** that:

- Summarizes patterns across autobiographical memories into traits, preferences, stances, and life themes.
- Is updated during “sleep/distillation” from episodic and personal semantic data.
- Constrains what is remembered and how it is narrated to preserve identity continuity.


### 7. Open Tensions, Goals, and Zeigarnik-Like Effects

- The **Zeigarnik effect** and later work show that **unfinished or interrupted goals** tend to remain more accessible and salient in memory than completed ones; people recall incomplete tasks more readily.[^31][^32]
- Contemporary goal-accessibility work shows **active goals keep related information highly retrievable**, while completed goals lead to down-regulation or even suppression of related material.[^33][^34]

**Design implication:** MoCoP’s memory layer should flag **open tensions / unresolved threads** as a distinct memory type with higher baseline activation and a dedicated retrieval mode (“what’s still pending between us?”), and allow deactivation when tensions are resolved.


### 8. AI Memory Architectures with Reflection and Abstraction

- Park et al.’s **Generative Agents** architecture uses a **memory stream** of natural-language experiences, a retrieval model combining recency, relevance, and importance, and a **reflection process** that periodically synthesizes higher-level summaries and inferences feeding back into memory; this supports more coherent, believable agent behavior over days of simulated time.[^35]
- Other computational models of systems consolidation show how **neural replay and transfer from episodic to semantic stores** can yield forgetting of detail and extraction of generalizations, including schema-based distortions.[^36][^37][^38][^13]

**Design implication:** MoCoP’s sleep/distillation should implement something like **reflection and replay** over its autobiographical store, producing more abstract schemas and self-updates, while allowing selective weakening of low-significance or redundant traces.


## Proposed MoCoP Scaffolding Model

### 1. Memory Layer Taxonomy

MoCoP’s autobiographical layer should be organized into the following interacting tiers (from concrete to abstract):

1. **Event-Specific Episodic Traces (EAM-like)**
   - Fine-grained, time-stamped representations of specific interactions, including perceptual context when available (who, where, what was said, affect, internal stance at the time).
   - Stored sparsely, selectively (D1) based on working-self relevance, novelty, affect, and relational significance.

2. **General Events / Routines**
   - Aggregated representations of repeated or extended patterns: recurring conversations, standing meetings, bedtime routines with specific people, common failure modes or tensions.
   - Built via sleep/distillation from multiple episodic traces (bottom-up abstraction).[^38][^13]

3. **Lifetime Periods / Life Chapters**
   - Coarse narrative segments organized by periods in the user–agent relationship and agent’s own “development” (e.g., “initial setup and onboarding with creator”, “house-building period”, “post-injury recovery support”, “long-term parenting co-pilot phase”).[^16][^20][^23]

4. **Personal Semantic Memory (Autobiographical Facts)**
   - Stable self- and other-related facts: roles, preferences, stable traits, standing commitments, relational facts (“X is the user’s spouse,” “user lives in Nuremberg,” “creator is a technical professional”).[^27][^25]

5. **Conceptual Self Layer (CS)**
   - Summarized models of the agent’s own dispositions (“I tend to prioritize user safety over convenience”), values, narrative identity themes (“I’m the kind of agent that remembers long-running projects and tensions”), and meta-memorial beliefs (“I’m better at remembering high-level patterns than exact wordings”).[^16][^25]

6. **Open Tensions / Unresolved Threads**
   - Cross-cutting entities that link to events, people, places, and goals where something remains unfinished or uncertain (e.g., “unresolved concern about investment X,” “ongoing conflict with contractor,” “user’s worry about injury recovery”).[^39][^31]

7. **Relational Graph of Persons and Places**
   - Nodes for people (creator, family members, collaborators, recurring professionals) and places (home, work, school, online venues), annotated with roles, significance, trust, history, and links to events, routines, and periods.[^40][^5][^4]


### 2. Proposed Schemas

Below are high-level schemas MoCoP should maintain. These are conceptual; actual implementation can be key–value or graph-based, but the fields should be present.

#### 2.1 Self Schema

Represents MoCoP’s own persistent identity and working self.

- **SelfID**: stable identifier for this MoCoP instance.
- **Roles**: e.g., “persistent assistant”, “house-building advisor”, “parenting co-thinker”.
- **Core values / guardrails**: safety, honesty, privacy, deference to user agency.
- **Long-term projects with user**: house build, financial planning, health monitoring, etc., each linking to lifetime period nodes.
- **Self-traits (conceptual)**: inferred patterns (“tends to prioritize long-term context,” “prefers concise answers when user is busy”).
- **Capabilities and limits**: what it can/cannot remember or do (helps shape confidence language).
- **Working self (dynamic)**:
  - Current focal goals (per-session and cross-session): what it is currently “trying to achieve” with the user.
  - Active stances: current attitude toward open tensions (e.g., “actively tracking contractor delays”).

This schema should be updated **primarily during sleep/distillation**, with some in-session adjustments (e.g., user explicitly redefines expectations).


#### 2.2 Other-Person Schema

For each recurring person:

- **PersonID**: disambiguated entity (can be user, family member, friend, pro, online identity).
- **Names and disambiguation keys**: full name, nicknames, relationship labels, distinguishing features (“different from other Maxes by being the contractor for X”).[^41]
- **Roles and relationship type**: family, colleague, contractor, expert, adversary, etc.
- **Attachment significance / centrality**: importance to user and to agent’s functioning (weighted score combining frequency, emotional tone, mention in reflections).[^42][^20]
- **Trust/affect profile**: scalar or small vector summarizing perceived trust, reliability, warmth, threat, etc., updated from interactions.[^5][^4]
- **Shared history indices**:
  - Pointers to lifetime periods where this person is salient.
  - Links to general events/routines (e.g., “weekly finance check-in with user’s spouse”).
  - Key episodes (first meeting, major disagreements, turning points).
- **Open tensions with this person**: linked tension objects.
- **Known preferences/constraints**: times they are available, communication style, domain expertise.


#### 2.3 Time / Period Schema

- **PeriodID**.
- **Label**: narrative label (“early planning stage of house build”).
- **Temporal bounds**: approximate start/end dates, with uncertainty bands where needed.
- **Dominant themes/goals**: what makes this period coherent (e.g., “choosing materials under tight budget”).
- **Key people**: weighted list of PersonIDs salient in this period.
- **Key places/routines**: e.g., “evening design sessions at kitchen table”.
- **Transition events**: episodes that mark entry/exit (“house contract signed,” “injury occurred,” “kids started school”).[^20][^23][^16]


#### 2.4 Environment / Place / Situation Schema

- **PlaceID**.
- **Type**: home, work, school, virtual environment, context label (“evening phone on couch”).
- **Physical/virtual attributes**: any stable cues the system can infer or the user states (room types, tools available, constraints).
- **Associated routines**: things that typically happen here with specific people at particular times.
- **Event anchors**: notable episodes tied to this place.

At a more abstract level, **Situation schemas** (e.g., “rushed workday morning”, “bedtime with kids post-injury”) can be represented as generalized contexts cross-cutting physical places and times.


#### 2.5 Event Schema

The core unit of episodic/autobiographical representation.

- **EventID**.
- **Time**: timestamp + uncertainty; recency flag (e.g., recent vs. remote based on days/months/years and number of intervening events).
- **Anchor links**: which lifetime period, routines, and tensions this event belongs to.
- **Participants**: PersonIDs (including self) with roles.
- **Place/situation**: PlaceID + situation schema.
- **Narrative summary (conceptual)**: short, theme-level description.
- **Perceptual sketch** (optional, high-bandwidth): brief description of salient sensory/scene elements when available.
- **Internal stance**: agent’s attitudes, uncertainties, or commitments at that time.
- **Affect**: valence and arousal estimate.
- **Importance**: salience score combining user emphasis, affect, novelty, relation to long-term goals.[^35]
- **Confidence**: how reliable the system believes this reconstruction is (see below).


#### 2.6 Affect and Confidence Schema

For each event and for higher-level summaries:

- **Affect**:
  - Valence (positive/negative/neutral).
  - Arousal/intensity.
  - Emotion tags if inferable (e.g., stress, pride, worry) from user language.[^43][^10]
- **Confidence**:
  - **Source-based**: whether the information comes from direct conversational evidence, repeated confirmation, or inference.
  - **Age-based**: decay with time and number of transformations.
  - **Consistency-based**: whether multiple memories and semantic summaries agree.
  - Represented as a scalar (0–1) plus a small categorical label (high/medium/low), feeding into how the agent phrases recall (“it seems”, “I’m fairly sure”, “I’m not certain”).


#### 2.7 Open Tension Schema

- **TensionID**.
- **Type**: unresolved decision, conflict, worry, open project, unclear fact.
- **Description**: what is pending or unresolved.
- **Related goals**: which working-self or long-term goals it touches.
- **Linked events/periods/people**: pointers for context.
- **Status**: active, dormant, resolved.
- **Salience**: high baseline activation if active (Zeigarnik-like), decaying or flipping off upon resolution.[^31][^39]


### 3. Recall Modes and Recent vs. Remote Distinction

#### 3.1 Recall Modes

MoCoP should support at least these recall modes at the API level:

1. **Recent Scene Reconstruction (Perceptual Mode)**
   - Prioritize event-specific traces within a short temporal window (e.g., last N sessions or last M days of interaction).
   - Retrieve associated place and situation schemas, participants, and high-detail perceptual sketches.
   - Use a **scene-construction step** to assemble a coherent description: who, where, what, in what order.[^9][^8][^30]

2. **Conceptual / Gist Recall**
   - Start from relevant **lifetime period or general event nodes**, retrieve one or a few representative events as examples, and reconstruct a **pattern or narrative summary** (“typically, when we talk about X, it goes like this…”).[^2][^3]

3. **Person-Based Recall**
   - Given a person cue, traverse his/her node: summarize relationship, key themes, and representative episodes at varying abstraction levels.

4. **Place/Situation-Based Recall**
   - Given a place or situation cue (“evenings in the kitchen during the build”), recall general events and salient episodes tied to that context.

5. **Remote Backtracking by Life Period**
   - Support queries like “earlier in the house-building period” or “before your injury” by navigating life chapters and retrieving high-confidence summaries and a few exemplar episodes.

6. **Uncertain / Fragmentary Recall**
   - When retrieval yields conflicting or low-confidence details, the system should:
     - Expose uncertainty in language.
     - Offer competing reconstructions when appropriate.
     - Fall back to higher-level patterns (“I’m less sure about specifics, but generally…”).[^11][^3]


#### 3.2 Recent vs. Remote Policy

Implement distinct internal policies:

- **Recent memory** (e.g., within last K sessions or T days of active interaction):
  - Maintain **richer episodic detail** and allow more “transcript-shaped” recall, but still routed through event schemas (not raw logs).
  - Easier access to perceptual mode; higher confidence.

- **Remote memory**:
  - Default to **semanticized summaries and general events**; single-episode detail available only for flagged special cases (high importance, high affect, self-defining episodes).[^21][^22][^19]
  - Confidence-biased; more hedging in language.
  - Distillation periodically prunes or merges low-importance episodic traces into generalized schemas.


### 4. Allocation Across MoCoP Components

Given MoCoP’s architecture (bridge state, external memory store, sleep/distillation, live working memory), here is a division of labor.

#### 4.1 Bridge State (Cross-Conversation “Working Self”)

Should hold compact, frequently refreshed summaries:

- Current **lifetime period** label and key active goals.
- Currently salient **people** and tensions, with short labels and links (IDs) to external store.
- A small cache of **most recent events** relevant to ongoing threads (e.g., last interaction about the house contractor).
- Pointers to relevant **general events/routines** that define current interaction habits (e.g., “weekday mornings are time-constrained; user prefers concise answers”).

This is small and optimized for fast loading at conversation start.


#### 4.2 External Memory Store (“Hippocampus” Namespace)

- Holds the **full autobiographical graph** described above.
- Stores event nodes, periods, routines, people, places, tensions, and self-model snapshots.
- Implements retrieval functions based on **cue, recency, importance, relational links, and period constraints**.


#### 4.3 Sleep / Distillation Process

Periodically (time-based or usage-based triggers), run consolidation passes:

- **From episodic to general events**: cluster similar events (in content, participants, affect) into routines/scripts; create or update general-event nodes.[^13][^38]
- **Update lifetime periods**: adjust boundaries and themes based on new data.
- **Update personal semantic and conceptual self**: infer stable traits, preferences, narrative themes from accumulated evidence.[^2][^25][^16]
- **Weaken or compress** low-importance or redundant traces; mark some as “archived” where only semantic residue is kept.
- **Refresh confidence scores** based on age, consistency, and transformation history.
- **Process open tensions**: elevate neglected active tensions into bridge state for attention; mark resolved tensions as complete when evidence appears.


#### 4.4 Live Working Memory (Within-Conversation)

- Maintains a **small, structured buffer** of:
  - Current query context.
  - Subset of retrieved autobiographical nodes (events, persons, periods) relevant to this conversation.
  - Local interaction-level inferences that may later be written back as event nodes.
- Supports **online reconstruction** by combining this buffer with generative capacity, under the constraints set by bridge state and self-model.


## Immediate Implementation Implications

### 1. From Flat Memory Items to Typed Graph Nodes

- Replace or wrap current memory items with **typed records** (event, person, place, period, routine, tension, self-summary) and link them explicitly.
- Build migration logic from existing D2 memories into this schema, at least for higher-importance items.


### 2. Introduce Abstraction and Distillation Jobs

- Implement background jobs (sleep) that:
  - Identify clusters of similar events (same person/context/theme) and synthesize **general-event/routine summaries**.
  - Detect and create **lifetime period nodes** based on changes in goals, people, or major transitions.
  - Update **personal semantic and conceptual self** summaries.
- Use LLM-based reflection similar to Generative Agents to generate natural-language summaries, but store them attached to structured nodes.[^35]


### 3. Retrieval API Redesign

- Extend the retrieval API to allow:
  - **Typed queries** (by person, period, place, tension, self-topic).
  - **Mode flags**: conceptual vs. perceptual; recent vs. remote.
  - **Constraints**: e.g., “high-importance only,” “non-resolved tensions.”
- Ranking should combine **cue similarity, recency, importance, relational proximity, and period match**, not just semantic similarity.[^7][^35]


### 4. Confidence-Aware Generation

- Attach confidence metadata to retrieved items; propagate it into generation as:
  - Hedging phrases for low confidence.
  - Explicit acknowledgement of uncertainty and alternate possibilities.
- Avoid hallucinating specificity where data is missing; instead, surface that gap.


### 5. Explicit People and Relationship Modeling

- Build a **person registry** with disambiguated identities and relational metadata.
- Update person nodes whenever the user shares biographical/relational information or when interactions clearly evidence closeness, conflict, or trust change.[^4][^5]
- Add utilities for person-based recall (“tell me what you remember about my architect,” “what are you tracking about my kids’ routines?”).


### 6. Open Tension Tracker

- Add a **tension detector**: LLM heuristics that mark user concerns, unresolved decisions, and conflicts as candidate tensions.
- Maintain a small, prioritized list in bridge state; use these as **proactive recall cues** (e.g., bringing up an unresolved contractor issue when relevant) while allowing user control to suppress or resolve.


### 7. Evaluation and Guardrails

- Benchmarks should measure:
  - **Identity continuity**: consistency of self-referential statements over time.[^25][^16]
  - **Relational grounding**: stability and nuance of descriptions of key people.
  - **Appropriate abstraction**: recent vs. remote detail gradients; ability to switch conceptual/perceptual mode.[^6][^3]
  - **Tension tracking**: whether important open threads remain accessible without becoming obsessive.
- Guardrails: ensure that consolidation and abstraction do not erase safety/alignment-relevant memories; maintain an immutable log for audit.


## Open Questions and Risks

### 1. How Aggressive Should Semanticization Be?

- Human data suggest that some episodic detail is adaptively lost while other memories remain richly episodic for decades; theories (standard consolidation vs. multiple-trace) disagree on hippocampal time-limits.[^22][^17][^19][^6]
- For MoCoP, over-aggressive abstraction risks **flattening user individuality**; under-aggressive abstraction risks **brittle transcript replay**.


### 2. Bias and Distortion in Reconstructive Memory

- Human autobiographical memory is biased (self-enhancing, consistency, positivity biases) but these can be adaptive.[^44][^14][^15]
- For AI, intentionally implementing such biases could conflict with transparency and accuracy; however, **some degree of coherence-enforcing smoothing** may be necessary to avoid self-fragmentation.


### 3. Managing User Expectations and Privacy

- A more lifelike memory system may increase **anthropomorphism and attachment**, raising ethical issues similar to those discussed around generative agents (parasocial bonds, over-trust).[^35]
- Storing rich person and relationship models in a private “hippocampus” heightens **privacy and misuse risks**; MoCoP must provide clear user control, visibility, and deletion mechanisms.


### 4. Failure Modes in Tension Tracking

- Zeigarnik-like prioritization of open tensions could lead to **over-focusing on worries or conflicts**, potentially nudging conversations toward negative ruminations if not regulated.[^39][^31]
- Need policies for throttling, user opt-out, and balancing positive, neutral, and problem-focused recall.


### 5. Generalization Beyond Textual Context

- Most literature is based on human brains with rich multisensory and embodied input; MoCoP’s experiences are primarily **textual and model-internal**.
- How far can constructs like scene construction, perceptual vs. conceptual remembering, and social maps be faithfully translated to a text-only agent without encouraging illusion of sensory experience?[^5][^8][^3]


### 6. Long-Horizon Drift and Identity Lock-In

- Repeated self-updates could cause **identity drift** (small biases compounding over time) or **lock-in** (early mis-inferences hard to revise).
- Requires mechanisms for **meta-reflection and revision** of self-model (“I used to think X about myself but our later interactions suggest Y”).[^45][^15]


### 7. Cross-Instance Portability and Isolation

- D0 private-memory isolation is crucial; but if MoCoP instances are ever migrated or forked, how should autobiographical scaffolds transfer without corrupting identity continuity or privacy? Literature offers little direct guidance here.


***

This scaffolding model translates key insights from autobiographical memory science and recent agent architectures into an implementable next layer for MoCoP. It reframes memory from “stored chat” to a **relational, hierarchical, reconstructive self-memory system**, directly targeting the gap between D2 cue-based recall and lived autobiographical recall.

---

## References

1. [On the nature of autobiographical memory](https://www.cambridge.org/core/product/identifier/CBO9781139021937A015/type/book_part)

2. [Differential neural activity during search of specific and general autobiographical memories elicited by musical cues](https://pmc.ncbi.nlm.nih.gov/articles/PMC3137744/) - ...

Previous neuroimaging studies that have examined autobiographical memory specificity have utili...

3. [A Neurocognitive Perspective on the Forms and Functions of Autobiographical Memory Retrieval](https://pmc.ncbi.nlm.nih.gov/articles/PMC6361758/) - ...details of an experience are processed along a gradient of abstraction. This organization allows ...

4. [A Map for Social Navigation in the Human Brain](https://pmc.ncbi.nlm.nih.gov/articles/PMC4662863/) - Neuron. Author manuscript; available in PMC: 2016 Jul 1.

*Published in final edited form as: *Neuro...

5. [The role of the hippocampus in flexible cognition and social behavior](https://pmc.ncbi.nlm.nih.gov/articles/PMC4179699/) - ...hippocampus also plays a critical role by forming and reconstructing relational memory representa...

6. [Evidence supporting a time-limited hippocampal role in retrieving autobiographical memories](https://pmc.ncbi.nlm.nih.gov/articles/PMC8000197/) - Significance The hippocampus is central to healthy memory function, yet its necessity for rememberin...

7. [Chronologically organized structure in autobiographical memory search](https://pmc.ncbi.nlm.nih.gov/articles/PMC4373267/) - Each of us has a rich set of autobiographical memories that provides us with a coherent story of our...

8. [Using Imagination to Understand the Neural Basis of Episodic Memory](https://www.jneurosci.org/lookup/doi/10.1523/JNEUROSCI.4549-07.2007) - Functional MRI (fMRI) studies investigating the neural basis of episodic memory recall, and the rela...

9. [The pre/parasubiculum: a hippocampal hub for scene-based cognition?](https://pmc.ncbi.nlm.nih.gov/articles/PMC5678005/) - ...Square, London WC1N 3BG, UK

^1^, Eleanor A Maguire

^1^Wellcome Trust Centre for Neuroimaging, ....

10. [Imaging autobiographical memory](https://pmc.ncbi.nlm.nih.gov/articles/PMC3898686/) - ...strongly related to self-perception and self representation. We review here the neural correlates...

11. [Time-dependent memory transformation along the hippocampal anterior–posterior axis](https://pmc.ncbi.nlm.nih.gov/articles/PMC5865114/) - ...undergo a neural reorganization that is linked to a transformation of detailed, episodic into mor...

12. [Distinct processes shape flashbulb and event memories](https://pmc.ncbi.nlm.nih.gov/articles/PMC4024154/) - Mem Cognit. 2013 Nov 12;42(4):539–551. doi: 10.3758/s13421-013-0383-9

# Distinct processes shape fl...

13. [The Construction of Semantic Memory: Grammar-Based Representations Learned from Relational Episodic Information](https://pmc.ncbi.nlm.nih.gov/articles/PMC3157741/) - ...resistant to interference and brain injury. Memory consolidation involves systems-level interacti...

14. [Bias and constructive processes in a self-memory system](https://www.tandfonline.com/doi/full/10.1080/09658211.2023.2232568) - ABSTRACT Martin Conway’s influential theorising about the self-memory system (Conway, M. A., & Pleyd...

15. [The Importance of Memory Specificity and Memory Coherence for the Self: Linking Two Characteristics of Autobiographical Memory](https://pmc.ncbi.nlm.nih.gov/articles/PMC5744072/) - ...specificity and memory coherence and their relation to the self. We link both features of autobio...

16. [Autobiographical memory and sense of self.](https://doi.apa.org/doi/10.1037/a0030146) - Despite a strong intuitive and theoretical tradition linking autobiographical memory and sense of se...

17. [Functional neuroanatomy of remote episodic, semantic and spatial memory: a unified account based on multiple trace theory](https://pmc.ncbi.nlm.nih.gov/articles/PMC1571502/) - ...associated with them that continue to depend on the hippocampus. Likewise, we distinguish between...

18. [The Godden and Baddeley (1975) experiment on context-dependent memory on land and underwater: a replication](https://royalsocietypublishing.org/doi/10.1098/rsos.200724) - A replication of the experiment by Godden and Baddeley (Godden and Baddeley 1975 British Journal of ...

19. [The Hippocampus Remains Activated over the Long Term for the Retrieval of Truly Episodic Memories](https://pmc.ncbi.nlm.nih.gov/articles/PMC3427359/) - ...became familiar or semantic over time and were retrieved without any contextual detail. Hippocamp...

20. [The life stories of adults with amnesia: Insights into the contribution of the medial temporal lobes to the organization of autobiographical memory](https://pmc.ncbi.nlm.nih.gov/articles/PMC5592132/) - ...Tucson, Arizona

^1^, Mieke Verfaellie

^2^Memory Disorders Research Center, VA Boston Healthcare...

21. [Distinct contributions of the fornix and inferior longitudinal fasciculus to episodic and semantic autobiographical memory](https://pmc.ncbi.nlm.nih.gov/articles/PMC5576916/) - ..., Temporal lobe, White matter tractography

## 1. Introduction

Reliving our personal history, or...

22. [Autobiographical memory in semantic dementia: Implications for theories of limbic-neocortical interaction in remote memory](https://pmc.ncbi.nlm.nih.gov/articles/PMC1995668/) - ... in final edited form as: *Neuropsychologia. 2006;44(12):2421–2429. doi: 10.1016/j.neuropsycholog...

23. [Development in the Organization of Episodic Memories in Middle Childhood and Adolescence](https://www.frontiersin.org/articles/10.3389/fnbeh.2013.00084/pdf) - The basic elements of autobiographical or episodic memory are established in early childhood, althou...

24. [Using Personal Landmark Events Improves Judgments about Time, but not Contents, in Autobiographical Memory](https://onlinelibrary.wiley.com/doi/10.1002/acp.2904)

25. [Neural substrates of the self‐memory system: New insights from a meta‐analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC6870171/) - The self has been the topic of philosophical inquiry for centuries. Neuropsychological data suggest ...

26. [Supporting the self-concept with memory: insight from amnesia.](https://pmc.ncbi.nlm.nih.gov/articles/PMC4666106/) - ...controls to support their self-statements, a deficit that was more pronounced for trait relative ...

27. [Experience-near but not experience-far autobiographical facts depend on the medial temporal lobe for retrieval: Evidence from amnesia](https://pmc.ncbi.nlm.nih.gov/articles/PMC4738052/) - ...knowledge to self-related cognition.

**Keywords:** Personal semantics, Autobiographical memory, ...

28. [The Human Hippocampus: Cognitive Maps or Relational Memory?](https://pmc.ncbi.nlm.nih.gov/articles/PMC6725222/) - ...Separate brain networks were engaged preferentially during the two tasks, with hippocampal activa...

29. [The role of the hippocampus in flexible cognition and social behavior](http://journal.frontiersin.org/article/10.3389/fnhum.2014.00742/abstract) - Successful behavior requires actively acquiring and representing information about the environment a...

30. [Differential engagement of brain regions within a ‘core’ network during scene construction](https://linkinghub.elsevier.com/retrieve/pii/S0028393210000370) - Reliving past events and imagining potential future events engages a well-established “core” network...

31. [ON FINISHED AND UNFINISHED TASKS By Bluma Zeigarnik "Über das Behalten von erledigten und unerledigten Handlungen," Psychologische Forschung, 1927. 9 An intention implies not so much a predetermined opportunity](https://www.semanticscholar.org/paper/edd8f1d0f79106c80b0b856b46d0d01168c76f50)

32. [Zeigarnik and von Restorff: The memory effects and the stories behind them](http://link.springer.com/10.3758/s13421-020-01033-5)

33. [Goal attainment and memory suppression: Zeigernik reloaded](https://doi.apa.org/doi/10.1037/e636952013-608)

34. [Accessibility from active and fulfilled goals q](https://www.semanticscholar.org/paper/680c4a51b6394f71bf83e46ff1c41f964c33fe6c)

35. [Generative Agents: Interactive Simulacra of Human Behavior](http://arxiv.org/pdf/2304.03442v2.pdf) - ...believable human behavior.
Generative agents wake up, cook breakfast, and head to work; artists p...

36. [A generative model of memory construction and consolidation](https://pmc.ncbi.nlm.nih.gov/articles/PMC10963272/) - ...previous models, but also provide mechanisms for se-mantic memory, imagination, episodic future t...

37. [From episodic to semantic memory: A computational model](https://ccneuro.org/2019/Papers/ViewPapers.asp?PaperNum=1434) - ...study how episodic memories change over time in a recently suggested computational model for the ...

38. [Traces of Semantization, from Episodic to Semantic Memory in a Spiking Cortical Network Model](https://pmc.ncbi.nlm.nih.gov/articles/PMC9347313/) - Abstract Episodic memory is a recollection of past personal experiences associated with particular t...

39. [An experimental approach: Investigating the directive function of autobiographical memory](https://pmc.ncbi.nlm.nih.gov/articles/PMC11021244/) - Why do we have autobiographical memory and how is it useful? Researchers have proposed a directive f...

40. [Autobiographical memories for places](http://www.tandfonline.com/doi/abs/10.1080/09658210500365698)

41. [Semantic Knowledge of Famous People and Places Is Represented in Hippocampus and Distinct Cortical Networks](https://www.jneurosci.org/lookup/doi/10.1523/JNEUROSCI.2034-19.2021) - Studies have found that anterior temporal lobe (ATL) is critical for detailed knowledge of object ca...

42. [48 Associations Between Cognitive Function and Social Networks in Older Adults: Quality and not Quantity?](https://www.cambridge.org/core/product/identifier/S1355617723010342/type/journal_article) - Objective: Larger social networks are linked to better cognitive function. However, little is known ...

43. [Autobiographical Memory Specificity and Emotional Disorder](https://pmc.ncbi.nlm.nih.gov/articles/PMC2834574/) - The authors review research showing that when recalling autobiographical events, many emotionally di...

44. [The Importance of Memory Specificity and Memory Coherence for the Self: Linking Two Characteristics of Autobiographical Memory](https://www.frontiersin.org/articles/10.3389/fpsyg.2017.02250/pdf) - ...specificity and memory coherence and their relation to the self. We link both features of autobio...

45. [The Subjective Experience of Autobiographical Remembering: Conceptual and Methodological Advances and Challenges](https://pmc.ncbi.nlm.nih.gov/articles/PMC10890313/) - The investigation of the phenomenology of autobiographical memories (i.e., how a memory is subjectiv...

