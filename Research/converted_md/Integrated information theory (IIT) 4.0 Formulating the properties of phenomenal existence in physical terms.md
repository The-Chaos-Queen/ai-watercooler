# PLOS COMPUTATIONAL BIOLOGY

RESEARCH ARTICLE

# Integrated information theory (IIT) 4.0: Formulating the properties of phenomenal existence in physical terms


**[Larissa AlbantakisID](https://orcid.org/0000-0003-1000-9917)** **[1]** [☯] **, Leonardo Barbosa** **[1,2]** [☯] **, Graham Findlay** **[1,3]** [☯] **[, Matteo GrassoID](https://orcid.org/0000-0002-2124-7147)** **[1]** [☯] **,**
**Andrew M. Haun** **[1]** [☯] **[, William MarshallID](https://orcid.org/0000-0002-4779-6734)** **[1,4]** [☯] **, William G. P. Mayner** **[1,3]** [☯] **,**
**Alireza Zaeemzadeh** **[1]** [☯] **, Melanie Boly** **[1,5]** **, Bjørn E. Juel** **[1,6]** **, Shuntaro Sasai** **[1,7]** **, Keiko Fujii** **[1]** **,**
**Isaac David** **[1]** **, Jeremiah Hendren** **[1,8]** **[, Jonathan P. LangID](https://orcid.org/0000-0001-8071-1344)** **[1]** **[, Giulio TononiID](https://orcid.org/0000-0002-3892-4087)** **[1]** *****



OPEN ACCESS


**Citation:** Albantakis L, Barbosa L, Findlay G,

Grasso M, Haun AM, Marshall W, et al. (2023)

Integrated information theory (IIT) 4.0: Formulating

the properties of phenomenal existence in physical

terms. PLoS Comput Biol 19(10): e1011465.

[https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465)


**Editor:** Lyle J. Graham, Universite´ Paris Descartes,

Centre National de la Recherche Scientifique,

FRANCE


**Received:** January 11, 2023


**Accepted:** August 26, 2023


**Published:** October 17, 2023


**Copyright:** © 2023 Albantakis et al. This is an open
access article distributed under the terms of the

[Creative Commons Attribution License, which](http://creativecommons.org/licenses/by/4.0/)

permits unrestricted use, distribution, and

reproduction in any medium, provided the original

author and source are credited.


**Data Availability Statement:** There are no primary

data in the paper; the code used to produce the

results and analyses presented in this manuscript

[is available at https://github.com/wmayner/pyphi/](https://github.com/wmayner/pyphi/tree/feature/iit-4.0/pyphi)

[tree/feature/iit-4.0/pyphi.](https://github.com/wmayner/pyphi/tree/feature/iit-4.0/pyphi)


**Funding:** This project was made possible through

the support of a grant from Templeton World

Charity Foundation (TWCF0216, G.T.). In addition,

this research was supported by the David P White

Chair in Sleep Medicine at the University of



**1** Department of Psychiatry, University of Wisconsin, Madison, Wisconsin, United States of America, **2** Fralin
Biomedical Research Institute at VTC, Virginia Tech, Roanoke, Virginia, United States of America,
**3** Neuroscience Training Program, University of Wisconsin, Madison, Wisconsin, United States of America,
**4** Department of Mathematics and Statistics, Brock University, St. Catharines, Ontario, Canada,
**5** Department of Neurology, University of Wisconsin, Madison, Wisconsin, United States of America,
**6** Institute of Basic Medical Sciences, University of Oslo, Oslo, Norway, **7** Araya Inc., Tokyo, Japan,
**8** Graduate School Language & Literature, Ludwig Maximilian University of Munich, Munich, Germany


☯ These authors contributed equally to this work.

- gtononi@wisc.edu

## Abstract


This paper presents Integrated Information Theory (IIT) 4.0. IIT aims to account for the prop
erties of experience in physical (operational) terms. It identifies the essential properties of

experience (axioms), infers the necessary and sufficient properties that its substrate must

satisfy (postulates), and expresses them in mathematical terms. In principle, the postulates

can be applied to any system of units in a state to determine whether it is conscious, to what

degree, and in what way. IIT offers a parsimonious explanation of empirical evidence,

makes testable predictions concerning both the presence and the quality of experience, and

permits inferences and extrapolations. IIT 4.0 incorporates several developments of the

past ten years, including a more accurate formulation of the axioms as postulates and math
ematical expressions, the introduction of a unique measure of intrinsic information that is

consistent with the postulates, and an explicit assessment of causal relations. By fully

unfolding a system’s irreducible cause–effect power, the distinctions and relations specified

by a substrate can account for the quality of experience.


Author summary


As a theory of consciousness, IIT aims to answer two questions: 1) Why is experience
present vs. absent? and 2) Why do specific experiences feel the way they do? The theory’s
starting point is the existence of experience. IIT then aims to account for phenomenal
existence and its essential properties in physical terms. It concludes that a substrate—a set
of interacting units—can support consciousness if it can take and make a difference for
itself (intrinsicality), select a specific cause and effect as an irreducible whole with a



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Integrated information theory (IIT) 4.0 Formulating the properties of phenomenal existence in physical terms_extracted/images/Integrated-information-theory-(IIT)-4.0-Formulating-the-properties-of-phenomenal-existence-in-physical-terms.pdf-0-0.png)

[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 1 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0



Wisconsin-Madison, by the Tiny Blue Dot

Foundation (UW 133AAG3451; G.T.), and by the

Natural Science and Engineering Research Council

of Canada (NSERC; RGPIN-2019-05418; W.M.). L.

A. also acknowledges the support of a grant from

the Templeton World Charity Foundation (TWCF
2020-20526, L.A.). The funders had no role in

study design, data collection and analysis, decision

to publish, or preparation of the manuscript.


**Competing interests:** I have read the journal’s

policy and the authors of this manuscript have the

following competing interests: G.T. holds an

executive position and has a financial interest in

Intrinsic Powers, Inc., a company whose purpose

is to develop a device that can be used in the clinic

to assess the presence and absence of

consciousness in patients. This does not pose any

conflict of interest with regard to the work

undertaken for this publication.



definite border and grain, and specify a structure of causes and effects through subsets of
its units. To that end, IIT provides a mathematical formalism that can be employed to
“unfold’’ the substrate’s cause–effect structure. This allows IIT to answer the two questions
above: 1) Experience is present for any substrate that fulfills the essential properties of
existence, and 2) specific experiences feel the way they do because of the specific causeeffect structure specified by their substrates. The theory is consistent with neurological
data, and some of its core principles have been successfully tested empirically.


**Introduction**


A scientific theory of consciousness should account for experience, which is subjective, in
objective terms [1]. Being conscious—having an experience—is understood to mean that
“there is something it is like to be” [2]: something it is like to see a blue sky, hear the ocean
roar, dream of a friend’s face, imagine a melody flow, contemplate a choice, or reflect on the
experience one is having.
IIT aims to account for phenomenal properties—the properties of experience—in physical
terms. IIT’s starting point is experience itself rather than its behavioral, functional, or neural
correlates [1]. Furthermore, in IIT “physical” is meant in a strictly operational sense—in terms
of what can be observed and manipulated.
The starting point of IIT is the existence of an experience, which is immediate and irrefutable [3]. From this “zeroth” axiom, IIT sets out to identify the essential properties of consciousness—those that are immediate and irrefutably true of every conceivable experience. These are
IIT’s five axioms of phenomenal existence: every experience is for the experiencer (intrinsicality), specific (information), unitary (integration), definite (exclusion), and structured
(composition).
Unlike phenomenal existence, which is immediate and irrefutable (an axiom), physical existence is an explanatory construct (a postulate), and it is assessed operationally (from within
consciousness): in physical terms, to be is to have cause–effect power. In other words, something can be said to exist physically if it can “take and make a difference”—bear a cause and
produce an effect—as judged by a conscious observer/manipulator.
The next step of IIT is to formulate the essential phenomenal properties (the axioms) in
terms of corresponding physical properties (the postulates). This formulation is an “inference
to a good explanation” and rests on basic assumptions such as realism, physicalism, and atomism (see Box 1: Methodological guidelines of IIT). If IIT is correct, the substrate of consciousness (see (1) in S1 Notes), beyond having cause–effect power (existence), must satisfy all five
essential phenomenal properties in physical terms: its cause–effect power must be for itself
(intrinsicality), specific (information), unitary (integration), definite (exclusion), and structured (composition).
On this basis, IIT proposes a fundamental explanatory identity: an experience is identical to
the cause–effect structure unfolded from a maximal substrate (defined below). Accordingly, all
the specific phenomenal properties of any experience must have a good explanation in terms
of the specific physical properties of the corresponding cause–effect structure, with no additional ingredients.
Based again on “inferences to a good explanation” (see Box 1), IIT formulates the postulates
in a mathematical framework that is in principle applicable to general models of interacting
units (but see (2) in S1 Notes). A mathematical framework is needed ( _a_ ) to evaluate whether
the theory is self-consistent and compatible with our overall knowledge about the world, ( _b_ ) to



[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 2 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


make specific predictions regarding the quality and quantity of our experiences and their substrate within the brain, and ( _c_ ) to extrapolate from our own consciousness to infer the presence
(or absence) and nature of consciousness in beings different from ourselves.
Ultimately, the theory should account for why our consciousness depends on certain portions of the world and their state, such as certain regions of the brain and not others, and for
why it fades during dreamless sleep, even though the brain remains active. It should also
account for why an experience feels the way it does—why the sky feels extended, why a melody
feels flowing in time, and so on. Moreover, the theory makes several predictions concerning
both the presence and the quality of experience, some of which have been and are being tested
empirically [4].
While the main tenets of the theory have remained the same, its formal framework has
been progressively refined and extended [5–8]. Compared to IIT 1.0 [5, 6], 2.0 [7, 9], and 3.0

[8], IIT 4.0 presents a more complete, self-consistent formulation and incorporates several
recent advances [10–13]. Chief among them are a more accurate formulation of the axioms as
postulates and mathematical expressions, the introduction of an Intrinsic Difference (ID) measure [12, 14] that is uniquely consistent with IIT’s postulates, and the explicit assessment of
causal relations [11].
In what follows, after introducing IIT’s axioms and postulates, we provide its updated
mathematical formalism. In the “Results and discussion” section, we apply the mathematical
framework of IIT to representative examples and discuss some of their implications. The article is meant as a reference for the theory’s mathematical formalism, a concise demonstration
of its internal consistency, and an illustration of how a substrate’s cause–effect structure is
unfolded computationally. A discussion of the theory’s motivation, its axioms and postulates,
and its assumptions and implications can be found in a forthcoming book (see (3) in S1 Notes)
and wiki [15] as well as in several publications [1, 16–21]. A survey of the explanatory power
and experimental predictions of IIT can be found in [4]. The way IIT’s analysis of cause–effect
power can be applied to actual causation, or “what caused what,” is presented in [10].


**From phenomenal axioms to physical postulates**

**Axioms of phenomenal existence**


That experience exists—that “there is something it is like to be”—is immediate and irrefutable,
as everybody can confirm, say, upon awakening from dreamless sleep. Phenomenal existence
is immediate in the sense that my experience is simply there, directly rather than indirectly: I
do not need to infer its existence from something else. It is irrefutable because the very doubting that my experience exists is itself an experience that exists—the experience of doubting [1,
3]. Thus, to claim that my experience does not exist is self-contradictory or absurd. The existence of experience is IIT’s zeroth axiom.


**Existence** Experience _exists_ : there is _something_ .


Traditionally, an axiom is a statement that is assumed to be true, cannot be inferred from
any other statement, and can serve as a starting point for inferences. The existence of experience is the ultimate axiom—the starting point for everything, including logic and physics.
On this basis, IIT proceeds by considering whether experience—phenomenal existence—
has some axiomatic or essential properties, properties that are immediate and irrefutably true
of every conceivable experience. Drawing on introspection and reason, IIT identifies the following five:


**Intrinsicality** Experience is _intrinsic_ : it exists _for itself_ .


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 3 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**Information** Experience is _specific_ : it is _this one_ .


**Integration** Experience is _unitary_ : it is _a whole_, irreducible to separate experiences.


**Exclusion** Experience is _definite_ : it is _this whole_ .


**Composition** Experience is _structured_ : it is composed of _distinctions_ and the _relations_ that
bind them together, yielding a _phenomenal structure_ that feels _the way it feels_ .


To exemplify, if I awaken from dreamless sleep and experience the white wall of my room,
my bed, and my body, the experience not only exists, immediately and irrefutably, but 1) it
exists for me, not for something else, 2) it is specific (this one experience, not a generic one), 3)
it is unitary (the left side is not experienced separately from the right side, and vice versa), 4) it
is definite (it includes the visual scene in front of me—neither less, say, its left side only, nor
more, say, the wall behind my head), 5) it is structured by distinctions (the wall, the bed, the
body) and relations (the body is on the bed, the bed in the room), which make it feel the way it
does and not some other way.
The axioms are not only immediately given, but they are irrefutably true of every conceivable experience. For example, once properly understood, the unity of experience cannot be
refuted. Trying to conceive of an experience that were not unitary leads to conceiving of two
separate experiences, each of which is unitary, which reaffirms the validity of the axiom. Even
though each of the axioms spells out an essential property in its own right, the axioms must be
considered together to properly characterize phenomenal existence.
IIT takes the above set of axioms to be complete: there are no further properties of experience that are essential. Other properties that might be considered as candidates for axiomatic
status include space (experience typically takes place in some spatial frame), time (an experience usually feels like it flows from a past to a future), change (an experience usually transitions
or flows into another), subject–object distinction (an experience seems to involve both a subject and an object), intentionality (experiences usually refer to something in the world, or at
least to something other than the subject), a sense of self (many experiences include a reference
to one’s body or even to one’s narrative self), figure–ground segregation (an experience usually
includes some object and some background), situatedness (an experience is often bound to a
time and a place), will (experience offers the opportunity for action), and affect (experience is
often colored by some mood), among others. However, experiences lacking each of these candidate properties are conceivable—that is, conceiving of them does not lead to self-contradiction or absurdity. They are also achievable, as revealed by altered states of consciousness
reached through dreaming, meditative practices, or drugs.


**Postulates of physical existence**


To account for the many regularities of experience (Box 1), it is a good inference to assume
the existence of a world that persists independently of one’s experience ( _realism_ ). From
within consciousness, we can probe the physical existence of things outside of our experience
operationally—through observations and manipulations. To be granted physical existence,
something should have the power to “take a difference” (be affected) and “make a difference”
(produce effects) in a reliable way ( _physicalism_ ). IIT also assumes “operational reductionism,” which means that, ideally, to establish what exists in physical terms, one would start
from the smallest units that can take and make a difference, so that nothing is left out
( _atomism_ ).
By characterizing physical existence operationally as cause–effect power, IIT can proceed to
formulate the axioms of phenomenal existence as postulates of physical existence. This


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 4 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


establishes the requirements for the _substrate of consciousness_, where “substrate” is meant
operationally as a set of units that can be observed and manipulated.


**Existence** The substrate of consciousness can be characterized operationally by _cause–effect_
_power_ : its units must _take and make a difference_ .


Building from this “zeroth” postulate, IIT formulates the five axioms in terms of postulates
of physical existence that must be satisfied by the substrate of consciousness:


**Intrinsicality** Its cause–effect power must be _intrinsic_ : it must take and make a difference
_within itself_ .


**Information** Its cause–effect power must be _specific_ : it must be in _this state_ and select _this_
_cause–effect state_ .
This state is the one with maximal _intrinsic information_ ( _ii_ ), a measure of the difference a
system takes or makes over itself for a given cause state and effect state.


**Integration** Its cause–effect power must be _unitary_ : it must specify its cause–effect state as _a_
_whole set_ of units, irreducible to separate subsets of units.
Irreducibility is measured by _integrated information_ ( _φ_ ) over the substrate’s minimum
partition.


**Exclusion** Its cause–effect power must be _definite_ : it must specify its cause–effect state as _this_
_whole set_ of units.
This is the set of units that is maximally irreducible, as measured by maximum _φ_ ( _φ_ *). This
set is called a _maximal substrate_, also known as a _complex_ [8, 13].


**Composition** Its cause–effect power must be _structured_ : subsets of its units must specify
cause–effect states over subsets of units ( _distinctions_ ) that can overlap with one another
( _relations_ ), yielding a _cause–effect structure_ or _Φ_                           - _structure_ (“Phi-structure”) that is _the way_
_it is_ .


Distinctions and relations, in turn, must also satisfy the postulates of physical existence:
they must have cause–effect power, within the substrate of consciousness, in a specific, unitary,
and definite way (they do not have components, being components themselves). They thus
have an associated _φ_ value. The _Φ_ -structure unfolded from a complex corresponds to the quality of consciousness. The sum total of the _φ_ values of the distinctions and relations that compose the _Φ_ -structure measures its _structure integrated information Φ_ (“big Phi,” “structure
Phi”) and corresponds to the quantity of consciousness.
According to IIT, the physical properties characterized by the postulates are necessary and
sufficient for an entity to be conscious. They are necessary because they are needed to account
for the properties of experience that are essential, in the sense that it is inconceivable for an
experience to lack any one of them. They are also sufficient because no additional property of
experience is essential, in the sense that it is conceivable for an experience to lack that property.
Thus, no additional physical property is a necessary requirement for being a substrate of
consciousness.
The postulates of IIT have been and are being applied to account for the location of the substrate of consciousness in the brain [4] and for its loss and recovery in physiological and pathological conditions [22, 23].


**The explanatory identity between experiences and** _**Φ**_ **-structures**


Having determined the necessary and sufficient conditions for a substrate to support consciousness, IIT proposes an explanatory identity: every property of an experience is accounted


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 5 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


for in full by the physical properties of the _Φ_ -structure unfolded from a maximal substrate (a
complex) in its current state, with no further or “ad hoc” ingredients. That is, there must be a
one-to-one correspondence between the way the experience feels and the way distinctions and
relations are structured. Importantly, the identity is not meant as a correspondence between
the properties of two separate things. Instead, the identity should be understood in an explanatory sense: the intrinsic (subjective) feeling of the experience can be explained extrinsically
(objectively, _i.e_ ., operationally or physically) in terms of cause–effect power (see (4) in S1
Notes).
The explanatory identity has been applied to account for how space feels (spatial extendedness) and which neural substrates may account for it [11]. Ongoing work is applying the identity to provide a basic account of the feeling of temporal flow [24] and that of objects [25].


Box 1. Methodological guidelines of IIT


Inference to a good explanation


We should generally assume that an explanation is good if it can account for a broad set
of facts ( _scope_ ), does so in a unified manner ( _synthesis_ ), can explain facts precisely ( _speci-_
_ficity_ ), is internally coherent ( _self-consistency_ ), is coherent with our overall understanding of things ( _system consistency_ ), is simpler than alternatives ( _simplicity_ ), and can make
testable predictions ( _scientific validation_ ). For example, IIT 4.0 aims at expressing the
postulates of intrinsicality, information, integration, and exclusion in a self-consistent
manner when applied to systems, causal distinctions, and relations (see formulas).


Realism


We should assume that something exists (and persists) independently of our own experience. This is a much better hypothesis than solipsism, which explains nothing and predicts nothing. Although IIT starts from our own phenomenology, it aims to account for
the many regularities of experience in a way that is fully consistent with realism.


Operational physicalism


To assess what exists independently of our own experience, we should employ an operational criterion: we should systematically observe and manipulate a substrate’s units and
determine that they can indeed take and make a difference in a way that is reliable.
Doing so demonstrates a substrate’s cause–effect power—the signature of physical existence. Ideally, cause–effect power is fully captured by a substrate’s transition probability
matrix (TPM) (1). This assumption is embedded in IIT’s zeroth postulate.


Operational reductionism (“atomism”)


Ideally, we should account for what exists physically in terms of the smallest units we
can observe and manipulate, as captured by unit TPMs. Doing so would leave nothing
unaccounted for. IIT assumes that, in principle, it should be possible to account for
everything purely in terms of cause–effect power—cause–effect power “all the way
down” to conditional probabilities between atomic units (see (5) in S1 Notes). Eventually, this would leave neither room nor need to assume intrinsic properties or laws.


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 6 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


Intrinsic perspective


When accounting for experience itself in physical terms, existence should be evaluated
from the intrinsic perspective of an entity—what exists for the entity itself—not from the
perspective of an external observer. This assumption is embedded in IIT’s postulate of
intrinsicality and has several consequences. One is that, from the intrinsic perspective,
the quality and quantity of existence must be observer-independent and cannot be arbitrary. For instance, information in IIT must be relative to the specific state the entity is
in, rather than an average of states as assessed by an external observer. Similarly, it
should be evaluated based on the uniform distribution of possible states, as captured by
the entity’s TPM (1), rather than on an observed probability distribution. By the same
token, units outside the entity should be treated as background conditions that do not
contribute directly to what the system is. The intrinsic perspective also imposes a tension
between expansion and dilution (see below and [12, 14]): from the intrinsic perspective
of a system (or a mechanism within the system), having more units may increase its
informativeness (cause–effect power measured as deviation from chance), while at the
same time diluting its selectivity (ability to concentrate cause–effect power over a specific
state).


**Overview of IIT’s framework**


IIT 4.0 aims at providing a formal framework to characterize the cause–effect structure of a
substrate in a given state by expressing IIT’s postulates in mathematical terms. In line with
operational physicalism (Box 1), we characterize a substrate by the transition probability function of its constituting units.
On this basis, the IIT formalism first identifies sets of units that fulfill all required properties
of a substrate of consciousness according to the postulates of physical existence. First, for a
candidate system, we determine a maximal cause–effect state based on the intrinsic information (ii) that the system in its current state specifies over its possible cause states and effect
states. We then determine the maximal substrate based on the integrated information ( _φs_, “system phi”) of the maximal cause–effect state. To qualify as a substrate of consciousness, a candidate system must specify a maximum of integrated information ( _φ_ [∗] _s_ [) compared to all]
competing candidate systems with overlapping units.
The second part of the IIT formalism _unfolds_ the cause–effect structure specified by a maximal substrate in its current state, its _Φ_                        - _structure_ . To that end, we determine the distinctions
and relations specified by the substrate’s subsets according to the postulates of physical existence. Distinctions are cause–effect states specified over subsets of substrate units ( _purviews_ )
by subsets of substrate units ( _mechanisms_ ). Relations are congruent overlaps among distinctions’ cause and/or effect states. Distinctions and relations are also characterized by their integrated information ( _φd_, _φr_ ). The _Φ_ -structure they compose corresponds to the quality of the
experience specified by the substrate; the sum of their _φd_ / _r_ values corresponds to its quantity
( _Φ_ ).
While IIT must still be considered as work in progress, having undergone successive refinements, IIT 4.0 is the first formulation of IIT that strives to characterize _Φ_ -structures completely
and to do so based on measures that satisfy the postulates uniquely. For a comparison of the
updated framework with IIT 1.0, 2.0, and 3.0, see S2 Text.


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 7 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**Substrates, transition probabilities, and cause–effect power**


IIT takes physical existence as synonymous with having cause–effect power, the ability to take
and make a difference. Consequently, a substrate _U_ with state space O _U_ is operationally
defined by its potential interactions, assessed in terms of conditional probabilities (physicalism, Box 1). We denote the complete transition probability function of a substrate _U_ over a system update _u_ ! _u_                   - as


T _U_                           - _p_ ð _u_                           - j _u_ Þ _;_ _u;_                           - _u_ 2 O _U:_ ð1Þ


A substrate in IIT can be described as a stochastic system _U_ = { _U_ 1, _U_ 2, . . ., _Un_ } of _n_ interacting
units with state space O _U_ ¼ [Q] _i_ [O] _Ui_ [and current state] _[ u]_ [ 2][ O] _[U]_ [. We define units in state] _[ u]_ [ as a set]

of tuples, where each tuple contains the unit and the state of the unit, _i.e_ ., _u_ = {( _Ui_, state( _Ui_ )) :
_Ui_ 2 _U_ }. This allows us to define set operations over _u_ that consider both the units and their
states. O _U_ is the set of all possible such tuple sets, corresponding to all the possible states of _U_ .
We assume that the system updates in discrete steps, that the state space O _U_ is finite, and that
the individual random variables _Ui_ 2 _U_ are conditionally independent from each other given
the preceding state of _U_ :


Y _n_
_p_ ð _u_                                - j _u_ Þ ¼ _p_ ð _u_                                - _i_ j _u_ Þ _:_ ð2Þ

_i_ ¼1


Finally, we assume a complete description of the substrate, which means that we can determine
the conditional probabilities in (2) for every system state, with _p_ ð _u_                       - j _u_ Þ ¼ _p_ ð _u_                       - j doð _u_ ÞÞ [10,
26–28], where the “do-operator” do( _u_ ) indicates that _u_ is imposed by intervention. This
implies that _U_ must correspond to a causal network [10], and T _U_ is a transition probability
matrix (TPM) of size |O _U_ | (see (6) in S1 Notes).
The TPM T _U_, which forms the starting point of IIT’s analysis, serves as an overall description of a system’s causal evolution under all possible interventions: what is the probability that
the system will transition into each of its possible states upon being initialized into every possible state (Fig 1)? (Notably, there is no additional role for intrinsic physical properties or laws of
nature.) In practice, a causal model will be neither complete nor atomic (capturing the smallest
units that can be observed and manipulated), but will capture the relevant features of what we
are trying to explain and predict (see (7) in S1 Notes).
In the “Results and discussion” section, the IIT formalism will be applied to extremely simple, simulated networks, rather than causal models of actual substrates. The cause–effect structures derived from these simple networks only serve as convenient illustrations of how a
hypothetical substrate’s cause–effect power can be unfolded.


**Implementing the postulates**


In what follows, our goal is to evaluate whether a hypothetical substrate (also called “system”)
satisfies all the postulates of IIT. To that end, we must verify whether the system has cause–
effect power that is intrinsic, specific, integrated, definite, and structured.
**Existence.** According to IIT, existence understood as cause–effect power requires the
capacity to both take _and_ make a difference (see Box 2, Principle of being). On the basis of a
complete description of the system in terms of interventional conditional probabilities (T _U_ )
(1), cause–effect power can be quantified as causal _informativeness_ . Cause informativeness
measures how much a potential cause increases the probability of the current state, and effect
informativeness how much the current state increases the probability of a potential effect (as
compared to chance).


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 8 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**Fig 1.** **Identifying substrates of consciousness through the postulates of existence, intrinsicality, information, integration, and exclusion.** (A) The substrate _S_ =
_aBC_ in state (−1, 1, 1) (lowercase letters for units indicated state “−1,” uppercase letters state “+1”) is the starting point for applying the postulates. The substrate
updates its state according to the depicted transition probability matrix (TPM) (gray shading indicates probability value from white (p = 0) to black (p = 1); each unit
follows a logistic equation (see “Results” for definition) with k = 4.0 and connection weights as indicated in the causal model). Existence requires that the substrate
must have cause–effect power, meaning that the TPM among substrate states must differ from chance. (B) Intrinsicality requires that a candidate substrate, for
example, units _aB_, has cause–effect power over itself. Units outside the candidate substrate (in this case, unit _C_ ) are treated as background conditions. The
corresponding cause and effect TPMs (Tc and Te) of system _aB_ are depicted on the right. (C) Information requires that the candidate substrate _aB_ selects a specific
cause–effect state ( _s_ [0] ). This is the cause state (red) and effect state (green) for which intrinsic information (ii) is maximal. Bar plots on the right indicate the three
probability terms relevant for computing ii _c_ (7) and ii _e_ (5): the selectivity (light colored bar), as well as the constrained (dark colored bar) and unconstrained (gray bar)
effect probabilities in the informativeness term. (D) Integration requires that the substrate specifies its cause–effect state irreducibly (“as one”). This is established by
identifying the minimum partition (MIP; _θ_ [0] ) and measuring the integrated information of the system ( _φs_ )—the minimum between cause integrated information ( _φc_ )
and effect integrated information ( _φe_ ). Here, gray bars represent the partitioned probability required for computing _φc_ (20) and _φe_ (19). (E) Exclusion requires that the
substrate of consciousness is definite, including some units and excluding others. This is established by identifying the candidate substrate with the maximum value of
system integrated information ( _φ_ [∗] _s_ [)—the maximal substrate, or complex. In this case,] _[ aB]_ [ is a complex since its system integrated information (] _[φ][s]_ [ = 0.17) is higher than]
that of all other overlapping systems (for example, subset _a_ with _φs_ = 0.04 and superset _aBC_ with _φs_ = 0.13).


[https://doi.org/10.1371/journal.pcbi.1011465.g001](https://doi.org/10.1371/journal.pcbi.1011465.g001)


**Intrinsicality.** Building upon the existence postulate, the intrinsicality postulate further
requires that a system exerts cause–effect power _within itself_ . In general, the systems we want
to evaluate are open systems _S_                     - _U_ that are part of a larger “universe” _U_ . From the intrinsic
perspective of a system _S_ (see Box 1), the set of the remaining units _W_ = _U_ \ _S_ merely act as
background conditions that do not contribute directly to cause–effect power. To enforce this,
we causally marginalize the background units, conditional on the current state of the universe,
rendering them causally inert (see “Identifying substrates of consciousness” for details).
**Information.** The information postulate requires that a system’s cause–effect power be
specific: the system in its current state must select a specific cause–effect state for its units.
Based on the _principle of maximal existence_ (Box 2), this is the state for which intrinsic information is maximal—the _maximal cause–effect state_ . _Intrinsic information_ (ii) measures the difference a system takes or makes over itself for a given cause and effect state as the product of


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 9 / 45



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Integrated information theory (IIT) 4.0 Formulating the properties of phenomenal existence in physical terms_extracted/images/Integrated-information-theory-(IIT)-4.0-Formulating-the-properties-of-phenomenal-existence-in-physical-terms.pdf-8-0.png)
PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


informativeness and selectivity. As we have seen (existence), _informativeness_ quantifies the
causal power of a system in its current state as a reduction of uncertainty with respect to
chance. _Selectivity_ measures how much cause–effect power is concentrated over that specific
cause or effect state. Selectivity is reduced by uncertainty in the cause or effect state with
respect to other potential cause and effect states.
From the intrinsic perspective of the system, the product of informativeness and selectivity
leads to a tension between _expansion_ and _dilution_, whereby a system comprising more units
may show increased deviation from chance but decreased concentration of cause–effect power
over a specific state [12, 14].
**Integration.** By the integration postulate, it is not sufficient for a system to have cause–
effect power within itself and select a specific cause–effect state: it must also specify its maximal
cause–effect state in a way that is irreducible. This can be assessed by _partitioning_ the set of
units that constitute the system into separate parts. The system integrated information ( _φs_ )
then quantifies how much the intrinsic information specified by the maximal state is reduced
due to the partition (see (8) in S1 Notes). Integrated information is evaluated over the partition
that makes the least difference, the _minimum partition_ (MIP), in accordance with the _principle_
_of minimal existence_ (see Box 2).
Integrated information is highly sensitive to the presence of _fault lines_ —partitions that separate parts of a system that interact weakly or directionally [13].
**Exclusion.** Many overlapping sets of units may have a positive value of integrated information ( _φs_ ). However, the exclusion postulate requires that the substrate of consciousness
must be constituted of a definite set of units, neither less nor more. Moreover, units, updates,
and states must have a definite grain. Operationally, the exclusion postulate is enforced by
selecting the set of units that maximizes integrated information over itself ( _φ_ [∗] _s_ [), based again on]
the principle of maximal existence (see Box 2). That set of units is called a _maximal substrate_,
or _complex_ . Over a universal substrate, sets of units for which integrated information is maximal compared to all competing candidate systems with overlapping units can be assessed
recursively (by identifying the first complex, then the second complex, and so on).
**Composition.** Once a complex has been identified, composition requires that we characterize its _cause–effect structure_ by considering all its subsets and fully _unfolding_ its cause–effect
power.
Usually, causal models are conceived in holistic terms, as state transitions of the system as a
whole (1), or in reductionist terms, as a description of the individual units of the system and
their interactions (2) [29]. However, to account for the structure of experience, considering only
the cause–effect power of the individual units or of the system as a whole would be insufficient

[17, 29]. Instead, by the composition postulate, we have to evaluate the system’s cause–effect
structure by considering the cause–effect power of its subsets as well as their causal relations.
To contribute to the cause–effect structure of a complex, a system subset must both take _and_
make a difference (as required by existence) _within_ the system (as required by intrinsicality). A
subset _M_                     - _S_ in state _m_ 2 O _M_ is called a _mechanism_ if it _links_ a cause and effect state over subsets of units _Zc_ / _e_                        - _S_, called _purviews_ . A mechanism together with the cause and effect state it
specifies is called a _causal distinction_ . Distinctions are evaluated based on whether they satisfy
all the postulates of IIT (except for composition). For every mechanism, the cause–effect state is
the one having maximal intrinsic information (ii), and the cause and effect purviews are those
yielding the maximum value of integrated information ( _φd_ ) within the complex—that is, those
that are maximally irreducible. By the information postulate, the cause–effect power of a complex must be specific, which means that it selects a specific cause–effect state at the system level.
Consequently, the distinctions that exist for the complex are only those whose cause–effect state


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 10 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


is congruent with the cause–effect state of the complex as a whole (incongruent distinctions are
not components of the complex and its specific cause–effect power because they would violate
the specificity postulate, according to which the experience can only be “this one”).
Distinctions whose cause or effect states overlap congruently within the system (over the
same subset of units in the same state) are _bound_ together by _causal relations_ . Relations also
have an associated value of integrated information ( _φr_ ), corresponding to their irreducibility.
Together, these distinctions and relations compose the _cause–effect structure_ of the complex
in its current state. The cause–effect structure specified by a complex is called a _Φ_                       - _structure_ .
The sum of its distinction and relation integrated information amounts to the structure integrated information ( _Φ_ ) of the complex.
In the following, we will provide a formal account of the IIT analysis. The first part demonstrates how to identify complexes. This requires that we (a) determine the cause–effect state of
a system in its current state, (b) evaluate the system integrated information ( _φs_ ) over that
cause–effect state, and (c) search iteratively for maxima of integrated information ( _φ_ [∗] _s_ [) within a]
universe. The second part describes how the postulates of IIT are applied to unfold the cause–
effect structure of a complex. This requires that we identify the causal distinctions specified by
subsets of units within the complex and the causal relations determined by the way distinctions
overlap, yielding the system’s _Φ_ -structure and its structure integrated information ( _Φ_ ).


Box 2. Ontological principles of IIT


Principle of being


The _principle of being_ states that _to be is to have cause–effect power_ . In other words, in
physical, operational terms, to exist requires being able to take and make a difference.
The principle is closely related to the so-called Eleatic principle, as found in Plato’s Sophist dialogue [30]: “I say that everything possessing any kind of power, either to do anything to something else, or to be affected to the smallest extent by the slightest cause,
even on a single occasion, has real existence: for I claim that entities are nothing else but
power.” A similar principle can be found in the work of the Buddhist philosopher Dharmakīrti: “Whatever has causal powers, that really exists.” [31] Note that the Eleatic principle is enunciated as a disjunction (either to do something. . . _or_ to be affected. . .),
whereas IIT’s principle of being is presented as a conjunction (take _and_ make a
difference).


Principle of maximal existence


The _principle of maximal existence_ states that, when it comes to a requirement for existence, _what exists is what exists the most_ . The principle is offered by IIT as a good explanation for why the system state specified by the complex and the cause–effect states
specified by its mechanisms are what they are. It also provides a criterion for determining the set of units constituting a complex—the one with maximally irreducible cause–
effect power—for determining the subsets of units constituting the distinctions and relations that compose its cause–effect structure, and for determining the units’ grain. To
exemplify, consider a set of candidate complexes overlapping over the same substrate.
By the postulates of integration and exclusion, a complex must be both unitary and definite. By the maximal existence principle, the complex should be the one that lays the
greatest claim to existence as _one_ entity, as measured by system integrated information


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 11 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


( _φs_ ). For the same reason, candidate complexes that overlap over the same substrate but
have a lower value of _φs_ are excluded from existence. In other words, if having maximal
_φs_ is the reason for assigning existence as a unitary complex to a set of units, it is also the
reason to exclude from existence any overlapping set not having maximal _φs_ .


Principle of minimal existence


Another key principle of IIT is the _principle of minimal existence_, which complements
that of maximal existence. The principle states that, when it comes to a requirement for
existence, _nothing exists more than the least it exists_ . The principle is offered by IIT as a
good explanation for why, given that a system can only exist as one system if it is irreducible, its degree of irreducibility should be assessed over the partition across which it is
least irreducible (the minimum partition). Similarly, a distinction within a system can
only exist as one distinction to the extent that it is irreducible, and its degree of irreducibility should be assessed over the partition across which it is least irreducible. Moreover,
a set of units can only exist as a system, or as a distinction within the system, if it specifies
both an irreducible cause and an irreducible effect, so its degree of irreducibility should
be the minimum between the irreducibility on the cause side and on the effect side (see
(9) in S1 Notes).


**Identifying substrates of consciousness**

Our starting point is a substrate _U_ in current state _u_ with TPM T _U_ (1). We consider any subset
_s_                         - _u_ as a possible complex and refer to a set of units _S_                         - _U_ as a candidate system. (Note that _s_
and _u_ are sets of tuples containing both the units and their states.).
By the intrinsicality postulate, the units _W_ = _U_ \ _S_ are background conditions, and do not
contribute directly to the cause–effect power of the system. To discount the contribution of
background units, they are _causally marginalized_, conditional on the current state of the universe. This means that the background units are marginalized based on a uniform marginal
distribution, updated by conditioning on _u_ . The process is repeated separately for each unit in
the system, and they are then combined using a product (in line with conditional independence), which eliminates any residual correlations due to the background units. Accordingly,
we obtain two TPMs T _e_ and T _c_ (for evaluating effects and causes, respectively) for the candidate system _S_ . For evaluating effects, the state of the background units is fully determined by
the current state of the universe. The corresponding TPM, T _e_, is used to identify the effect of
the current state:


T _e_ ¼ T _e_ ðT _U; u; w_ Þ � _pe_ ð� _s_ j _s_ Þ ¼ _p_ ð� _s_ j _s; w_ Þ _;_ _s;_                      - _s_ 2 O _S;_ ð3Þ


where _w_ = _u_ \ _s_ . For evaluating causes, knowledge of the current state is used to compute the
probability distribution over potential prior states of the background units, which is not necessarily uniform or deterministic. The corresponding TPM, T _c_, is used to evaluate the cause of
the current state:



X



P



Yj _S_ j
T _c_ ¼ T _c_ ðT _U; u; w_ Þ � _pc_ ð _s_ j � _s_ Þ ¼



�P 
^ _s_ _[p]_ [ð] _[u]_ [ j] [^] _[s][;]_ _[w]_ [�] [Þ]
~~P~~ _;_ _s;_ - _s_ 2 O _S:_ ð4Þ



^ _s_ _[p]_ [ð] _[u]_ [ j] [^] _[s][;]_ _[w]_ [�] [Þ]
~~P~~



_i_ ¼1



_p_ ð _si_ j � _s;_  - _w_ Þ
_w_ 


_u_ ^ _[p]_ [ð] _[u]_ [ j] _[u]_ [^][Þ]



[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 12 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


In both TPMs, the background units _W_ are rendered causally inert, so that causes and effects
are evaluated from the intrinsic perspective of the system.
The intrinsic information ii _c_ / _e_ is a measure of the intrinsic cause or effect power exerted by
a system _S_ in its current state _s_ over itself by selecting a specific cause or effect state � _s_ . The
cause–effect state for which intrinsic information (ii _c_ and ii _e_ ) is maximal is called the maximal
cause–effect state _s_ [0] ¼ f _s_ [0] _c_ _[;][ s]_ [0] _e_ [g][. The integrated information] _[ φ][s]_ [ is a measure of the irreducibility]
of a cause–effect state, compared to the directional system partition _θ_ [0] that affects the maximal
cause–effect state the least (minimum partition, or MIP). Systems for which integrated information is maximal ( _φ_ [∗] _s_ [) compared to any competing candidate system with overlapping units]
are called maximal substrates, or complexes.
The IIT 4.0 formalism to measure a system’s integrated information _φs_ and to identify maximal substrates was first presented in [13]. An example of how to identify complexes in a simple system is given in Fig 1, while a comparison with prior accounts (IIT 1.0, IIT 2.0, and IIT
3.0) can be found in S2 Text. An outline of the IIT algorithm is included in S1 Fig.


**Existence, intrinsicality, and information: Determining the maximal**
**cause–effect state of a candidate system**

Given a causal model with corresponding TPMs T _e_ (3) and T _c_ (4), we wish to identify the
maximal cause–effect state specified by a system in its current state over itself and to quantify
the causal power with which it does so. In this way, we quantify the cause–effect power of a system from its intrinsic perspective, rather than from the perspective of an outside observer (see
Box 1).
**System intrinsic information ii.** Intrinsic information iið _s;_                      - _s_ Þ measures the causal power
of a system _S_ over itself, for its current state _s_, over a specific cause or effect state � _s_ . Intrinsic
information depends on interventional conditional probabilities and unconstrained probabilities of cause or effect states and is the product of selectivity and informativeness.
On the effect side, intrinsic effect information ii _e_ of the current state _s_ over a possible effect
state � _s_ is defined as:

                         -                          
ii _e_ ð _s;_                                                     - _s_ Þ ¼ _pe_ ð� _s_ j _s_ Þ log _pep_ ð _e_                                                     - _s_ ð� _s_ j _s_ Þ Þ _;_ ð5Þ



where _pe_ ð� _s_ j _s_ Þ (3) is the interventional conditional probability that the current state _s_ produces
the effect state � _s_, as indicated by T _e_ .
The interventional unconstrained probability _pe_ ð� _s_ Þ



_pe_ ð� _s_ Þ ¼ jO _S_ j




- 1 [X]



_pe_ ð� _s_ j _s_ Þ _;_ ð6Þ



_s_ 2O _S_


is defined as the marginal probability of � _s_, averaged across all possible current states of _S_ with
equal probability (where |O _S_ | denotes the cardinality of the state space O _S_ ).
On the cause side, intrinsic cause information ii _c_ of the current state _s_ over a possible cause
state � _s_ is defined as:

                          -                          
ii _c_ ð _s;_                                                    - _s_ Þ ¼ _pc_ [ð][�] _[s]_ [j] _[ s]_ [Þ][ log] _pc_ ð _s_ j � _s_ Þ _;_ ð7Þ
_pc_ ð _s_ Þ


where _pc_ ð _s;_                  - _s_ Þ (4) is the interventional conditional probability that the cause state � _s_ produces
the current state _s_, as indicated by T _c_, and the interventional unconstrained probability is
again defined as the marginal probability of _s_, averaged across all possible cause states of _S_ with


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 13 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


equal probability,



_pc_ ð _s_ Þ ¼ jO _S_ j




- 1 [X]

_pc_ ð _s_ j � _s_ Þ _:_ ð8Þ

  - _s_ 2O _S_



Moreover, _pc_ [ð][�] _[s]_ [j] _[ s]_ [Þ][ (4)][ is the interventional conditional probability that the current state]
_s_ 2 O _S_ was produced by � _s_ ; it is derived from T _c_ using Bayes’ rule, where we again assign a uniform prior to the possible cause states � _s_,



_pc_ [ð][�] _[s]_ [j] _[ s]_ [Þ ¼] _[p][c]_ [ð] _[s]_ [ j][ �] _[s]_ [Þ �j][O] _[S]_ [j]




[ �] _[s]_ [Þ �j][O] _[S]_ [j] ¼ ~~X~~ _pc_ ð _s_ j � _s_ Þ

_pc_ ð _s_ Þ _p_ ð _s_ j




- 1



_:_
ð9Þ
_pc_ ð _s_ j ^ _s_ Þ



^ _s_ 2O _S_


**Informativeness (over chance).** In (5) and (7), the logarithmic term (in base 2 throughout) is called _informativeness_ . Note that informativeness is expressed in terms of ‘forward’
probabilities (probability of a subsequent state given the current state) for both ii _e_ (5) and ii _c_
(7). However, ii _e_ (5) evaluates the increase in probability of the effect state due to the current
state based on T _e_, while ii _c_ (7) evaluates the increase in probability of the current state due to
the cause state based on T _c_ .
In line with the existence postulate, a system _S_ in state _s_ has cause–effect power (it takes and
makes a difference) if it raises the probability of a possible effect state compared to chance,
which is to say compared to its unconstrained probability,


                      -                       
log _pe_ ð� _s_ j _s_ Þ _>_ 0 _;_ ð10Þ
_pe_ ð� _s_ Þ


and if the probability of the current state is raised above chance by a possible cause state,


                      -                       
log _pc_ ð _s_ j � _s_ Þ _>_ 0 _:_ ð11Þ
_pc_ ð _s_ Þ


Informativeness is additive over the number of units: if a system specifies a cause or effect state
with probability _p_ = 1, its causal power increases additively with the number of units whose
states it fully specifies ( _expansion_ ), given that the chance probability of all states decreases
exponentially.
**Selectivity (over states).** From the intrinsic perspective of a system, cause–effect power
over a specific cause or effect state depends not only on the deviation from chance it produces,
but also on how its probability is concentrated on that state, rather than being diluted over
other states. This is measured by the _selectivity_ term in front of the logarithmic term in (5) and
(7), corresponding to the conditional probability _pc_ [ð][�] _[s]_ [j] _[ s]_ [Þ][ or] _[ p]_ _e_ [ð][�] _[s]_ [j] _[ s]_ [Þ][ of that specific cause or]
effect state. (Note that here, on the cause side, we use the ‘backward’ probability (probability of
a prior state given the current state) obtained through Bayes’ rule, while we use the ‘forward’
probability of the effect state � _s_ given _s_ on the effect side.) Selectivity means that if _p <_ 1, the system’s causal power becomes subadditive ( _dilution_ ) (see [14] for details). For example, as
shown in [12], if an unconstrained unit is added to a fully specified unit, intrinsic information
does not just stay the same, but decreases exponentially. From the intrinsic perspective of the
system, the informativeness of a specific cause or effect state is diluted because it is spread over
multiple possible states, yet the system must select only one state.
Altogether, taking the product of informativeness and selectivity leads to a tension between
expansion and dilution: a larger system will tend to have higher informativeness than a smaller


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 14 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


system because it will deviate more from chance, but it will also tend to have lower selectivity
because it will have a larger repertoire of states to select from.
Because of the selectivity term, intrinsic information is reduced by indeterminism and
degeneracy. As shown in [13], indeterminism decreases the probability of the selected effect
state because it implies that the same state can lead to multiple states. In turn, degeneracy
decreases the probability of the selected cause state because it implies that multiple states can
lead to the same state, even in a deterministic system.
The intrinsic information ii is quantified in units of _intrinsic bits_, or _ibits_, to distinguish it
from standard information-theoretic measures (which are typically additive). Formally, the
_ibit_ corresponds to a point-wise information value (measured in bits) weighted by a
probability.
**The maximal cause–effect state.** Taking the product of informativeness and selectivity
on the system’s cause and effect sides captures the postulates of existence (taking and making a
difference) and intrinsicality (taking and making a difference over itself) for each possible
cause or effect state, as measured by intrinsic information. However, the information postulate
further requires that the system selects a specific cause or effect state. The selection is determined by the principle of maximal existence (Box 1): the cause or effect specified by the system
should be the one that maximizes intrinsic information. On the effect side (and similarly for
the cause side, see S1 Fig),


_s_ [0] _e_ [ð][T] _e_ _[;][ s]_ [Þ] ¼ argmax ii _e_ ð _s;_                                      - _s_ Þ

                                                     - _s_ 2O _S_




- _s_ 2O _S_ _pe_ ð� _s_ j _s_ Þ log _pep_ ð _e_ - _s_ ð� _s_ j _s_ Þ Þ



¼ argmax




- - ð12Þ

_pe_ ð� _s_ j _s_ Þ _:_



The system’s intrinsic effect information is the value of ii _e_ (5) for its maximal effect state:




[j] _[ s]_ [Þ][ log] _pe_ ð� _s_ j _s_ Þ

- _s_ 2O _S_ _[p][e]_ [ð][�] _[s]_ _pe_ ð� _s_ Þ



ii _e_ ðT _e; s_ Þ ≔ ii _e_ ð _s; s_ [0] _e_ [Þ ¼][ max]




- 
_pe_ ð� _s_ j _s_ Þ _:_ ð13Þ



We have made the dependency of _s_ [0] and ii _e_ on T _e_ explicit in (12) and (13) to highlight that, for
intrinsic information to properly assess cause–effect power, all probabilities must be derived
from the system’s interventional transition probability function, while imposing a uniform
prior distribution over all possible system states. If ii _e_ ðT _e; s_ Þ ¼ 0, the system _S_ in state _s_ has no
causal power. This is the case if and only if _pe_ ð� _s_ j _s_ Þ ¼ _pe_ ð� _s_ Þ for every � _s_ [14] (and likewise, it
can be shown that ii _c_ ðT _c; s_ Þ ¼ 0 if and only if _pc_ ð _s_ j � _s_ Þ ¼ _pc_ ð _s_ Þ for every � _s_ .) It is worthwhile to
mention that when ii _e_ ðT _e; s_ Þ 6¼ 0, the system state _s_ always increases the probability of the
intrinsic effect state compared to chance. Similarly, when ii _c_ ðT _c; s_ Þ 6¼ 0 the intrinsic cause
state increases the probability of the system state, satisfying (11). Note also that a system’s
intrinsic cause–effect state does not necessarily correspond to the actual cause and effect states
(what actually happened before / will happen after) in the dynamical evolution of the system,
which typically also depends on extrinsic influences. (For an account of actual causation
according to the causal principles of IIT, see [10].).
**Intrinsic difference.** Because consciousness is the way it is, the formulation of its properties in physical, operational terms should be unique and based on quantities that uniquely satisfy the postulates [12, 32]. Intrinsic information is formulated as a product of selectivity and
informativeness based on the notion of intrinsic difference (ID) [14]. This is a measure of the
difference between two probability distributions which uniquely satisfies three properties (causality, intrinsicality, and specificity) that align with the postulates of IIT (but also have independent justification):


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 15 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**causality (Existence)** : the measure is zero if and only if the system does not make a difference


**intrinsicality (Intrinsicality)** : the measure increases if the system is expanded without noise
(expansion) and decreases if the system is expanded without signal (dilution)


**specificity (Information)** : the measure reflects the cause–effect power of a specific state over a
specific cause and effect state.


The properties uniquely satisfied by the ID are described in a general mathematical context
in [14], as well as some additional discussion in S2 Text.
Note that, on the effect side, ii _e_ is formally equivalent to the ID between the constrained
effect repertoire _pe_ ð� _s_ j _s_ Þ and the unconstrained effect repertoire _pe_ ð� _s_ Þ. On the cause side, the
application of Bayes rule to compute _pc_ [ð][�] _[s]_ [j] _[ s]_ [Þ][ as the selectivity term means that ii] _[c]_ [ is not]
strictly equivalent to the ID between two probability distributions. However, analogously to
the effect formulation, it is defined as the product of selectivity and informativeness of
causes.


**Integration: Determining the irreducibility of a candidate system**


Having identified the maximal cause–effect state _s_ [0] ¼ f _s_ [0] _c_ _[;][ s]_ [0] _e_ [g][ of a candidate system] _[ S]_ [ in its cur-]
rent state _s_, the next step is to evaluate whether the system specifies the cause–effect state of its
units in a way that is _irreducible_, as required by the integration postulate: a candidate system
can only be a substrate of consciousness if it is _one_ system—that is, if it cannot be subdivided
into subsets of units that exist separately from one another.
**Directional system partitions.** To that end, we define a set of _directional_ system partitions
Θ( _S_ ) that divide _S_ into _k_                - 2 parts f _S_ [ð] _[i]_ [Þ] g _ki_ ¼1 [, such that]




[ _k_
_S_ [ð] _[i]_ [Þ] 6¼ � _;_ _S_ [ð] _[i]_ [Þ] \ _S_ [ð] _[j]_ [Þ] ¼ � _;_ and


_i_ ¼1



_S_ [ð] _[i]_ [Þ] ¼ _S:_ ð14Þ



In words, each part _S_ [(] _[i]_ [)] must contain at least one unit, there must be no overlap between any
two parts _S_ [(] _[i]_ [)] and _S_ [(] _[j]_ [)], and every unit of the system must appear in exactly one part. For each
part _S_ [(] _[i]_ [)], the partition removes the causal connections of that part with the rest of the system
in a directional manner: either the part’s inputs, outputs, or both are replaced by independent “noise” (they are “cut” by the partition in the sense that their causal powers are substituted by chance). Directional partitions are necessary because, from the intrinsic perspective
of a system, a subset of units that cannot affect the rest of the system, or cannot be affected
by it, cannot truly be a part of the system. In other words, to be a part of a system, a subset of
units must be able to interact with the rest of the system in both directions (cause _and_
effect).
A partition _θ_ 2 Θ( _S_ ) thus has the form



ðd _kk_ Þ [g] _[;]_ ð15Þ



y ¼ f _S_



ð1Þ ð2Þ
d1 _[;][ S]_ d2 _[;]_ [ . . .] _[ ;][ S]_



where _δi_ 2 {, !, $} indicates whether the inputs ( ), outputs (!), or both ($) are cut for
a given part. For each part _S_ [(] _[i]_ [)], we can then identify a set of units _X_ [(] _[i]_ [)] - _S_ whose inputs to _S_ [(] _[i]_ [)]

have been cut by the partition, and the complementary set _Y_ [(] _[i]_ [)] = _S_ \ _X_ [(] _[i]_ [)] whose inputs to _S_ [(] _[i]_ [)] are



[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 16 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


left intact. Specifically,



_S_ n _S_ [ð] _[i]_ [Þ] if d _i_ 2 f _;_ $g

[



_S_ [ð] _[j]_ [Þ] if d _i_ 2 f!g _:_



_X_ [ð] _[i]_ [Þ] ¼



8
>><



_S_ if _i_ ð16Þ

>>: _j_ 6¼ _i_ :



_j_ 6¼ _i_ :
d _j_ 2 f! _;_ $g



In the first case, if _δi_ 2 {, $}, all inputs to _S_ [(] _[i]_ [)] from _S_ \ _S_ [(] _[i]_ [)] are cut. In the second case, if
_δi_ 2 {!}, there may still be inputs to _S_ [(] _[i]_ [)] that are cut, which correspond to the outputs of all _S_ [(] _[j]_ [)]



with _δj_ 2 {!, $}.
Given a partition _θ_ 2 Θ( _S_ ), we define partitioned transition probability matrices T



y
_e_ [and][ T]



Given a partition _θ_ 2 Θ( _S_ ), we define partitioned transition probability matrices T y _e_ [and][ T] y _c_

in which all connections affected by the partition are “noised.” This is done by combining the
independent contributions of each unit _Sj_ 2 _S_ in line with the conditional independence
assumption (2). For the effect TPM (and analogously for the cause TPM)



T



Y _n_
y _e_ [�] _[p]_ _e_ [y][ð][�] _[s]_ [j] _[ s]_ [Þ ¼] _p_ [y] _e_ [ð][�] _[s]_ _j_ [j] _[ s]_ [Þ] _[;]_ [�] _[s][;][ s]_ [ 2][ O] _S_ _[;]_ ð17Þ



_j_ ¼1


where the partitioned probability of a unit _Sj_ 2 _S_ [(] _[i]_ [)] is defined as



_p_ [y] _e_ [ð][�] _[s]_ _j_ [j] _[ s]_ [Þ ¼ j][O] _X_ [ð] _[i]_ [Þ][j]




- 1 [X]


_x_ [ð] _[i]_ [Þ] 2O _X_ ð _i_ Þ



_pe_ ð� _sj_ j _x_ [ð] _[i]_ [Þ] _; y_ [ð] _[i]_ [Þ] Þ _;_ ð18Þ



and _y_ [(] _[i]_ [)] = _s_ \ _x_ [(] _[i]_ [)] . This means that all connections to unit _Sj_ that are affected by the partition are
_causally marginalized_ (replaced by independent noise).
**System integrated information** _**φs**_ **.** The integrated effect information _φe_ measures how
much the partition _θ_ 2 Θ _S_ reduces the probability with which a system _S_ in state _s_ 2 O _S_ specifies its effect state _s_ [0] _e_ [(12)][,]




        
_pe_ ð _s_ [0] _e_ [j] _[ s]_ [Þ]
_φe_ ðT _e; s;_ yÞ ¼ _pe_ ð _s_ [0] _e_ [j] _[ s]_ [Þ] ���� log ����� _:_ ð19Þ
_p_ [y] _e_ [ð] _[s]_ [0] _e_ [j] _[ s]_ [Þ] þ



Note that _φe_ has the same form as the intrinsic information ii _e_ ð _s;_ - _s_ Þ (5), with the partitioned
effect probability taking the place of the unconstrained (marginal) probability. Here, |.|+ represents the positive part operator, which sets the negative values to 0. This ensures that the system as a whole raises the probability of the effect state compared to the partitioned probability.
Likewise, the integrated cause information _φc_ is defined as




        
_pc_ ð _s_ j _s_ [0] _c_ [Þ]
_φc_ ðT _c; s;_ yÞ ¼ _pc_ [ð] _[s]_ _c_ [0] [j] _[ s]_ [Þ] ���� log ����� _:_ ð20Þ
_p_ [y] _c_ [ð] _[s]_ [ j] _[ s]_ [0] _c_ [Þ] þ



(By the principle of maximal existence, if two or more cause–effect states are tied for maximal
intrinsic information, the system specifies the one that maximizes _φc_ / _e_ .).
By the zeroth postulate, existence requires cause _and_ effect power, and the integration postulate requires that its cause–effect power be irreducible. By the principle of minimal existence
(Box 2), then, system integrated information for a given partition is the minimum of its irreducibility on the cause _and_ effect sides:


_φs_ ðT _e;_ T _c; s;_ yÞ ¼ minf _φc_ ðT _c; s;_ yÞ _; φe_ ðT _e; s;_ yÞg _:_ ð21Þ


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 17 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


Moreover, again by the principle of minimal existence, the integrated information of a system is given by its irreducibility over its minimum partition (MIP) _θ_ [0] 2 Θ _S_, such that

_φs_ ðT _e;_ T _c; s_ Þ ≔ _φs_ ðT _e;_ T _c; s;_ y [0] Þ _:_ ð22Þ



The MIP is defined as the partition _θ_ 2 Θ _S_ that minimizes the system’s integrated information, relative to the maximum possible value it could take for arbitrary TPMs T 0 _[;]_ [ T] 0 [over the]



tion, relative to the maximum possible value it could take for arbitrary TPMs T 0 _e_ _[;]_ [ T] 0 _c_ [over the]

units of system _S_



0
_e_ _[;]_ [ T]



y [0] ¼ argmin

y2Yð _S_ Þ



_φs_ ðT _e;_ T _c; s;_ yÞ
max _φ_ ðT 0 _[;]_ [ T] 0 _[;][ s][;]_



T [0] _e_ _[;]_ [T] [0] _c_



0
_e_ _[;]_ [ T]



0 ð23Þ
_c_ _[;][ s][;]_ [ y][Þ] _[ :]_



_φs_ ðT



Accordingly, the system is reducible if at least one partition _θ_ 2 Θ _S_ makes no difference to the
cause or effect probability. The normalization term in the denominator of (23) ensures that
_φs_ ðT _e;_ T _c; s_ Þ is evaluated fairly over a system’s fault lines by assessing integration relative to its
maximum possible value over a given partition. Using the _relative_ integrated information
quantifies the strength of the interactions between parts in a way that does not depend on the
number of parts and their size. As proven in [13], the maximal value of _φs_ ðT _e;_ T _c; s;_ yÞ for a



X _k_
0
_c_ _[;][ s][;]_ [ y][Þ ¼]

_i_ ¼1



given partition _θ_ is the normalization factor max

T [0] _e_ _[;]_ [T] [0] _c_



_φs_ ðT 0 _e_ _[;]_ [ T]



j _S_ [ð] _[i]_ [Þ] jj _X_ [ð] _[i]_ [Þ] j, which corre


sponds to the maximal possible number of “connections” (pairwise interactions) affected by _θ_ .
For example, as shown in [13], the MIP will correctly identify the fault line dividing a system
into two large subsets of units linked through a few interconnected units (a “bridge”), rather
than defaulting to partitions between individual units and the rest of the system. Once the
minimum partition has been identified, the integrated information across it is an _absolute_
quantity, quantifying the loss of intrinsic information due to cutting the minimum partition of
the system. (If two or more partitions _θ_ 2 Θ( _S_ ) minimize Eq (23), we select the partition with
the largest unnormalized _φs_ value as _θ_ [0], applying the principle of maximal existence.) Defining
_θ_ [0] as in (23), moreover, ensures that _φs_ ðT _e;_ T _c; s_ Þ ¼ 0 if the system is not _strongly connected_ in
graph-theoretic terms (see (10) in S1 Notes).
In summary, the system integrated information ( _φs_ ðT _e;_ T _c; s_ Þ, also called ‘ _small phi_ ’, quantifies the extent to which system _S_ in state _s_ has cause–effect power over itself as _one_ system ( _i._
_e_ ., irreducibly). _φs_ ðT _e;_ T _c; s_ Þ is thus a quantifier of irreducible existence.


**Exclusion: Determining maximal substrates (complexes)**


In general, multiple candidate systems with overlapping units may have positive values of
_φs_ ðT _e;_ T _c; s_ Þ. By the exclusion postulate, the substrate of consciousness must be definite; that
is, it must comprise a definite set of units. But which one? Once again, we employ the principle
of maximal existence (Box 2): among candidate systems competing over the same substrate
with respect to an essential requirement for existence, in this case irreducibility, the one that
exists is the one that exists the most. Accordingly, the maximal substrate, or complex, is the
candidate substrate with the maximum value of system integrated information ( _φ_ [∗] _s_ [), and over-]
lapping substrates with lower _φs_ are thus excluded from existence.
**Determining maximal substrates recursively.** Within a universal substrate _U_ 0 in state _u_ 0,
subsets of units that specify maxima of irreducible cause–effect power (complexes) can be
identified iteratively: the substrate with maximum _φ_ [∗] _s_ [is identified as a complex, the corre-]
sponding units are excluded from further consideration, the remaining units are searched for
the next maximal substrate. Formally, an iterative search is performed to find a sequence of


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 18 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


systems _S_ [∗] _k_ [�] _[U]_ _k_ [with]

_φ_ [∗] _s_ [ð][T] _e_ _[;]_ [ T] _c_ _[;][ u]_ _k_ [Þ ¼][ max] _S_                         - _Uk_ _[φ][s]_ [ð][T] _[e][;]_ [ T] _[c][;][ s]_ [Þ] _[;]_ ð24Þ


such that



_S_ [∗] _k_ [¼][ argmax]

_S_      - _Uk_



_φs_ ðT _e;_ T _c; s_ Þ _;_ ð25Þ



and _Uk_ þ1 ¼ _Uk_ n _S_ [∗] _k_ [until] _[ U][k]_ [+1][ =][ ;][ or] _[ U][k]_ [+1][ =] _[ U][k]_ [ (the units in] _[ U]_ [0][\] _[U][k]_ [+1][ still serve as background]
conditions, for details see [13]). If the maximal substrate _S_ [∗] _k_ [is not unique, and all tied systems]
overlap, the next best system that is unique is chosen instead (see S1 Text).
For any complex _S_                     - in its corresponding state _s_                     - 2 O _S_ *, overlapping substrates that specify
less integrated information ( _φs_ _< φs_ ðT _e;_ T _c; s_ [∗] Þ) are excluded. Consequently, specifying a
maximum of integrated information _φ_ [∗] _s_ [compared to all overlapping systems]


_S_ \ _S_ [~] 6¼ ; ) _φs_ ð _s_ Þ _> φs_ ð~ _s_ Þ _;_ 8 _S_ 6¼ _S_ [~]                             - _U_ ð26Þ


is a sufficient requirement for a system _S_                      - _U_ to be a complex.
As described in [13], this recursive search for maximal substrates “condenses” the universe
_U_ 0 in state _u_ 0 2 O _U_ 0 into a disjoint (non-overlapping) and exhaustive set of complexes—the
first complex, second complex, and so on.
**Determining maximal unit grains.** Above, we presented how to determine the borders of
a complex within a larger system _U_, assuming a particular grain for the units _Ui_ 2 _U_ . In principle, however, all possible grains should be considered [33, 34]. In the brain, for example, the
grain of units could be brain regions, groups of neurons, individual neurons, sub-cellular
structures, molecules, atoms, quarks, or anything finer, down to hypothetical atomic units of
cause–effect power [3, 4]. For any unit grain—neurons, for example—the grain of updates
could be minutes, seconds, milliseconds, micro-seconds, and so on. However, by the exclusion
postulate, the units that constitute a system _S_ must also be definite, in the sense of having a definite grain.
Once again, the grain is defined by the principle of maximal existence: across the possible
micro- and macroscopic levels, the “winning” grain is the one that ensures maximally irreducible existence ( _φ_ [∗] _s_ [) for the entity to which the units belong [][33][,][ 34][].]
To evaluate integrated information across grains requires a mathematical framework for
defining coarser (macro) units from finer (micro) units. Such a framework has been developed
in previous work [33–35], and is updated here to fully align with the postulates.
Supposing that _U_ = _u_ is a universe of micro units in a state, a macro unit _J_ = _j_ is a combination of a set of micro units _S_ [^]                       - _U_, and a mapping _g_ from the state _S_ [^] to the state of _J_,


_j_ ¼ _g_ ð^ _s_ Þ _;_


where


_g_ : O _S_ ^ ! O _J:_


As constituents of a complex upon which its cause–effect power rests, the units themselves
should comply with the postulates of IIT. Otherwise it would be possible to “make something
out of nothing.” Accordingly, units themselves must also be maximally irreducible, as measured by the integrated information of the units when they are treated as candidate systems
( _φs_ ); otherwise, they would not be units but “disintegrate” into their constituents. However, in
contrast to systems, units only need to be maximally irreducible _within_, because they do not


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 19 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


exist as complexes in their own right: a unit _J_ with substrate _S_ [^] qualifies as a candidate unit of a
larger system _S_ if its integrated information when treated as a candidate system ( _φs_ ) is higher
than that of any system of units (including potential macro units) that can be defined using a
subset of _S_ [^] . Out of all possible sets of such candidate units, the set of (macro) units that define
a complex is the one that maximizes the existence of the complex to which the units belong,
rather than their own existence.
In practice, the search for the maximal grain should be an iterative process, starting from
micro units: identify potential substrates for macro units ( _S_ [^] ) that are maximally irreducible
within, identify mappings _g_ that maximize the integrated information of systems of macro
units, then consider additional potential substrates for macro units, and so on iteratively, until
a global maximum is found. The iterative approach is necessary for establishing that a substrate
is maximally irreducible within, as this criterion requires consideration not only of micro
units, but also of all finer grains (potential meso units defined from subsets of _S_ [^] ).
Here we outlined an overall framework for identifying macro units consistent with the postulates. Additional details about the nature of the mapping _g_, and how to derive the transition
probabilities for a system of macro units are also informed by the postulates (see (11) in S1
Notes).


**Unfolding the cause–effect structure of a complex**


Once a maximal substrate and the associated maximal cause–effect state have been identified,
we must unfold its cause–effect power to reveal its cause–effect structure of distinctions and
relations, in line with the composition postulate. As components of the cause–effect structure,
distinctions and relations must also satisfy the postulates of IIT (save for composition).


**Composition and causal distinctions**


Causal distinctions capture how the cause–effect power of a substrate is structured by subsets
of units that specify irreducible causes and effects over subsets of its units. A candidate distinction _d_ ( _m_ ) consists of (1) a mechanism _M_                     - _S_ in state _m_ 2 O _M_ inherited from the system state _s_
2 O _S_ ; (2) a maximal cause–effect state _z_ [∗] ¼ f _zc_ [∗] _[;][ z]_ _e_ [∗][g][ over the cause and effect purviews (] _[Z][c]_ [,] _[ Z][e]_

           - _S_ ) linked by the mechanism; and (3) an associated value of irreducibility ( _φd >_ 0). A distinction _d_ ( _m_ ) is thus represented by the tuple


_d_ ð _m_ Þ ¼ ð _m; z_ [∗] _; φd_ Þ _:_ ð27Þ


For a given mechanism _m_, our goal is to identify its maximal cause _Zc_ [∗] [in state] _[ z]_ _c_ [∗] [2][ O] _Zc_ [∗] [and]
its maximal effect _Ze_ [∗] [in state] _[ z]_ _e_ [∗] [2][ O] _Ze_ [∗] [within the system, where] _[ Z]_ _c_ [∗] _[;][ Z]_ _e_ [∗] [�] _[S]_ [.]
As above, in line with existence, intrinsicality, and information, we determine the maximal
cause or effect state specified by the mechanism over a candidate purview within the system
based on the value of intrinsic information ii( _m_, _z_ ). Next, in line with integration, we determine the value of integrated information _φd_ ( _m_, _Z_, _θ_ ) over the minimum partition _θ_ [0] . In line
with exclusion, we determine the maximal cause–effect purviews for that mechanism over all
possible purviews _Z_                     - _S_ based on the associated value of irreducibility _φd_ ( _m_, _Z_, _θ_ [0] ). Finally, we
determine whether the maximal cause–effect state specified by the mechanism is congruent
with the system’s overall cause–effect state ( _zc_ [∗] [�] _[s]_ _c_ [∗][,] _[ z]_ _e_ [∗] [�] _[s]_ _e_ [∗][), in which case we conclude that it]
contributes a distinction to the overall cause–effect structure.
The updated formalism to identify causal distinctions within a system _S_ in state _s_ was first
presented in [12]. Here we provide a summary with minor adjustments on selecting _zc_ [∗] [and] _[ z]_ _e_ [∗][,]


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 20 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


the cause integrated information _φc_ ( _m_, _Z_ ), and the requirement that causal distinctions must
be congruent with the system’s maximal cause–effect state (see S2 Text).
**Existence, intrinsicality, and information: Determining the cause and effect state speci-**
**fied by a mechanism over candidate purviews.** Like the system as a whole, its subsets must
comply with existence, intrinsicality, and information. As for the system, we begin by quantifying, in probabilistic terms, the difference a subset of units _M_                       - _S_ in its current state _m_                       - _s_
takes and makes from and to subsets of units _Z_                     - _S_ (cause and effect purview). As above, we
start by establishing the interventional conditional probabilities and unconstrained probabilities from the TPMs T _c_ and T _e_ .
When dealing with a mechanism constituted by a subset of system units, it is important to
capture the constraints on a purview state _z_ that are exclusively due to the mechanism in its
state ( _m_ ), removing any potential contribution from other system units. This is done by causally marginalizing all variables in _X_ = _S_ \ _M_, which corresponds to imposing a uniform distribution as _p_ ( _X_ ) [8, 10, 12] (see (12) in S1 Notes). The effect probability of a single unit _Zi_ 2 _Z_
conditioned on the current state _m_ is thus defined as




- 1 [X]


_x_ 2O _X_



_pe_ ð _zi_ j _m_ Þ ¼ jO _X_ j



_p_ ð _zi_ j _m; x_ Þ _;_ _zi_ 2 O _Zi:_ ð28Þ



In addition, product probabilities _π_ ( _z_ j _m_ ) are used instead of conditional probabilities _pe_ ( _z_ j _m_ )
to discount correlations from units in _X_ = _S_ \ _M_ with divergent outputs to multiple units in _Z_ _S_ [8, 10, 36]. Otherwise, _X_ might introduce correlations in _Z_ that would be wrongly considered
as effects of _M_ . Based on the appropriate TPM, the probability over a set _Z_ of | _Z_ | units is thus
defined as the product of the probabilities over individual units


Yj _Z_ j
p _e_ ð _z_ j _m_ Þ ¼ _pe_ ð _zi_ j _m_ Þ _;_ _z_ 2 O _Z;_ ð29Þ

_i_ ¼1


and



Yj _M_ j
p _c_ ð _m_ j _z_ Þ ¼

_i_ ¼1



_pc_ ð _mi_ j _z_ Þ _;_ _m_ 2 O _M:_ ð30Þ



Note that for a single unit purview _πe_ ( _z_ j _m_ ) = _pe_ ( _z_ j _m_ ), and for a single unit mechanism _πc_ ( _m_ j _z_ )
= _pc_ ( _m_ j _z_ ). By using product probabilities, causal marginalization maintains the conditional
independence between units (2) because independent noise is applied to individual connections. The assumption of conditional independence distinguishes IIT’s causal powers analysis
from standard information-theoretic analyses of information flow [10, 27] and corresponds to
an assumption that variables are “physical” units in the sense that they are irreducible within
and can be observed and manipulated independently.
From Eqs (29) and (30) we can also define unconstrained probabilities




                      - 1 [X]

p _e_ ð _z_ ; _M_ Þ ¼ jO _M_ j

_m_ 2O _M_



p _e_ ð _z_ j _m_ Þ _;_ _z_ 2 O _Z;_ ð31Þ



and




 - 1 [X]


_z_ 2O _Z_



p _c_ ð _m_ ; _Z_ Þ ¼ jO _Z_ j



p _c_ ð _m_ j _z_ Þ _;_ _m_ 2 O _M:_ ð32Þ



[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 21 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


Given the set _Y_ = _S_ \ _Z_, the backward cause probability (selectivity) for a mechanism _m_ with
| _M_ | units is computed using Bayes’ rule over the product distributions


Yj _M_ j



_pc_ ð _mi_ j _z_ Þ



p _c_ [ð] _[z]_ [j] _[ m]_ [Þ ¼][ p] _[c]_ [ð] _[m]_ [ j] _[ z]_ [Þ �j][O] _[Z]_ [j]




- 1



¼
p _c_ ð _m_ ; _Z_ Þ



X


_z_ ^2O _Z_



_i_ ¼1



Yj _M_ j

_pc_ ð _mi_ j ^ _z_ Þ

_i_ ¼1



_;_ _z_ 2 O _Z;_ ð33Þ




                                - 1 [X]

where _pc_ ð _mi_ j _z_ Þ ¼ jO _Y_ j



_pc_ ð _mi_ j _z; y_ Þ in line with (28).



_y_ 2O _Y_

To correctly quantify intrinsic causal constraints, the marginal probability of possible cause
states (for computing p _c_ [ð] _[z]_ [ j] _[ m]_ [Þ][ or] _[ π][c]_ [(] _[m]_ [;] _[ Z]_ [)) is again set to the uniform distribution. As above,]
all probabilities are obtained from the TPMs T _e_ (3) and T _c_ (4) and thus correspond to _inter-_
_ventional_ probabilities throughout.
Having defined cause and effect probabilities, we can now evaluate the intrinsic information of a mechanism _m_ over a purview state _z_ 2 O _Z_ analogously to the system intrinsic information (5) and (7). The intrinsic effect information that a mechanism in a state _m_ specifies
about a purview state _z_ is

              -               
ii _e_ ð _m; z_ Þ ¼ p _e_ ð _z_ j _m_ Þ log pp _ee_ ðð _zz_ j; _M m_ ÞÞ _:_ ð34Þ


The intrinsic cause information that a mechanism in a state _m_ specifies about a purview state _z_
is

              -               
ii _c_ ð _m; z_ Þ ¼ p _c_ [ð] _[z]_ [ j] _[ m]_ [Þ][ log] p _c_ ð _m_ j _z_ Þ _:_ ð35Þ
p _c_ ð _m_ ; _Z_ Þ


As with system intrinsic information, the logarithmic term is the informativeness, which
captures how much causal power is exerted by the mechanism _m_ on its potential effect _z_ (how
much it increases the probability of that state above chance), or by the potential cause _z_ on the
mechanism _m_ . The term in front of the logarithm corresponds to the mechanism’s selectivity,
which captures how much the causal power of the mechanism _m_ is concentrated on a specific
state of its purview (as opposed to other states). In the following we will again focus on the
effect side, but an equivalent procedure applies on the cause side (see S1 Fig).
Based on the principle of maximal existence, the maximal effect state of _m_ within the purview _Z_ is defined as



_ze_ [0] [ð] _[m][;][ Z]_ [Þ ¼][ argmax]

_z_ 2O _Z_



ii _e_ ð _m; z_ Þ _;_ ð36Þ



which corresponds to the specific effect of _m_ on _Z_ . Note that _ze_ [0] [is not always unique (see][ S1]
Text). The maximal intrinsic information of mechanism _m_ over a purview _Z_ is then

ii _e_ ð _m; Z_ Þ ≔ ii _e_ ð _m; ze_ [0] [Þ ¼][ max] _z_ 2O _Z_ [ii] _[e]_ [ð] _[m][;][ z]_ [Þ] _[:]_ ð37Þ


Note that, by this definition, if ii _e_ ( _m_, _Z_ ) 6¼ 0, mechanism _m_ always raises the probability of
its maximal effect state compared to the unconstrained probability. This is because there is at
least one state _z_ 2 O _Z_ such that _πe_ ( _z_ j _m_ ) _> πe_ ( _z_ ; _M_ ).
The intrinsic information of a candidate distinction, like that of the system as a whole, is
sensitive to indeterminism (the same state leading to multiple states) and degeneracy (multiple
states leading to the same state) because both factors decrease the probability of the selected


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 22 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


state. Moreover, the product of selectivity and informativeness leads to a tension between
expansion and dilution: larger purviews tend to increase informativeness because conditional
probabilities will deviate more from chance, but they also tend to decrease selectivity because
of the larger repertoire of states.
**Integration: Determining the irreducibility of a candidate distinction.** To comply with
integration, we must next ask whether the specific effect of _m_ on _Z_ is irreducible. As for the
system, we do so by evaluating the integrated information _φe_ ( _m_, _Z_ ). To that end, we define a
set of “disintegrating” partitions Θ( _M_, _Z_ ) as

               Yð _M; Z_ Þ ¼ fð _M_ [ð] _[i]_ [Þ] _; Z_ [ð] _[i]_ [Þ] Þg _ki_ ¼1 [:] _[k]_ [ 2 f][2] _[;]_ [ 3] _[;]_ [ 4] _[;]_ [ . . .][g] _[;]_ _[M]_ [ð] _[i]_ [Þ] [2][ P][ð] _[M]_ [Þ] _[;]_ _[Z]_ [ð] _[i]_ [Þ] [2][ P][ð] _[Z]_ [Þ] _[;]_

                                  - ð38Þ
S
_M_ ð _i_ Þ ¼ _M;_ S _Z_ ð _i_ Þ ¼ _Z; Z_ ð _i_ Þ \ _Z_ ð _j_ Þ ¼ _M_ ð _i_ Þ \ _M_ ð _j_ Þ ¼ ; 8 _i_ 6¼ _j; M_ ð _i_ Þ ¼ _M_ ) _Z_ ð _i_ Þ ¼ ; _;_


where { _M_ [(] _[i]_ [)] } is a partition of _M_ and { _Z_ [(] _[i]_ [)] } is a partition of _Z_, but the empty set may also be used
as a part (P denotes the power set). As introduced in [10, 12], a disintegrating partition _θ_ 2 Θ
( _M_, _Z_ ) either “cuts” the mechanism into at least two independent parts if | _M_ | _>_ 1, or it severs
all connections between _M_ and _Z_, which is always the case if | _M_ | = 1 (we refer to [10, 12] for
details). Note that disintegrating partitions differ from system partitions (23), which divide the
system into two or more parts in a directed manner to evaluate whether and to what extent the
system is integrated in terms of its cause–effect power. Instead, disintegrating partitions apply
to mechanism–purview pairs within the system, which are already directed, to evaluate the
cause or effect power specified by the mechanism over its purview.
Given a partition _θ_ 2 Θ( _M_, _Z_ ), we can define the partitioned effect probability


Y _k_
p [y] _e_ [ð] _[z]_ _e_ [0] [j] _[ m]_ [Þ ¼] p _e_ ð _ze_ [0ð] _[i]_ [Þ] j _m_ [ð] _[i]_ [Þ] Þ _;_ ð39Þ

_i_ ¼1


with pð�j _m_ [ð] _[i]_ [Þ] Þ ¼ pð�Þ ¼ 1. In the case of _m_ [ð] _[i]_ [Þ] ¼ �, p _e_ ð _ze_ [0ð] _[i]_ [Þ][j][�][Þ][ corresponds to the fully parti-]
tioned effect probability



Yj _Z_ j X
p _e_ ð _z_ j �Þ ¼ _pe_ ð _zi_ j _s_ ÞjO _S_ j

_i_ ¼1 _s_ 2O _S_




- 1 _:_ ð40Þ



The integrated effect information of mechanism _m_ over a purview _Z_  - _S_ with effect state _ze_ [0]
for a particular partition _θ_ 2 Θ( _M_, _Z_ ) is then defined as




        
p _e_ ð _ze_ [0] [j] _[ m]_ [Þ]
_φe_ ð _m; Z;_ yÞ ¼ p _e_ ð _ze_ [0] [j] _[ m]_ [Þ] ���� log �����
p [y] _e_ [ð] _[z]_ _e_ [0] [j] _[ m]_ [Þ] þ



_:_ ð41Þ



The effect of _m_ on _ze_ [0] [is reducible if at least one partition] _[ θ]_ [ 2][ Θ][(] _[M]_ [,] _[ Z]_ [) makes no difference to]
the effect probability or increases it compared to the unpartitioned probability. In line with the
principle of minimal existence, the total integrated effect information _φe_ ( _m_, _Z_ ) again has to be
evaluated over _θ_ [0], the minimum partition (MIP)


_φe_ ð _m; Z_ Þ ≔ _φe_ ð _m; Z;_ y [0] Þ _;_ ð42Þ


which requires a search over all possible partitions _θ_ 2 Θ( _M_, _Z_ ):



_φ_ ð _m; Z;_ yÞ

y [0] ¼ argminy2Yð _M;Z_ Þ max _[:]_ ð43Þ

T [0] _[φ]_ [ð] _[m][;][ Z][;]_ [ y][Þ]



[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 23 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


As in (23), the minimum partition is evaluated against its maximum possible value across all
possible systems TPMs T 0, which again corresponds to the number of possible pairwise inter
actions affected by the partition.
The integrated cause information is defined analogously, as





p _c_ ð _m_ j _zc_ [0][Þ]

�����

p [y] _c_ [0] [ð] _[m]_ [ j] _[ z]_ _c_ [0][Þ] þ




            
p _c_ ð _m_ j _zc_ [0][Þ]
_φc_ ð _m; Z_ Þ ≔ _φc_ ð _m; Z;_ y [0] Þ ¼ p _c_ [ð] _[z]_ _c_ [0] [j] _[ m]_ [Þ] ���� log
p [y][0] [ð] _[m]_ [ j] _[ z]_ [0][Þ]




[y] _c_ [ð] _[m]_ [ j] _[ z]_ _c_ [0][Þ]



_;_ ð44Þ



where the partitioned probability p [y] _c_ [ð] _[m]_ [ j] _[ z]_ [Þ][ is again a product distribution over the parts in the]
partition, as in (39).
Taken together, the intrinsic information (37) determines what cause or effect state the
mechanism _m_ specifies. Its integrated information quantifies to what extent _m_ specifies its
cause or effect in an irreducible manner. Again, _φ_ ( _m_, _Z_ ) is a quantifier of irreducible existence.
**Exclusion: Determining causal distinctions.** Finally, to comply with exclusion, a mechanism must select a definite effect purview, as well as a cause purview, out of a set of candidate
purviews. Resorting again to the principle of maximal existence, the mechanism’s effect purview and associated effect is the one having the maximum value of integrated information
across all possible purviews _Z_ - _S_ in state _ze_ [0] [ð] _[m][;][ Z]_ [Þ][ (36)]



_ze_ [∗][ð] _[m]_ [Þ ¼][ argmax]

_Z_       - _S_



_φe_ ð _m; ze_ [0] [ð] _[m][;][ Z]_ [ÞÞ] _[:]_ ð45Þ



The integrated effect information of a mechanism _m_ within _S_ is then

_φe_ ð _m_ Þ ≔ _φe_ ð _m; ze_ [∗][ð] _[m]_ [ÞÞ ¼][ max] _Z_                                - _S_ _[φ][e]_ [ð] _[m][;][ z]_ _e_ [0] [ð] _[m][;][ Z]_ [ÞÞ] _[:]_ ð46Þ


The integrated cause information _φc_ ( _m_ ) and the maximally irreducible cause _zc_ [∗][ð] _[m]_ [Þ][ are]
defined in the same way (see S1 Fig). Based again on the principle of minimal existence, the
irreducibility of the distinction specified by a mechanism is given by the minimum between its
integrated cause and effect information


_φd_ ð _m_ Þ ¼ min ð _φc_ ð _m_ Þ _; φe_ ð _m_ ÞÞ _:_ ð47Þ


**Determining the set of causal distinctions that are congruent with the system cause–**
**effect state.** As required by composition, unfolding the full cause–effect structure of the system _S_ in state _s_ requires assessing the irreducible cause–effect power of every subset of units
within _S_ (Fig 2). Any _m_                    - _s_ with _φd >_ 0 specifies a candidate distinction _d_ ( _m_ ) = ( _m_, _z_ *, _φd_ )
(27) within the system _S_ in state _s_ . However, in order to contribute to the cause–effect structure
of a system, distinctions must also comply with intrinsicality and information at the system
level. Thus, the fact that the system must select a specific cause–effect state implies that the
cause–effect state they specify over subsets of the system ( _z_ [∗] ¼ f _zc_ [∗] _[;][ z]_ _e_ [∗][g][) must be congruent]
with the cause–effect state specified over itself by the system as a whole _s_ [0] .
We thus define the set of all causal distinctions within _S_ in state _s_ as


_D_ ðT _e;_ T _c; s_ Þ ¼ f _d_ ð _m_ Þ : _m_               - _s;_ _φd_ ð _m_ Þ _>_ 0 _;_ _zc_ [∗][ð] _[m]_ [Þ �] _[s]_ [0] _c_ _[;]_ _[z]_ _e_ [∗][ð] _[m]_ [Þ �] _[s]_ [0] _e_ [g] _[:]_ ð48Þ


Altogether, distinctions can be thought of as irreducible “handles” through which the system can take and make a difference to itself by linking an intrinsic cause to an intrinsic effect
over subsets of itself. As components within the system, causal distinctions have no inherent
structure themselves. Whatever structure there may be between the units that make up a distinction is not a property of the distinction but due to the structure of the system, and thus captured already by its compositional set of distinctions. Similarly, from an extrinsic perspective,


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 24 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**Fig 2.** **Composition and causal distinctions.** Identifying the irreducible causal distinctions specified by a substrate in a state requires evaluating the specific
causes and effects of every system subset. The candidate substrate is constituted of two interacting units _S_ = _aB_ (see Fig 1) with TPMs T _e_ and T _c_ as shown.
In addition to the two first-order mechanisms _a_ and _B_, the second-order mechanism _aB_ specifies its own irreducible cause and effect, as indicated by
_φd >_ 0.


[https://doi.org/10.1371/journal.pcbi.1011465.g002](https://doi.org/10.1371/journal.pcbi.1011465.g002)


one may uncover additional causes and effects, both within the system and across its borders,
at either macro or micro grains. However, from the intrinsic perspective of the system causes
and effects that are excluded from its cause–effect structure do not exist [17, 29].
For example, as shown in Fig 3(A), a system may have a mechanism through which it specifies, in a maximally irreducible manner, the effect state of a triplet of units ( _e.g_ ., _ze_ [∗] [¼] _[ abc]_ [, a]
third-order purview; again lowercase letters for units indicate state “−1,” uppercase letters state
“+1”). However, if the system lacks a mechanism through which it can specify the effect state
of single units, each taken individually (say, unit _a_, a first-order effect purview), then, from its
intrinsic perspective, that unit does not exist as a single unit. By the same token, if the system
can specify individually the state of unit _a_, _b_, and _c_, but lacks a way to specify irreducibly the
state of _abc_ together, then, from its intrinsic perspective, the triplet _abc_ does not exist as a triplet (see Fig 3(B)). Finally, even if the system can distinguish the single units _a_, _b_, and _c_, as well
as the triplet _abc_, if it lacks handles to distinguish pairs of units such as _ab_ and _bc_, it cannot
order units in a sequence.


**Composition and causal relations**


Causal relations capture how the causes and/or effects of a set of distinctions within a complex
overlap with each other. Just as a distinction specifies which units/states constitute a cause purview and the linked effect purview, a relation specifies which units/states correspond to which
units/states among the purviews of a set of distinctions. Relations thus reflect how the cause–
effect power of its distinctions is “bound together” within a complex. The irreducibility due to
this binding of cause–effect power is measured by the relations’ irreducibility ( _φr >_ 0). Relations between distinctions were first described in [11] (for differences with the initial presentation see S2 Text).
A set of distinctions _**d**_                        - _D_ ( _s_ ) is related if the cause–effect state of each distinction _d_ 2 _**d**_
overlaps congruently over a set of shared units, which may be part of the cause, the effect, or


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 25 / 45



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Integrated information theory (IIT) 4.0 Formulating the properties of phenomenal existence in physical terms_extracted/images/Integrated-information-theory-(IIT)-4.0-Formulating-the-properties-of-phenomenal-existence-in-physical-terms.pdf-24-0.png)
PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**Fig 3.** **Composition of intrinsic effects.** From the intrinsic perspective of the system, a specific cause or effect is only available to the system if it is selected
by a causal distinction _d_ 2 _D_ ( _s_ ). In (A), only the top-order effect is specified. From the intrinsic perspective, the system cannot distinguish the individual
units. In (B), only first-order effects are specified. The system has no “handle” to select all three units together. (C) If both first- and third-order effects are
specified, but no second-order effects, the system can distinguish individual units and select them together, but has no way of ordering them sequentially.
(D) The system can distinguish individual units, select them altogether, as well as order them sequentially, in the sense that it has a handle for _ab_ and _bc_, but
not _ac_ . The ordering becomes apparent once the relations among the distinctions are considered (see below, Fig 5).


[https://doi.org/10.1371/journal.pcbi.1011465.g003](https://doi.org/10.1371/journal.pcbi.1011465.g003)


both the cause and the effect of each distinction. Below we will denote the cause of a distinction
_d_ as _zc_ [∗][ð] _[d]_ [Þ][ and its effect as] _[ z]_ _e_ [∗][ð] _[d]_ [Þ][. For a given set of distinctions] _**[ d]**_ [ �] _[D]_ [(] _[s]_ [), there are potentially]
many “relating” sets of causes and/or effects _**z**_ such that

\
_**z**_ : _**z**_ \ f _zc_ [∗][ð] _[d]_ [Þ] _[;][ z]_ _e_ [∗][ð] _[d]_ [Þg 6¼][ �] [8] _[d]_ [ 2] _**[ d]**_ _[;]_ _z_ 6¼ � _;_ j _**z**_ j _>_ 1 ð49Þ

_z_ 2 _**z**_


with maximal overlap



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Integrated information theory (IIT) 4.0 Formulating the properties of phenomenal existence in physical terms_extracted/images/Integrated-information-theory-(IIT)-4.0-Formulating-the-properties-of-phenomenal-existence-in-physical-terms.pdf-25-0.png)

\

_o_ [∗] ð _**z**_ Þ ¼


_z_ 2 _**z**_



_z_ 6¼ � _:_ ð50Þ



Since _zc_ [∗][ð] _[m]_ [Þ �] _[s]_ [0] _c_ [and] _[ z]_ _e_ [∗][ð] _[m]_ [Þ �] _[s]_ [0] _e_ [are sets of tuples containing both the units and their states,]
the intersection operation considers both the units and the state of the units.
All possible sets _**z**_ specify unique aspects about a relation _r_ ( _**d**_ ) and constitute the various
“faces” of the relation (Fig 4). The maximal overlap _o_ *( _**z**_ ) (50) is also called the “face purview.”
The set of faces associated with a relation thus specifies which type of relation it is (e.g., a single-faceted relation that only relates the causes of the set of distinctions, or a multi-faceted relation, which requires some of the distinctions to overlap on both the cause and effect side).
Note that (49) includes the case _**z**_ ¼ f _zc_ [∗][ð] _[d]_ [Þ] _[;][ z]_ _e_ [∗][ð] _[d]_ [Þg][, which indicates a “self-relation” over the]
cause and effect of a single distinction _d_ 2 _D_ ( _s_ ).
A relation _r_ ( _**d**_ ) thus consists of a set of distinctions _**d**_ 2 _D_ ( _s_ ), with an associated set of faces
_**f**_ ( _**d**_ ) = { _f_ ( _**z**_ )} _**d**_ and irreducibility _φr >_ 0,


_r_ ð _**d**_ Þ ¼ ð _**d**_ _;_ _**f**_ ð _**d**_ Þ _; φr_ Þ _:_ ð51Þ


A relation that binds together _h_ = | _**d**_ | distinctions is a _h_ -degree relation. A relation face _f_ ( _**z**_ ) 2 _**f**_ ( _**d**_ )


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 26 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**Fig 4.** **Composition and causal relations.** Relations between distinctions specify joint causes and/or effects. The two distinctions _d_ ( _a_ ) and _d_ ( _aB_ ) each
specify their own cause and effect. In this example, their cause and effect purviews overlap over the unit _b_ and are congruent, which means that they all
specify _b_ to be in state “-1.” The relation _r_ ({ _a_, _aB_ }) thus binds the two distinctions together over the same unit. Relation faces are indicated by the blue lines
and surfaces between the distinctions’ causes and/or effects (different shades are used to individuate the faces). Because all four purviews overlap over the
same unit, all nine possible faces exist. Note that the fact that the two distinctions overlap irreducibly can only be captured by a relation and not by a highorder distinction.


[https://doi.org/10.1371/journal.pcbi.1011465.g004](https://doi.org/10.1371/journal.pcbi.1011465.g004)


consists of a set of causes and effects _**z**_ (as in 49), with associated face purview _o_ [∗] ð _**z**_ Þ (50)


_f_ ð _**z**_ Þ ¼ ð _**z**_ _; o_ [∗] ð _**z**_ ÞÞ _:_ ð52Þ


A relation face over _k_ = | _**z**_ | purviews is a _k_ -degree face. The set of faces includes all the ways in
which the set of distinctions _**d**_ counts as related according to (49). Because _**z**_ may include either
the cause, or the effect, or both the cause and effect of a distinction _d_ 2 _**d**_, a relation _r_ ( _**d**_ ) with
| _**d**_ | _>_ 1 may comprise up to 3 [|] _**[d]**_ [|] faces. If a set of distinctions _**d**_ 2 _D_ ( _s_ ) does not overlap congruently, it is not related (in that case _o_ [∗] ð _**z**_ Þ ¼ � for all possible _f_ ( _**z**_ ) 2 _**f**_ ( _**d**_ )) (Fig 5).
Causal relations inherit existence from the cause–effect power of the distinctions that compose them. They inherit intrinsicality because the causes and effects that compose their faces
are specified within the substrate. Moreover, relations are specific because the joint purviews
of their faces must be congruent for all causes and effects _z_                      - 2 _**z**_ . Note that relation purviews
are necessarily congruent with the overall cause and effect state specified by the system as a
whole, because the causes and effects of the distinctions composing a relation must themselves
be congruent.
The irreducibility of a causal relation is measured by “unbinding” distinctions from their
joint purviews, taking into account all faces of the relation. Distinctions _d_ 2 _D_ ( _s_ ) are already
established as maximally irreducible components, characterized by their value of integrated
information _φd_ . To assess the irreducibility of a relation, we thus assume that the integrated
information _φd_ of a distinction is distributed uniformly across unique cause and effect purview
units, such that

_φd_ ð53Þ
j _zc_ [∗][ð] _[d]_ [Þ [] _[ z]_ _e_ [∗][ð] _[d]_ [Þj]


is the average irreducible information _φd_ per unique purview unit for an individual distinction
_d_ 2 _**d**_ with cause–effect state _z_ [∗] ð _d_ Þ ¼ f _zc_ [∗][ð] _[d]_ [Þ] _[;][ z]_ _e_ [∗][ð] _[d]_ [Þg][. Since the union operator takes the states]
of the units into account, incongruent units are counted separately, while congruent units on
the cause and effect side count as one.
Since distinctions are related by specifying common units into common states, the effect of
“unbinding” a distinction must be proportional to the number of units jointly specified in the


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 27 / 45



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Integrated information theory (IIT) 4.0 Formulating the properties of phenomenal existence in physical terms_extracted/images/Integrated-information-theory-(IIT)-4.0-Formulating-the-properties-of-phenomenal-existence-in-physical-terms.pdf-26-0.png)
PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**Fig 5.** **Structuring of intrinsic effects by relations.** (A) A single undifferentiated effect has no relations. (B) Likewise, there are no relations among
multiple non-overlapping effects. (C) The set of three first-order effects and one third-order effect supports three relations, which bind the effects together.
(D) The set of first, second, and third-order effects supports a large number of relations (ten 2-relations (between two effects), six 3-relations, and one
4-relation), which bind the effects in a structure that is ordered sequentially.


[https://doi.org/10.1371/journal.pcbi.1011465.g005](https://doi.org/10.1371/journal.pcbi.1011465.g005)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Integrated information theory (IIT) 4.0 Formulating the properties of phenomenal existence in physical terms_extracted/images/Integrated-information-theory-(IIT)-4.0-Formulating-the-properties-of-phenomenal-existence-in-physical-terms.pdf-27-0.png)

relation, _i.e_ . the number of distinct units over the joint purviews of all faces in the relation:


[

_o_ [∗] _f_ _:_

����� �����




[




_o_ [∗] _f_



_:_ ð54Þ
�����



_f_ 2 _**f**_ ð _**d**_ Þ



This union of the face purviews _o_ [∗] _f_ [is also called the “relation purview” or the “joint purview”]
of the relation. While any partition of one or more distinctions from the relation will “unbind”
the set of distinctions _**d**_, by the principle of minimal existence, a relation can only be as irreducible as the minimal amount of integrated information specified by any one distinction in
the relation. Therefore, the relation integrated information _φr_ ( _**d**_ ) is defined as




[


_f_ 2 _**f**_ ð _**d**_ Þ



_φd_ ð55Þ
����� j _zc_ [∗][ð] _[d]_ [Þ [] _[ z]_ _e_ [∗][ð] _[d]_ [Þj] _[:]_



_φr_ ð _**d**_ Þ ¼ min _d_ 2 _**d**_



�����




_o_ [∗] _f_



In words, for each distinction, we take the average integrated information per distinct purview
element (53), multiply it by the number of units across all faces of the relation (54), and then
find the distinction that contributes the least integrated information per overlap unit as the
minimum partition of the relation (with corresponding integrated information _φr_ ). Defining
_φr_ in this way guarantees that the integrated information of a relation cannot exceed the integrated information of its weakest distinction. For a given set of distinctions, the maximum
value of _φr_ occurs for a relation in which the cause and effect of each distinction is fully overlapped by all other distinctions in the relation (in that case, _φr_ = min _d_ 2 _**d**_ _φd_ ). Note also that a
relation satisfies exclusion (distinctions overlap on _this whole_ set of units) in that its integrated
information is naturally maximized (per the principle of maximal existence) over the maximal


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 28 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


congruent overlap _o_ [∗] _f_ [for each relation face][ (50)][ (taking subsets of these overlaps could only]
reduce the integrated information of the relation).
In summary, just as distinctions link a cause with an effect, relations bind various combinations of causes and effects that are congruent over the same units (Fig 4). And just as a distinction captures the irreducibility of an individual cause–effect linked by a mechanism, a relation
captures the irreducibility of a set of distinctions bound by the joint purviews of their causes
and/or effects.
For a set of distinctions _D_, we define the set of all relations among them as


_R_ ð _D_ Þ ¼ f _r_ ðdÞ : _φr_ ðdÞ _>_ 0g _;_ 8d � _D:_ ð56Þ


In practice, the total number of relations and their S _**R**_ ( _**D**_ ) _φr_ can be determined analytically for
a given set of distinctions _D_, which greatly reduces the necessary computations (see S3 Text).
Together, a set of distinctions _D_ and its associated set of relations _R_ ( _D_ ) compose a cause–effect
structure.


**Cause–effect structures and** _**Φ**_ **-structures**


A cause–effect structure is defined as the union of the distinctions specified by a substrate and
the relations binding them together:


_C_ ð _D_ Þ ¼ _D_ [ _R_ ð _D_ Þ _:_ ð57Þ


The cause–effect structure specified by a maximal substrate—a complex—is also called a _Φ_                     structure:

            -             _C_ ðT _e;_ T _c; s_ [∗] Þ ¼ f _d_ ð _m_ Þ ¼ f _m; z_ [∗] _; φd_ g 2 T _e;_ T _c; s_ [∗] Þg [S] f _r_ ð _**d**_ Þ ¼ f _**d**_ _;_ _**f**_ ð _**d**_ Þ _; φr_ g 2 _R_ ð _D_ ðT _e;_ T _c; s_ [∗] ÞÞg _:_ ð58Þ


The sum of the values of integrated information of a substrate’s distinctions and relations,
called _Φ_ (“big Phi,” “structure Phi”) corresponds to the _structure integrated information_ of the
_Φ_ -structure,



X
_Φ_ ðT _e;_ T _c; s_ [∗] Þ ¼

_C_ ðT _e;_ T _c;s_ [∗] Þ



_φ:_
ð59Þ



Note that _Φ_ is not computed based on a partition (as system phi), but rather a sum of the
integrated information within the structure (where each term of the sum was computed by
partitioning). Within a _Φ_ -structure, various types of meaningful sub-structures can be specified, which we term _Φ-folds_ . A _Φ_ -fold is composed of a subset of the distinctions and relations
that compose the overall cause–effect structure. A special case is the _distinction Φ-fold_, denoted
_C_ ({ _d_ }), a sub-structure composed of a single distinction and the relations bound to it, which
form its _context_ [11] (see (13) in S1 Notes). A _compound Φ-fold_ is a sub-structure composed of
the distinction _Φ_ -folds specified by a subset of units. A _compound Φ-fold_ is a relevant part of a
_Φ_ -structure because it can be accessed or manipulated by changing the state, connections, or
functioning of a part of the substrate. Finally, a _content Φ-fold_, or simply _content_, is composed
of a subset of distinctions that are highly interrelated (regardless of the mechanisms and units
that specify them).
In conclusion, a maximal substrate or complex is a set of units _S_                       - = _s_                       - that satisfies all of
IIT’s postulates: its cause–effect power is intrinsic, specific, irreducible, definite, and structured. By IIT, a complex _S_                     - does not exist as such, but exists “unfolded” into its _Φ_ -structure,
with all the causal distinctions and relations that compose it. In other words, a substrate is
what can be observed and manipulated “operationally” from the extrinsic perspective. From


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 29 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


the intrinsic perspective, what truly exists is a complex with all its causal powers unfolded—an
_intrinsic entity_ that exists for itself, absolutely, rather than relative to an external observer.
According to the explanatory identity of IIT, an experience is identical to the _Φ_ -structure of
an intrinsic entity: every property of the experience should be accounted for by a corresponding property of the _Φ_ -structure, with no additional ingredients. If a system _S_ in state _s_ is a complex, then its _Φ_ -structure corresponds to the quality of the experience of _S_ in state _s_, while its _Φ_
value corresponds to its quantity—in other words, to the nature and amount of intrinsic
content.


**Results and discussion**


In this section, we apply the mathematical framework of IIT 4.0 to several example systems.
The goal is to illustrate three critical implications of IIT’s postulates:


1. **Consciousness and connectivity** : how the way units interact determines whether a substrate can support a _Φ_ -structure of high _Φ_ .


2. **Consciousness and activity** : how changes in the state of a substrate’s units change _Φ_                        structures.


3. **Consciousness and functional equivalence** : how substrates that are functionally equivalent
may not be equivalent in terms of their _Φ_ -structures, and thus in terms of consciousness.


The following examples will feature very simple networks constituted of binary units _Ui_ 2
_U_ with O _Ui_ ¼ f� 1 _;_ 1g for all _Ui_ and a logistic (sigmoidal) activation function


1
_p_ ð _Ui;t_ ¼ 1 j _ut_                          - 1Þ ¼ 1 þ exp ð� _k_ ~~[P]~~ _[n]_ _j_ ¼1 _[w]_ _j;i_ _[u]_ _j;t_                          - 1 [Þ] _[;]_ ð60Þ


where _k >_ 0 and


X _n_

_wj;i_ ¼ 1 8 _i:_ ð61Þ

_j_ ¼1


In Eq (60), the parameter _k_ defines the slope of the logistic function and allows one to adjust
the amount of noise or determinism in the activation function (higher values signify a
steeper slope and thus more determinism). The units _Ui_ can thus be viewed as noisy linear
threshold units with weighted connections among them, where _k_ determines the connection
strength.
As in Figs 1 and 2, units denoted by uppercase letters are in state ‘1’ (ON, depicted in
black), units denoted by lowercase letters are in state ‘−1’ (OFF, depicted in white). Cause–
effect structures are illustrated as geometrical shapes projected into 3D space (Fig 6). Distinctions are depicted as mechanisms (black labels) tying a cause (red labels) and an effect
(green labels) through a link (orange edges, thickness indicating _φd_ ). Relation faces of second- and third-degree relations are depicted as edges or triangular surfaces between the
causes and effects of the related distinctions. While edges always bind pairs of distinctions
(a second-degree relation), triangular surfaces may bind the causes and effects of two or
three distinctions (second- or third-degree relation). Relations of higher degrees are not
depicted.
All examples were computed using the “iit-4.0” feature branch of PyPhi [37]. This branch
[will be available in the next official release of the software. An example notebook available here](https://colab.research.google.com/github/wmayner/pyphi/blob/feature/iit-4.0/docs/examples/IIT_4.0_demo.ipynb)
recreates the analysis of Fig 1 (identifying complexes), Fig 2 (computing distinctions), and Fig
4 (computing relations).


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 30 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**Fig 6.** **Causal powers analysis of various network architectures.** Each panel shows the network’s causal model and
weights on the left. Blue regions indicate complexes with their respective _φs_ values. In all networks, _k_ = 4 and the state
is _Abcdef_ . The _Φ_ -structure(s) specified by the network’s complexes are illustrated to the right (with only second- and
third-degree relation faces depicted) with a list of their distinctions for smaller systems and their ∑ _φ_ values for those
systems with many distinctions and relations. All integrated information values are in ibits. (A) A degenerate network


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 31 / 45



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Integrated information theory (IIT) 4.0 Formulating the properties of phenomenal existence in physical terms_extracted/images/Integrated-information-theory-(IIT)-4.0-Formulating-the-properties-of-phenomenal-existence-in-physical-terms.pdf-30-0.png)
PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


in which unit _A_ forms a bottleneck with redundant inputs from and outputs to the remaining units. The first-maximal
complex is _Ab_, which excludes all other subsets with _φs >_ 0 except for the individual units _c_, _d_, _e_, and _f_ . (B) The
modular network condenses into three complexes along its fault lines (which exclude all subsets and supersets), each
with a maximal _φs_ value, but low _Φ_, as the modules each specify only two or three distinctions and at most five
relations. (C) A directed cycle of six units forms a six-unit complex with _φs_ = 1.74 ibits, as no other subset is integrated.
However, the _Φ_ -structure of the directed cycle is composed of only first-order distinctions and few relations. (D) A
specialized lattice also forms a complex (which excludes all subsets), but specifies 27 first- and high-order distinctions,
with many relations ( _>_ 1.5 × 10 [6] ) among them. Its _Φ_ value is 11452 ibits. (E) A slightly modified version of the
specialized lattice in which the first-maximal complex is _Abef_ . The full system is not maximally irreducible and is
excluded as a complex, despite its positive _φs_ value (indicated in gray).


[https://doi.org/10.1371/journal.pcbi.1011465.g006](https://doi.org/10.1371/journal.pcbi.1011465.g006)


**Consciousness and connectivity**


The first set of examples highlights how the organization of connections among units impacts
the ability of a substrate to support a cause–effect structure with high structure integrated
information (high _Φ_ ). Fig 6 shows five systems, all in the same state _s_ = _Abcdef_ with the same
number of units, but with different connectivity among the units.
**Degenerate systems, indeterminism, and specificity.** Fig 6A shows a network with
medium indeterminism ( _k_ = 4) and high degeneracy, due to the fact that unit _A_ forms a “bottleneck” with inputs and outputs to and from the remaining units. The network condenses
into one complex of two units _Ab_ and four complexes corresponding to the individual units _c_,
_d_, _e_, and _f_ (also called “monads”).
The causes and effects of the causal distinctions for the two types of complexes are shown in
the middle, and the corresponding cause–effect structures are illustrated on the right. In this
case, degeneracy (coupled with indeterminism) undermines the ability of the maximal substrate to grow in size, which in turn limits the richness of the _Φ_ -structure that can be supported. Because of the bottleneck architecture, the current state of candidate system _Abcdef_ has
many possible causes and effects, leading to an exponential decrease in selectivity (the conditional probabilities of cause and effect states). This dilutes the value of intrinsic information
(ii) for larger subsets of units, which in turn reduces their value of system integrated information _φs_ . Consequently, the maximal substrates are small, and their _Φ_ values are necessarily low.
This example suggests that to grow and achieve high values of _Φ_, substrates must be constituted of units that are specialized (low degeneracy) and interact very effectively (low
indeterminism).
Notably, the organization of the cerebral cortex, widely considered as the likely substrate of
human consciousness, is characterized by extraordinary specialization of neural units at all levels [38–40]. Moreover, if the background conditions are well controlled, neurons are thought
to interact in a highly reliable, nearly deterministic manner [41–43].
**Modular systems, fault lines, and irreducibility.** Fig 6B shows a network comprising
three weakly interconnected modules, each having two strongly connected units ( _k_ = 4). In
this case, the weak inter-module connections are clear fault lines. Properly normalized, partitions along these fault lines separating modules yield values of _φs_ that are much smaller than
those yielded by partitions that cut across modules. As a consequence, the 6-unit system condenses into three complexes ( _Ab_, _cd_, and _ef_ ), as determined by their maximal _φs_ values. Again,
because the modules are small, their _Φ_ values are low. Intriguingly, a brain region such as the
cerebellum, whose anatomical organization is highly modular, does not contribute to consciousness [44, 45], even though it contains several times more neurons than the cerebral cortex (and is indirectly connected to it).
Note that fault lines can be due not just to neuroanatomy but also to neurophysiological factors. For example, during early slow-wave sleep, the dense interconnections among neuronal
groups in cerebral cortical areas may break down, becoming causally ineffective due to the


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 32 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


bistability of neuronal excitability. This bistability, brought about by neuromodulatory changes

[46], is associated with the loss of consciousness [47].
**Directed cycles, structural sparseness, and composition.** Fig 6C shows a directed cycle
in which six units are unidirectionally connected with weight _w_ = 1.0 and _k_ = 4. Each unit copies the state of the unit before it, and its state is copied by the unit after it, with some indeterminism. The copy cycle constitutes a 6-unit complex with a maximal _φs_ = 1.74 ibits. However,
despite the “large” substrate, the _Φ_ -structure it specifies has low structure integrated information ( _Φ_ = 7.65). This is because the system’s _Φ_ -structure is composed exclusively of first-order
distinctions, and consequently of a small number of relations.
Highly deterministic directed cycles can easily be extended to constitute large complexes,
being more irreducible than any of their subsets. However, the lack of cross-connections
(“chords” in graph-theoretic terms) greatly limits the number of components of the _Φ_ -structures specified by the complexes, and thus their structure integrated information ( _Φ_ ). (Note
also that increasing the number of units that constitute the directed cycle would not change
the amount of _φs_ specified by the network as a whole.).
The brain is rich in partially segregated, directed cycles, such as those originating in cortical
areas, sequentially reaching stations in the basal ganglia and thalamus, and cycling back to cortex [48, 49]. These cycles are critical for carrying out many cognitive and other functions, but
they do not appear to contribute directly to experience [4].
**Specialized lattices and** _**Φ**_ **-structures with high structure integrated information.** Fig
6D shows a network consisting of six heterogeneously connected units—a “specialized” lattice,
again with _k_ = 4. While many subsystems within the specialized network have positive values
of system integrated information _φs_, the full 6-unit system is the maximal substrate (excluding
all its subsets from being maximal substrates). Out of 63 possible distinctions, the _Φ_ -structure
comprises 27 distinctions with causes and effects congruent with the system’s maximal cause–
effect state. Consequently, the full 6-unit system also specifies a much larger number of causal
relations compared to the copy cycle system.
Preliminary work indicates that lattices of specialized units, implementing different input–
output functions, but partially overlapping in their inputs (receptive field) and outputs (projective fields), are particularly well suited to constituting large substrates that unfold into extraordinarily rich _Φ_ -structures. The number of distinctions specified by an optimally connected,
specialized system is bounded above by 2 _[n]_ −1, and that of the relations among as many distinctions is bounded by 2 [ð][2] _[n]_ [�] [1][Þ]                     - 1. The structure integrated information of such structures is correspondingly large [50].
In the brain, a large part of the cerebral cortex, especially its posterior regions, is organized
as a dense, divergent-convergent hierarchical 3D lattice of specialized units, which makes it a
plausible candidate for the substrate of human consciousness [4, 11, 51, 52]. Note that directed
cycles originating and ending in such lattices typically remain excluded from the first-maximal
complex because minimal partitions across such cycles yield a much lower value of _φs_ compared to minimal partitions across large lattices.
**Near-maximal substrates, extrinsic entities, and exclusion.** Finally, Fig 6E shows a network of six units, four of which ( _Abef_ ) constitute a specialized lattice that corresponds to the
first complex. Though integrated, the full set of 6 units happens to be slightly less irreducible
( _φs_ = 0.15) than one of its 4-unit subsets ( _φs_ = 0.27). From the extrinsic perspective, the 6-unit
system undoubtedly behaves as a highly integrated whole (nearly as much as its 4-unit subset),
one that could produce complex input–output functions due to its rich internal structure.
From the intrinsic perspective of the system, however, only the 4-unit subset satisfies all the
postulates of existence, including maximal irreducibility (accounting for the definite nature of


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 33 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


experience). In this example, the remaining units form a second complex with low _φs_ and
serve as background conditions for the first complex.
A similar situation may occur in the brain. The brain as a whole is undoubtedly integrated
(not to mention that it is integrated with the body as a whole), and neural “traffic” is heavy
throughout. However, its anatomical organization may be such that a subset of brain regions,
arranged in a dense 3D lattice primarily located in posterior cortex, may achieve a much
higher value of integrated information than any other subset. Those regions would then constitute the first complex (the “main complex,” [4]), and the remaining regions might condense
into a large number of much smaller complexes.
Taken together, the examples in Fig 6 demonstrate that the connectivity among the units of
a system has a strong impact on what set of units can constitute a complex and thereby on the
structure integrated information it can specify. The examples also demonstrate the role played
by the various requirements that must be satisfied by a substrate of consciousness: existence
(causal power), intrinsicality, specificity, maximal irreducibility (integration and exclusion),
and composition (structure).


**Consciousness and activity: Active, inactive, and inactivated units**


A substrate exerts cause–effect power in its current state. For the same substrate, changing the
state of even one unit may have major consequences on the distinctions and relations that
compose its _Φ_ -structure: many may be lost, or gained, and many may change their value of
irreducibility ( _φd_ and _φr_ ).

Fig 7 shows a network of five binary units that interact through excitatory and inhibitory
connections (weights indicated in the figure). The system is initially in state _s_ = _ABcdE_ (Fig
7A) and is a maximal substrate with _φs_ = 1.1 ibits and a _Φ_ -structure composed of 23 distinctions and their 13740 relations.
If we change the state of unit _E_ from ON to OFF (in neural terms, the unit becomes inactive), the distinctions that the unit contributes to when ON, as well as the associated relations,
may change (Fig 7B). In the case illustrated by the Figure, what changes are the purviews and
irreducibility of several distinctions and associated relations, the number of distinctions stays
the same, _φs_ changes only slightly, but the number of relations is lower, leading to a lower _Φ_
value. In other words, what a single unit contributes to intrinsic existence is not some small
“bit” of information. Instead, a unit contributes an entire sub-structure, composed of a very
large number of distinctions and relations. The set of distinctions to which a subset of units
contributes as a mechanism, either alone or in combination with other units, together with
their associated relations, forms a compound _Φ_ -fold. With respect to the neural substrate of
consciousness in the brain, this means that even a change in the state of a single unit is typically
associated with a change in an entire _Φ_ -fold within the overall _Φ_ -structure, with a corresponding change in the structure of the experience. (Note, however, that in larger systems such
changes will typically be less extreme, see also [11].).
In Fig 7C, we see what happens if unit _E_, instead of just turning inactive (OFF) is _inactivated_
(abolishing its cause–effect power because it no longer has any counterfactual states and thus
cannot be intervened upon). In this case, all the distinctions and relations to which that unit
contributes as a mechanism would cease to exist (its compound _Φ_ -fold collapses). Moreover,
all the distinctions and relations to whose purviews that unit contributes—its purview _Φ_ -fold
—would also collapse or change. In fact, the complex shrinks because it cannot include that
unit. With respect to the neural substrate of consciousness, this means that while an inactive
unit contributes to a different experience, an inactivated unit ceases to contribute to experience
altogether. The fundamental difference between inactive and inactivated units leads to the


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 34 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**Fig 7.** **Causal powers analysis of the same system with one of its units set to active, inactive, or inactivated.** In all panels,
the same causal model and weights are shown on the left, but in different states. For all networks _k_ = 4. The set of distinctions
_D s_ ), their causes and effects, and their _φd_ values are shown in the middle. The _Φ_ -structure specified by the network’s
complex is illustrated on the right (again with only second- and third-degree relation faces depicted). All integrated
information values are in ibits. (A) The system in state _ABcdE_ is a complex with 23 out of 31 distinctions and _Φ_ = 22.26. (B)


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 35 / 45



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Integrated information theory (IIT) 4.0 Formulating the properties of phenomenal existence in physical terms_extracted/images/Integrated-information-theory-(IIT)-4.0-Formulating-the-properties-of-phenomenal-existence-in-physical-terms.pdf-34-0.png)
PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


The same system in state _ABcde_, where unit _E_ is inactive (“OFF”) also forms a complex with the same number of distinctions,
but a somewhat lower _Φ_ value due to a lower number of relations between distinctions. In addition, the system’s _Φ_ -structure
differs from that in (A), as the system now specifies a different set of compositional causes and effects. (C) If instead of being
inactive, unit _E_ is inactivated (fixed into the “OFF” state), the inactivated unit cannot contribute to the complex or _Φ_                         structure anymore. The complex is now constituted of four units ( _ABcd_ ), with only 14 distinctions and markedly reduced
structure integrated information ( _Φ_ = 3.35).


[https://doi.org/10.1371/journal.pcbi.1011465.g007](https://doi.org/10.1371/journal.pcbi.1011465.g007)


following corollary of IIT: unlike a fully inactivated substrate which, as would be suspected,
cannot support any experience, an inactive substrate can. If a maximal substrate in an inactive
state is in working order and specifies a large _Φ_ -structure, it will support a highly structured
experience, such as the experience of empty space [11] or the feeling of “pure presence” (see
(14) in S1 Notes).


**Consciousness and functional equivalence: Being is not doing**


By the intrinsicality postulate, the _Φ_ -structure of a complex depends on the causal interactions
between system subsets, not on the system’s interaction with its environment (except for the
role of the environment in triggering specific system states). In general, different physical systems with different internal causal structure may perform the same input–output functions.

Fig 8 shows three simple deterministic systems with binary units (here the “OFF” state is 0,
and “ON” is 1) that perform the same input–output function, treating the internal dynamics of
the system as a black box. The function could be thought of, for example, as an electronic tollbooth “counting 8 valid coins” (8 times input _I_ = 1) before opening the gate [53]. Each system
receives one binary input ( _I_ ) and has one binary output ( _O_ ). The output unit switches “ON”
on a count of eight positive inputs _I_ = 1 (when the global state with label ‘0’ is reached in the
cycle), upon which the system resets (Fig 8A).
In addition to being functionally equivalent in their outward behavior, the three systems
share the same internal global dynamics, as their internal states update according to the same
global state-transition diagram (Fig 8B). Given an input _I_ = 1, the system updates its state,
cycling through all its 8 global states (labeled 0–7) over 8 updates. For an input of _I_ = 0, the system remains in its present state. Moreover, all three systems are constituted of three binary
units whose joint states map one-to-one onto the systems’ global state labels (0–7). However,
the mapping is different for different systems (Fig 8C, left). This is because the internal binary
update sequence depends on the interactions among the internal units [29, 53], which differ in
the three cases, as can easily be determined through manipulations and observations.
For consistency in the causal powers analysis, in all three cases, the global state “0” that activates the output unit if _I_ = 1 is selected such that it corresponds to the binary state “all OFF”
(000), which is followed by 1 ≔ 100 and 2 ≔ 010. Also, the _Φ_ -structure of each system is
unfolded in state 1 ≔ 100 in all three cases.
Despite their functional equivalence and equivalent global dynamics, the systems differ in
how they condense into complexes and in the cause–effect structures they specify.
As shown in Fig 8C, the first system forms a 3-unit complex with a relatively rich _Φ_ -structure ( _Φ_ = 21.01 ibits). While the second system also forms a 3-unit complex with the same _φs_ =
2 ibits, it specifies a completely different set of distinctions and has much lower structure integrated information ( _Φ_ = 3.64 ibits).
Finally, the third system is reducible ( _φs_ = 0 ibits)—in this case, because there are only feedforward connections from unit _A_ to units _B_ and _C_ —and it condenses into three complexes
with small _Φ_ -structures.
These examples illustrate a simple scenario of functional equivalence of three systems characterized by a different architecture. The equivalence is with respect to a simple input–output


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 36 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**Fig 8.** **Functionally equivalent networks with different** _**Φ**_ **-structures.** (A) The input–output function realized by three different systems (shown in (C)): a
count of eight instances of input _I_ = 1 leads to output _O_ = 1. (B) The global state-transition diagram is also the same for the three systems: if _I_ = 0, the
systems will remain in their current global state, labeled as 0–7; if _I_ = 1, the systems will move one state forward, cycling through their global states, and
activate the output if _S_ = 0. (C) Three systems constituted of three binary units but differing in how the units are connected and interact. As a consequence,
the one-to-one mapping between the 3-bit binary states and the global state labels differ. However, all three systems initially transition from 000 to 100 to
010. Analyzed in state 100, the first system (top) turns out to be a single complex that specifies a _Φ_ -structure with six distinctions and many relations,
yielding a high value of _Φ_ . The second system (middle) is also a complex, with the same _φs_ value, but it specifies a _Φ_ -structure with fewer distinctions and
relations, yielding a lower value of _Φ_ . Finally, the third system (bottom) is reducible ( _φs_ = 0) and splits into three smaller complexes (entities) with minimal
_Φ_ -structures and low _Φ_ .


[https://doi.org/10.1371/journal.pcbi.1011465.g008](https://doi.org/10.1371/journal.pcbi.1011465.g008)


function, in this case coin counting, which they multiply realize. The systems are also equivalent in terms of their global system dynamics, in the sense that they go through a globally
equivalent sequence of internal states. However, because of their different substrates, the three
systems specify different cause–effect structures. Therefore, based on the postulates of IIT,
they are not phenomenally equivalent. In other words, they are equivalent in what they _do_
extrinsically, but not in what they _are_ intrinsically.
This dissociation between phenomenal and functional equivalence has important implications. As we have seen, a purely feed-forward system necessarily has _φs_ = 0. Therefore, it cannot support a cause–effect structure and cannot be conscious, whereas systems with a
recurrent architecture can. On the other hand, the behavior (input–output function) of any
(discrete) recurrent system can also be implemented by a system with a feed-forward architecture [54]. This implies that any behavior performed by a conscious system supported by a
recurrent architecture can also be performed by an unconscious system, no matter how complex the behavior is. More generally, digital computers implementing programs capable of artificial general intelligence may in principle be able to emulate any function performed by
conscious humans and yet, because of the way they are physically organized, they would do so
without experiencing anything, or at least anything resembling, in quantity and quality, what
each of us experiences [20] (see also (15) in S1 Notes).


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 37 / 45



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Integrated information theory (IIT) 4.0 Formulating the properties of phenomenal existence in physical terms_extracted/images/Integrated-information-theory-(IIT)-4.0-Formulating-the-properties-of-phenomenal-existence-in-physical-terms.pdf-36-0.png)
PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


The examples also show that the overall system dynamics, while often revealing relevant
aspects of a system’s architecture, typically do not and cannot exhaust the richness of its current cause–effect structure. For example, a system in a fixed point is dynamically “dead” (and
“does” nothing), but it may be phenomenally quite “alive,” for example, experiencing “pure
presence” (see (14) in S1 Notes). Of course, the system’s causal powers can be fully unfolded,
and revealed dynamically, by extensive manipulations and observations of subsets of system
units because they are implicitly captured by the system’s causal model and ultimately by its
transition probability matrix [29].


**Conclusions**


IIT attempts to account for the presence and quality of consciousness in physical terms. It
starts from the existence of experience, and proceeds by characterizing its essential properties
—those that are immediate and irrefutably true of every conceivable experience (axioms).
These are then formulated as essential properties of physical existence (postulates), the necessary and sufficient conditions that a substrate must satisfy to support an experience—to constitute a complex. Note that “substrate” is meant in purely operational terms—as a set of units
that a conscious observer can observe and manipulate. Likewise, “physical” is understood in
purely operational terms as cause–effect power—the power to take and make a difference.
The postulates can be assessed based purely on a substrate’s transition probability matrix,
as was illustrated by a few idealized causal models. Thus, a substrate of consciousness must
be able to take and make a difference upon itself (existence and intrinsicality), it must be able
to specify a cause and an effect state that are highly informative and selective (information),
and it must do so in a way that is both irreducible (integration) and definite (exclusion).
Finally, it must specify its cause and effect in a structured manner (composition), where the
causal powers of its subsets over its subsets compose a cause–effect structure of distinctions
and relations—a _Φ_ -structure. Thus, a complex does not exist as such but only “unfolded” as
a _Φ_ -structure—an _intrinsic entity_ that exists for itself, absolutely, rather than relative to an
external observer.
As shown above, these requirements constrain what substrates can and cannot support consciousness. Substrates that lack in specificity, due to indeterminism and/or degeneracy, cannot
grow to be large complexes. Substrates that are weakly integrated, due to architectural or functional fault lines in their interactions, are less integrated than some of their subsets. Because
they are not maximally irreducible, they do not qualify as complexes. This is the case even
though they may “hang together” well enough from an extrinsic perspective (having a respectable value of _φs_ ). Furthermore, even substrates that are maximally integrated may support _Φ_                       structures that are extremely sparse, as in the case of directed cycles. Based on the postulates of
IIT, a universal substrate ultimately “condenses” into a set of disjoint (non-overlapping) complexes, each constituted of a set of macro or micro units.
The physical account of consciousness provided by IIT should be understood as an explanatory identity: every property of an experience should ultimately be accounted for by a property
of the cause–effect structure specified by a substrate that satisfies its postulates, with no additional ingredients. The identity is not between two different substances or realms—the phenomenal and the physical—but between intrinsic (subjective) existence and extrinsic
(objective) existence. Intrinsic existence is immediate and irrefutable, while extrinsic existence
is defined operationally as cause–effect power discovered through observation and manipulation. The primacy of intrinsic existence (of experience) in IIT contrasts with standard attempts
at accounting for consciousness as something “generated by” or “emerging from” a substrate
constituted of matter and energy and following physical laws.


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 38 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


The physical correspondent of an experience is not the substrate as such but the _Φ_ -structure
specified by the substrate in its current state. Therefore, minor changes in the substrate state
can correspond to major changes in the specified _Φ_ -structure. For example, if the state of a single unit changes, an entire _Φ_ -fold within the _Φ_ -structure will change, and if a single inactive
unit is inactivated, its associated _Φ_ -fold will collapse, even though the current state of the substrate appears the same (Fig 7).
Each experience corresponds to a _Φ_ -structure, not a set of functions, processes, or computations. Said otherwise, consciousness is about being, not doing [1, 29, 55]. This means that systems
with different architectures may be functionally equivalent—both in terms of global input–output
functions and global intrinsic dynamics—but they will not be phenomenally equivalent. For
example, a feed-forward system can be functionally equivalent to a recurrent system that constitutes a complex, but feed-forward systems cannot constitute complexes because they do not satisfy maximal irreducibility. Accordingly, artificial systems powered by super-intelligent computer
programs, but implemented by feed-forward hardware or encompassing critical bottlenecks,
would experience nothing (or nearly nothing) because they have the wrong kind of physical
architecture, even though they may be behaviorally indistinguishable from human beings [20].
Even though the entire framework of IIT is based on just a few axioms and postulates, it is
not possible in practice to exhaustively apply the postulates to unfold the cause–effect power of
realistic systems [32, 56]. It is not feasible to perform all possible observations and manipulations to fully characterize a universal TPM, or to perform all calculations on the TPM that
would be necessary to condense it exhaustively into complexes and unfold their cause–effect
power in full. The number of possible systems, of system partitions, of candidate distinctions
—each with their partitions and relations—is the result of multiple, nested combinatorial
explosions. Moreover, these observations, manipulations, and calculations would need to be
repeated at many different grains, with many rounds of maximizations. For these reasons, a
full analysis of complexes and their cause–effect structure can only be performed on idealized
systems of a few units [37].
On the other hand, we can simplify the computation considerably by using various assumptions and approximations, as with the “cut one” approximation described in [37]. Also, while
the number of relations vastly exceeds the number of units and of distinctions (its upper
bound for a system of _n_ units is 2 [ð][2] _[n]_ [�] [1][Þ]                     - 1), it can be determined analytically, and so can ∑ _φr_
for a given set of distinctions S3 Text. Developing tight approximations, as well as bounded
estimates of a system’s integrated information ( _φs_ and _Φ_ ), is one of the main areas of ongoing
research related to IIT [50].
Despite the infeasibility of an exhaustive calculation of the relevant quantities and structures
for a realistic system, IIT already provides considerable explanatory and predictive power in
many real-world situations, making it eminently testable [4, 57, 58]. A fundamental prediction
is that _Φ_ should be high in conscious states, such as wakefulness and dreaming, and low in
unconscious states, such as dreamless sleep and anesthesia. This prediction has already found
substantial support in human studies that have applied measures of complexity inspired by IIT
to successfully classify subjects as conscious vs. unconscious [4, 22, 23, 59]. IIT can also
account mechanistically for the loss of consciousness in deep sleep and anesthesia [4, 47]. Furthermore, it can provide a principled account of why certain portions of the brain may constitute an ideal substrate of consciousness and others may not, why the borders of the main
complex in the brain should be where they are, and why the units of the complex should have
a particular grain (the one that yields a maximum of _φs_ ). A stringent prediction is that the location of the main complex, as determined by the overall maximum of _φs_ within the brain,
should correspond to its location as determined through clinical and experimental evidence.


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 39 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


Another prediction that follows from first principles is that constituents of the main complex
can support conscious contents even if they are mostly inactive, but not if they are inactivated

[4, 11]. Yet another prediction is that the complete inactivation of constituents of the main
complex should lead to absolute agnosia (unawareness that anything is missing).
IIT further predicts that the quality of experience should be accounted for by the way the
_Φ_ -structure is composed, which in turn depends on the architecture of the substrate specifying
it. This was demonstrated in a recent paper showing how the fundamental properties of spatial
experiences—those that make space feel “extended”—can be accounted for by those of _Φ_                     structures specified by 2D grids of units, such as those found in much of posterior cortex [11].
This prediction is in line with neurological evidence of their role in supporting the experience
of space [11]. Ongoing work aims at accounting for the quality of experienced time and that of
experienced objects (see (16) in S1 Notes). A related prediction is that changes in the strength
of connections within the neural substrate of consciousness should be associated with changes
in experience, even if neural activity does not change [60]. Also, similarities and dissimilarities
in the structure of experience should be accounted for by similarities and dissimilarities
among _Φ_ -structures and _Φ_ -folds specified by the neural substrate of consciousness.
While the listed predictions may appear largely qualitative in nature, many of them rest on
specific features of the accompanying quantitative analysis. This is the case for predictions
regarding the borders (and grain) of the main complex in the brain, which depend on the relative _φs_ values of potential substrates of interest, and even more so for predictions regarding the
quality and richness of certain experiences and the predicted features of their underlying substrates. IIT’s postulates, and the mathematical framework proposed to evaluate them, rest on
“inferences to a good explanation” (Box 1). While we have aimed for maximal consistency,
specificity, and simplicity at every junction in formulating IIT’s mathematical implementation,
some of the algorithmic choices remain open to further evaluation. These include, for example,
the proper treatment of background conditions and the resolution of ties given symmetries in
the TPMs of specific systems (see S1 Text). More generally, further validation of IIT will
depend on a systematic back-and-forth between phenomenology, theoretical inferences, and
neuroscientific evidence [1].
In addition to empirical work aimed at validating the theory, much remains to be done at
the theoretical level. According to IIT, the meaning of an experience is its feeling—whether
those of spatial extendedness, of temporal flow, or of objects, to name but a few (“the meaning
is the feeling”). This means that every meaning is identical to a sub-structure within a current
_Φ_ -structure—a content of experience—whether it is triggered by extrinsic inputs or it occurs
spontaneously during a dream. Therefore, all meaning is ultimately intrinsic. Ongoing work
aims at providing a self-consistent explanation of how intrinsic meanings can capture relevant
features of causal processes in the environment (see (17) in S1 Notes). It will also be important
to explain how intersubjectively validated knowledge can be obtained despite the intrinsic and
partially idiosyncratic nature of meaning.
To the extent that the theory is validated through empirical evidence obtained from the
human brain, IIT can then offer a plausible inferential basis for addressing several questions
that depend on an explicit theory of consciousness. As indicated in the section on phenomenal
and functional equivalence, and argued in ongoing work [20], one consequence of IIT is that
typical computer architectures are not suitable for supporting consciousness, no matter
whether their behavior may resemble ours. By the same token, it can be inferred from IIT that
animal species that may look and behave quite differently from us may be highly conscious, as
long as their brains have a compatible architecture. Other inferences concern our own experience and whether it plays a causal role, or is simply “along for the ride” while our brain performs its functions. As recently argued, IIT implies that we have true free will—that we have


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 40 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


true alternatives, make true decisions, and truly cause. Because only what truly exists (intrinsically, for itself) can truly cause, we, rather than our neurons, cause our willed actions and are
responsible for their consequences [18].
Finally, an ontology that is grounded in experience as intrinsic existence—an intrinsic
ontology—must not only provide an account of subjective existence in objective, operational
terms, but also offer a path toward a unified view of nature—of all that exists and happens.
One step in this direction is the application of the same postulates that define causal powers
(existence) to the evaluation of actual causes and effects (“what caused what” [10]). Another is
to unify classical accounts of information (as communication and storage of signals) with IIT’s
notion of information as derived from the properties of experience—that is, information as
causal, intrinsic, specific, maximally irreducible, and structured (meaningful) [8] (see also (18)
in S1 Notes). Yet another is the study of the evolution of a substrate’s causal powers as conditional probabilities that update themselves [61].
Even so, there are many ways in which IIT may turn out to be inadequate or wrong. Are
some of its assumptions, including those of a discrete, finite set of “atomic” units of cause–
effect power, incompatible with current physics [32, 62] (but see [63–66])? Are its axiomatic
basis and the formulation of axioms as postulates sound and unique? And, most critically, can
IIT survive the results of empirical investigations assessing the relationship between the quantity and quality of consciousness and its substrate in the brain?


**Supporting information**


**[S1 Text. Resolving ties in the IIT algorithm.](http://journals.plos.org/ploscompbiol/article/asset?unique&id=info:doi/10.1371/journal.pcbi.1011465.s001)** Operational process for resolving ties due to
maxima / minima in the IIT algorithm.
(PDF)


**[S2 Text. Comparison to IIT 1.0—3.0 and subsequent publications.](http://journals.plos.org/ploscompbiol/article/asset?unique&id=info:doi/10.1371/journal.pcbi.1011465.s002)** Summary of the changes
in IIT 4.0 relative to earlier versions of the theory.
(PDF)


**[S3 Text. Analytical results for the number and integrated information of relations.](http://journals.plos.org/ploscompbiol/article/asset?unique&id=info:doi/10.1371/journal.pcbi.1011465.s003)** Statement and proof of theorems describing the number of relations and the sum of their integrated
information, ∑ _φr_ .
(PDF)


**[S1 Fig. IIT Algorithm.](http://journals.plos.org/ploscompbiol/article/asset?unique&id=info:doi/10.1371/journal.pcbi.1011465.s004)** Visual summary of the algorithm for identifying complexes and
unfolding cause–effect structures.
(PDF)


**[S1 Notes. Footnotes.](http://journals.plos.org/ploscompbiol/article/asset?unique&id=info:doi/10.1371/journal.pcbi.1011465.s005)**
(PDF)


**Author Contributions**


**Conceptualization:** Larissa Albantakis, Leonardo Barbosa, Graham Findlay, Matteo Grasso,
Andrew M. Haun, William Marshall, Alireza Zaeemzadeh, Melanie Boly, Bjørn E. Juel, Jeremiah Hendren, Jonathan P. Lang, Giulio Tononi.


**Formal analysis:** Larissa Albantakis, Leonardo Barbosa, Graham Findlay, Matteo Grasso,
Andrew M. Haun, William Marshall, William G. P. Mayner, Alireza Zaeemzadeh.


**Funding acquisition:** Larissa Albantakis, William Marshall, Giulio Tononi.


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 41 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**Investigation:** Larissa Albantakis, Leonardo Barbosa, Graham Findlay, Matteo Grasso,
Andrew M. Haun, William Marshall, William G. P. Mayner, Alireza Zaeemzadeh, Bjørn E.
Juel, Shuntaro Sasai, Keiko Fujii, Isaac David.


**Methodology:** Larissa Albantakis, Leonardo Barbosa, Graham Findlay, Matteo Grasso,
Andrew M. Haun, William Marshall, William G. P. Mayner, Alireza Zaeemzadeh, Shuntaro
Sasai, Keiko Fujii, Giulio Tononi.


**Project administration:** Jonathan P. Lang, Giulio Tononi.


**Software:** William G. P. Mayner, Isaac David.


**Supervision:** Larissa Albantakis, Giulio Tononi.


**Validation:** Larissa Albantakis.


**Visualization:** Larissa Albantakis, Matteo Grasso.


**Writing – original draft:** Larissa Albantakis, Giulio Tononi.


**Writing – review & editing:** Leonardo Barbosa, Graham Findlay, Matteo Grasso, Andrew M.
Haun, William Marshall, William G. P. Mayner, Alireza Zaeemzadeh, Bjørn E. Juel, Isaac
David, Jeremiah Hendren, Jonathan P. Lang.


**References**


**1.** Ellia F, Hendren J, Grasso M, Kozma C, Mindt G, P Lang J, M Haun A, Albantakis L, Boly M, and Tononi
G. Consciousness and the fallacy of misplaced objectivity. Neuroscience of Consciousness. 2021;
[2021(2):1–12. https://doi.org/10.1093/nc/niab032 PMID: 34667639](https://doi.org/10.1093/nc/niab032)


**2.** [Nagel T. What is it like to be a bat? The philosophical review. 1974; 83(4):435–450. https://doi.org/10.](https://doi.org/10.2307/2183914)
[2307/2183914](https://doi.org/10.2307/2183914)


**3.** [Tononi G. Integrated information theory. Scholarpedia. 2015; 10(1):4164. https://doi.org/10.4249/](https://doi.org/10.4249/scholarpedia.4164)
[scholarpedia.4164](https://doi.org/10.4249/scholarpedia.4164)


**4.** Tononi G, Boly M, Massimini M, Koch C. Integrated information theory: from consciousness to its physi[cal substrate. Nature Reviews Neuroscience. 2016; 17(7):450–461. https://doi.org/10.1038/nrn.2016.](https://doi.org/10.1038/nrn.2016.44)
[44 PMID: 27225071](https://doi.org/10.1038/nrn.2016.44)


**5.** [Tononi G, Sporns O. Measuring information integration. BMC neuroscience. 2003; 4(31):1–20. https://](https://doi.org/10.1186/1471-2202-4-31)
[doi.org/10.1186/1471-2202-4-31 PMID: 14641936](https://doi.org/10.1186/1471-2202-4-31)


**6.** [Tononi G. An information integration theory of consciousness. BMC neuroscience. 2004; 5:42. https://](https://doi.org/10.1186/1471-2202-5-42)
[doi.org/10.1186/1471-2202-5-42 PMID: 15522121](https://doi.org/10.1186/1471-2202-5-42)


**7.** Balduzzi D, Tononi G. Integrated information in discrete dynamical systems: motivation and theoretical
[framework. PLoS Comput Biol. 2008; 4(6):e1000091. https://doi.org/10.1371/journal.pcbi.1000091](https://doi.org/10.1371/journal.pcbi.1000091)
[PMID: 18551165](http://www.ncbi.nlm.nih.gov/pubmed/18551165)


**8.** Oizumi M, Albantakis L, Tononi G. From the Phenomenology to the Mechanisms of Consciousness:
[Integrated Information Theory 3.0. PLoS Computational Biology. 2014; 10(5):e1003588. https://doi.org/](https://doi.org/10.1371/journal.pcbi.1003588)
[10.1371/journal.pcbi.1003588 PMID: 24811198](https://doi.org/10.1371/journal.pcbi.1003588)


**9.** Balduzzi D, Tononi G. Qualia: the geometry of integrated information. PLoS computational biology.
[2009; 5(8):e1000462. https://doi.org/10.1371/journal.pcbi.1000462 PMID: 19680424](https://doi.org/10.1371/journal.pcbi.1000462)


**10.** Albantakis L, Marshall W, Hoel E, Tononi G. What caused what? A quantitative account of actual causa[tion using dynamical causal networks. Entropy. 2019; 21(5):459. https://doi.org/10.3390/e21050459](https://doi.org/10.3390/e21050459)
[PMID: 33267173](http://www.ncbi.nlm.nih.gov/pubmed/33267173)


**11.** Haun AM, Tononi G. Why Does Space Feel the Way it Does? Towards a Principled Account of Spatial
[Experience. Entropy. 2019; 21(12):1160. https://doi.org/10.3390/e21121160](https://doi.org/10.3390/e21121160)


**12.** Barbosa LS, Marshall W, Albantakis L, Tononi G. Mechanism Integrated Information. Entropy. 2021; 23
[(3):362. https://doi.org/10.3390/e23030362 PMID: 33803765](https://doi.org/10.3390/e23030362)


**13.** Marshall W, Grasso M, Mayner WG, Zaeemzadeh A, Barbosa LS, Chastain E, et al. System Integrated
[Information. Entropy. 2023; 25. https://doi.org/10.3390/e25020334 PMID: 36832700](https://doi.org/10.3390/e25020334)


**14.** Barbosa LS, Marshall W, Streipert S, Albantakis L, Tononi G. A measure for intrinsic information. Scien[tific Reports. 2020; 10(1):18803. https://doi.org/10.1038/s41598-020-75943-4 PMID: 33139829](https://doi.org/10.1038/s41598-020-75943-4)


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 42 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**15.** [Intrinsic Ontology Wiki;. Available from: https://centerforsleepandconsciousness.psychiatry.wisc.edu/](https://centerforsleepandconsciousness.psychiatry.wisc.edu/intrinsic-ontology-wiki/)
[intrinsic-ontology-wiki/.](https://centerforsleepandconsciousness.psychiatry.wisc.edu/intrinsic-ontology-wiki/)


**16.** Albantakis L. Integrated information theory. In: Overgaard M, Mogensen J, Kirkeby-Hinrup A, editors.
Beyond Neural Correlates of Consciousness. Routledge; 2020. p. 87–103.


**17.** Grasso M, Albantakis L, Lang JP, Tononi G. Causal reductionism and causal structures. Nature Neuro[science. 2021; 24(10):1348–1355. https://doi.org/10.1038/s41593-021-00911-8 PMID: 34556868](https://doi.org/10.1038/s41593-021-00911-8)


**18.** Tononi G, Albantakis L, Boly M, Cirelli C, Koch C. Only what exists can cause: An intrinsic view of free
will. 2022.


**19.** Tononi G, Koch C. Consciousness: here, there and everywhere? Philosophical transactions of the
[Royal Society of London Series B, Biological sciences. 2015; 370:20140167–. https://doi.org/10.1098/](https://doi.org/10.1098/rstb.2014.0167)
[rstb.2014.0167 PMID: 25823865](https://doi.org/10.1098/rstb.2014.0167)


**20.** Findlay G, Marshall W, Albantakis L, Mayner WGP, Koch C, Tononi G. Dissociating Intelligence from
Consciousness in Artificial Systems – Implications of Integrated Information Theory. In: Proceedings of
the 2019 Towards Conscious AI Systems Symposium, AAAI SSS19; 2019 and forthcoming.


**21.** Albantakis L, Prentner R, Durham I. Measuring the integrated information of a quantum mechanism.
Entropy. 2023; 25.


**22.** Massimini M, Ferrarelli F, Huber R, Esser SK, Singh H, Tononi G. Breakdown of cortical effective con[nectivity during sleep. Science. 2005; 309(5744):2228–2232. https://doi.org/10.1126/science.1117256](https://doi.org/10.1126/science.1117256)
[PMID: 16195466](http://www.ncbi.nlm.nih.gov/pubmed/16195466)


**23.** Casarotto S, Comanducci A, Rosanova M, Sarasso S, Fecchio M, Napolitani M, et al. Stratification of
unresponsive patients by an independently validated index of brain complexity. Annals of Neurology.
[2016; 80(5):718–729. https://doi.org/10.1002/ana.24779 PMID: 27717082](https://doi.org/10.1002/ana.24779)


**24.** Comolatti, R et al. Why does time feel flowing?; in preparation.


**25.** Grasso, M et al. How do phenomenal objects bind general concepts with particular features?; in
preparation.


**26.** Janzing D, Balduzzi D, Grosse-Wentrup M, Scho¨lkopf B. Quantifying causal influences. The Annals of
[Statistics. 2013; 41(5):2324–2358. https://doi.org/10.1214/13-AOS1145](https://doi.org/10.1214/13-AOS1145)


**27.** Ay N, Polani D. Information Flows in Causal Networks. Advances in Complex Systems. 2008; 11
[(01):17–41. https://doi.org/10.1142/S0219525908001465](https://doi.org/10.1142/S0219525908001465)


**28.** Pearl J. Causality: models, reasoning and inference. vol. 29. Cambridge Univ Press; 2000.


**29.** Albantakis L, Tononi G. Causal Composition: Structural Differences among Dynamically Equivalent
Systems. Entropy 2019, Vol 21, Page 989. 2019; 21(10):989.


**30.** Cooper J. Plato: Complete Works. Hackett; 1997.


**31.** Tillemans T. Dharmak?rti. In: Zalta EN, editor. The Stanford Encyclopedia of Philosophy. Spring 2021
ed. Metaphysics Research Lab, Stanford University; 2021.


**32.** Barrett AB, Mediano PAM. The phi measure of integrated information is not well-defined for general
physical systems. Journal of Consciousness Studies. 2019; 26(1-2):11–20.


**33.** Hoel EP, Albantakis L, Marshall W, Tononi G. Can the macro beat the micro? Integrated information
[across spatiotemporal scales. Neuroscience of Consciousness. 2016; 2016(1). https://doi.org/10.1093/](https://doi.org/10.1093/nc/niw012)
[nc/niw012 PMID: 30788150](https://doi.org/10.1093/nc/niw012)


**34.** Marshall W, Albantakis L, Tononi G. Black-boxing and cause-effect power. PLOS Computational Biol[ogy. 2018; 14(4):e1006114. https://doi.org/10.1371/journal.pcbi.1006114 PMID: 29684020](https://doi.org/10.1371/journal.pcbi.1006114)


**35.** Hoel EP, Albantakis L, Tononi G. Quantifying causal emergence shows that macro can beat micro.
[PNAS. 2013; 110(49):19790–19795. https://doi.org/10.1073/pnas.1314922110 PMID: 24248356](https://doi.org/10.1073/pnas.1314922110)


**36.** Krohn S, Ostwald D. Computing integrated information. Neuroscience of Consciousness. 2017; 2017
[(1). https://doi.org/10.1093/nc/nix017 PMID: 30042849](https://doi.org/10.1093/nc/nix017)


**37.** Mayner WGP, Marshall W, Albantakis L, Findlay G, Marchman R, Tononi G. PyPhi: A toolbox for inte[grated information theory. PLoS Computational Biology. 2018; 14(7):e1006343. https://doi.org/10.](https://doi.org/10.1371/journal.pcbi.1006343)
[1371/journal.pcbi.1006343 PMID:](https://doi.org/10.1371/journal.pcbi.1006343) [30048445](http://www.ncbi.nlm.nih.gov/pubmed/30048445)


**38.** Kanwisher N. Functional specificity in the human brain: a window into the functional architecture of the
[mind. Proceedings of the National Academy of Sciences. 2010; 107(25):11163–11170. https://doi.org/](https://doi.org/10.1073/pnas.1005062107)
[10.1073/pnas.1005062107](https://doi.org/10.1073/pnas.1005062107)


**39.** Ponce CR, Xiao W, Schade PF, Hartmann TS, Kreiman G, Livingstone MS. Evolving images for visual
neurons using a deep generative network reveals coding principles and neuronal preferences. Cell.
[2019; 177(4):999–1009. https://doi.org/10.1016/j.cell.2019.04.005 PMID: 31051108](https://doi.org/10.1016/j.cell.2019.04.005)


**40.** Khosla M, Wehbe L. High-level visual areas act like domain-general filters with strong selectivity and
functional specialization. bioRxiv. 2022.


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 43 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**41.** Mainen ZF, Sejnowski TJ. Reliability of spike timing in neocortical neurons. Science. 1995; 268
[(5216):1503–1506. https://doi.org/10.1126/science.7770778 PMID: 7770778](https://doi.org/10.1126/science.7770778)


**42.** Hires SA, Gutnisky DA, Yu J, O’Connor DH, Svoboda K. Low-noise encoding of active touch by layer 4
[in the somatosensory cortex. eLife. 2015; 4:e06619. https://doi.org/10.7554/eLife.06619 PMID:](https://doi.org/10.7554/eLife.06619)
[26245232](http://www.ncbi.nlm.nih.gov/pubmed/26245232)


**43.** Nolte M, Reimann MW, King JG, Markram H, Muller EB. Cortical reliability amid noise and chaos.
[Nature Communications. 2019; 10(1):1–15. https://doi.org/10.1038/s41467-019-11633-8 PMID:](https://doi.org/10.1038/s41467-019-11633-8)
[31439838](http://www.ncbi.nlm.nih.gov/pubmed/31439838)


**44.** [Lemon R, Edgley S. Life without a cerebellum. Brain. 2010; 133(3):652–654. https://doi.org/10.1093/](https://doi.org/10.1093/brain/awq030)
[brain/awq030 PMID: 20305277](https://doi.org/10.1093/brain/awq030)


**45.** Yu F, Jiang Qj, Sun Xy, Zhang Rw. A new case of complete primary cerebellar agenesis: clinical and
[imaging findings in a living patient. Brain. 2015; 138(6):e353–e353. https://doi.org/10.1093/brain/](https://doi.org/10.1093/brain/awu239)
[awu239 PMID: 25149410](https://doi.org/10.1093/brain/awu239)


**46.** Steriade M, Nunez A, Amzica F. A novel slow (< 1 Hz) oscillation of neocortical neurons in vivo: depolar[izing and hyperpolarizing components. Journal of Neuroscience. 1993; 13(8):3252–3265. https://doi.](https://doi.org/10.1523/JNEUROSCI.13-08-03252.1993)
[org/10.1523/JNEUROSCI.13-08-03252.1993 PMID: 8340806](https://doi.org/10.1523/JNEUROSCI.13-08-03252.1993)


**47.** Pigorini A, Sarasso S, Proserpio P, Szymanski C, Arnulfo G, Casarotto S, et al. Bistability breaks-off
deterministic responses to intracortical stimulation during non-REM sleep. Neuroimage. 2015;
[112:105–113. https://doi.org/10.1016/j.neuroimage.2015.02.056 PMID: 25747918](https://doi.org/10.1016/j.neuroimage.2015.02.056)


**48.** Middleton FA, Strick PL. Basal ganglia and cerebellar loops: motor and cognitive circuits. Brain
[Research Reviews. 2000; 31(2-3):236–250. https://doi.org/10.1016/S0165-0173(99)00040-5 PMID:](https://doi.org/10.1016/S0165-0173(99)00040-5)
[10719151](http://www.ncbi.nlm.nih.gov/pubmed/10719151)


**49.** Foster NN, Barry J, Korobkova L, Garcia L, Gao L, Becerra M, et al. The mouse cortico–basal ganglia–
[thalamic network. Nature. 2021; 598(7879):188–194. https://doi.org/10.1038/s41586-021-03993-3](https://doi.org/10.1038/s41586-021-03993-3)
[PMID: 34616074](http://www.ncbi.nlm.nih.gov/pubmed/34616074)


**50.** Zaeemzadeh, A et al. Upper Bounds for Integrated Information; in preparation.


**51.** Boly M, Massimini M, Tsuchiya N, Postle BR, Koch C, Tononi G. Are the neural correlates of consciousness in the front or in the back of the cerebral cortex? Clinical and neuroimaging evidence. Journal of
[Neuroscience. 2017; 37(40):9603–9613. https://doi.org/10.1523/JNEUROSCI.3218-16.2017 PMID:](https://doi.org/10.1523/JNEUROSCI.3218-16.2017)
[28978697](http://www.ncbi.nlm.nih.gov/pubmed/28978697)


**52.** Watakabe A, Skibbe H, Nakae K, Abe H, Ichinohe N, Rachmadi MF, et al. Local and long-distance organization of prefrontal cortex circuits in the marmoset brain. bioRxiv. 2022.


**53.** Hanson JR, Walker SI. Formalizing falsification for theories of consciousness across computational
[hierarchies. Neuroscience of Consciousness. 2021; 2021(2). https://doi.org/10.1093/nc/niab014 PMID:](https://doi.org/10.1093/nc/niab014)
[34377534](http://www.ncbi.nlm.nih.gov/pubmed/34377534)


**54.** Krohn K, Rhodes J. Algebraic Theory of Machines. I. Prime Decomposition Theorem for Finite Semi[groups and Machines. Transactions of the American Mathematical Society. 1965; 116:450. https://doi.](https://doi.org/10.1090/S0002-9947-1965-0188316-1)
[org/10.1090/S0002-9947-1965-0188316-1](https://doi.org/10.1090/S0002-9947-1965-0188316-1)


**55.** Albantakis L, Tononi G. The Intrinsic Cause-Effect Power of Discrete Dynamical Systems–From Ele[mentary Cellular Automata to Adapting Animats. Entropy. 2015; 17(8):5472–5502. https://doi.org/10.](https://doi.org/10.3390/e17085472)
[3390/e17085472](https://doi.org/10.3390/e17085472)


**56.** Moyal R, Fekete T, Edelman S. Dynamical Emergence Theory (DET): A Computational Account of Phe[nomenal Consciousness. Minds and Machines. 2020; 30(1):1–21. https://doi.org/10.1007/s11023-020-](https://doi.org/10.1007/s11023-020-09516-9)
[09516-9](https://doi.org/10.1007/s11023-020-09516-9)


**57.** Melloni L, Mudrik L, Pitts M, Koch C. Making the hard problem of consciousness easier. Science. 2021;
[372(6545):911–912. https://doi.org/10.1126/science.abj3259 PMID: 34045342](https://doi.org/10.1126/science.abj3259)


**58.** Sarasso S, Casali AG, Casarotto S, Rosanova M, Sinigaglia C, Massimini M, et al. Consciousness and
complexity: a consilience of evidence. Neuroscience of Consciousness. 2021; 7(2):1–24.


**59.** Sarasso S, D’Ambrosio S, Fecchio M, Casarotto S, Viganò A, Landi C, et al. Local sleep-like cortical
[reactivity in the awake brain after focal injury. Brain. 2020; 143(12):3672–3684. https://doi.org/10.1093/](https://doi.org/10.1093/brain/awaa338)
[brain/awaa338 PMID: 33188680](https://doi.org/10.1093/brain/awaa338)


**60.** [Song C, Haun AM, Tononi G. Plasticity in the structure of visual space. Eneuro. 2017; 4(3). https://doi.](https://doi.org/10.1523/ENEURO.0080-17.2017)
[org/10.1523/ENEURO.0080-17.2017 PMID: 28660245](https://doi.org/10.1523/ENEURO.0080-17.2017)


**61.** Albantakis L, Hintze A, Koch C, Adami C, Tononi G. Evolution of Integrated Causal Structures in Animats Exposed to Environments of Increasing Complexity. PLoS computational biology. 2014; 10(12):
[e1003966. https://doi.org/10.1371/journal.pcbi.1003966 PMID: 25521484](https://doi.org/10.1371/journal.pcbi.1003966)


**62.** Carroll S. Consciousness and the Laws of Physics. Journal of Consciousness Studies. 2021; 28(9):16–
[31. https://doi.org/10.53765/20512201.28.9.016](https://doi.org/10.53765/20512201.28.9.016)


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 44 / 45


PLOS COMPUTATIONAL BIOLOGY Integrated information theory (IIT) 4.0


**63.** Zanardi P, Tomka M, Venuti LC. Towards Quantum Integrated Information Theory. arXiv.
2018;1806.01421.


**64.** Kleiner J, Tull S. The Mathematical Structure of Integrated Information Theory. Frontiers in Applied
[Mathematics and Statistics. 2021; 6:74. https://doi.org/10.3389/fams.2020.602973](https://doi.org/10.3389/fams.2020.602973)


**65.** Esteban FJ, Galadı´ JA, Langa JA, Portillo JR, Soler-Toscano F. Informational structures: A dynamical
system approach for integrated information. PLOS Computational Biology. 2018; 14(9):e1006154.
[https://doi.org/10.1371/journal.pcbi.1006154 PMID: 30212467](https://doi.org/10.1371/journal.pcbi.1006154)


**66.** Kalita P, Langa JA, Soler-Toscano F. Informational Structures and Informational Fields as a Prototype
[for the Description of Postulates of the Integrated Information Theory. Entropy. 2019; 21(5):493. https://](https://doi.org/10.3390/e21050493)
[doi.org/10.3390/e21050493 PMID: 33267207](https://doi.org/10.3390/e21050493)


[PLOS Computational Biology | https://doi.org/10.1371/journal.pcbi.1011465](https://doi.org/10.1371/journal.pcbi.1011465) October 17, 2023 45 / 45


