Under review as a conference paper at ICLR 2026

# MAMBA-3: IMPROVED SEQUENCE MODELING USING STATE SPACE PRINCIPLES


**Anonymous authors**
Paper under double-blind review


ABSTRACT


The recent scaling of test-time compute for LLMs has restricted the practical deployment of models to those with strong capabilities that can generate high-quality
outputs in an inference-efficient manner. While current Transformer-based models are the standard, their quadratic compute and linear memory bottlenecks have
spurred the development of sub-quadratic models with linear-scaling compute
with constant memory requirements. However, many recent linear-style models
lack certain capabilities or lag behind in quality, and even their linear-time inference is not hardware-efficient. Guided by an inference-first perspective, we introduce three core methodological improvements inspired by the state-space model
viewpoint of linear models. We combine a: 1) more expressive recurrence derived
from discretization, 2) complex-valued state update rule that enables richer
state tracking, and 3) multi-input, multi-output formulation together, resulting
in a stronger model. Together with architectural refinements, our **Mamba-3**
model achieves significant gains across retrieval, state-tracking, and downstream
language modeling tasks. Our new architecture sets the Pareto-frontier for performance under a fixed inference budget and outperforms strong baselines in a
head-to-head comparison.


1 INTRODUCTION


Test-time compute has emerged as a key driver of progress in AI, with techniques like chain-ofthought reasoning and iterative refinement demonstrating that inference-time scaling can unlock
new capabilities (Wu et al., 2025; Snell et al., 2024). This paradigm shift makes inference efficiency (Kwon et al., 2023; Li et al., 2024) paramount, as the practical impact of AI systems now
depends critically on their ability to perform large-scale inference during deployment. Model architecture design plays a fundamental role in determining inference efficiency, as architectural choices
directly dictate the computational and memory requirements during generation. While Transformerbased models (Vaswani et al., 2017) are the current industry standard, they are fundamentally bottlenecked by linearly increasing memory demands through the KV cache and quadratically increasing
compute requirements through the self-attention mechanism. These drawbacks have motivated recent lines of work on sub-quadratic models, e.g., state-space models (SSMs), which, despite utilizing
only constant memory and linear compute, have comparable or better performance than their Transformer counterparts. Models that benefit the most from this new scaling paradigm perform well on
the following three axes: (i) quality, (ii) capability, and (iii) inference efficiency.


Recent model architectures have tried to strike a balance between the three, but many fall short on
at least one of these three axes. In particular, Mamba-2 and Gated DeltaNet (GDN), which have
gained significant traction and adoption due to their inference efficiency, made architectural design
choices that enable their linear compute requirements but sacrifice quality and capabilities (Dao &
Gu, 2024; Yang et al., 2025a). For example, Mamba-2 was developed to improve training speed
and simplicity over Mamba-1 (Gu & Dao, 2024), opting out of more expressive parameterizations
of the underlying SSM and hindering the quality of the model (Dao & Gu, 2024). Linear attentionstyle models (Katharopoulos et al., 2020) have also been shown to lack certain capabilities, with
poor state-tracking abilities, e.g., determining parity of bit sequences, being one of the most notable (Grazzi et al., 2025; Sarrof et al., 2024). In addition, despite these sub-quadratic models being
prized for theoretically efficient inference, these inference algorithms are not hardware efficient. In
particular, because these algorithms were developed from a training perspective, their decoding
phase has low arithmetic intensity (the ratio of FLOPs to memory traffic), resulting in large portions
of hardware remaining idle.

1

To develop more performant models from an inference-first paradigm, we introduce three core
methodological changes on top of Mamba-2, influenced by a SSM-centric viewpoint of subquadratic models. While many recent models fall into the linear attention framework (Dao &
Gu, 2024; Yang et al., 2025a; Sun et al., 2023), we find that the classical SSM toolbox (Kalman,
1960; Gopal, 1993) leads to natural interpretations and improvements on modeling.


**Trapezoidal Discretization.** We discretize the underlying continuous-time dynamical system with
a trapezoidal methodology. The final recurrence is a more expressive superset of Mamba-2’s recurrence and can be viewed as a convolution. We combine this new discretization with applied biases
on the _B, C_, inspired by Yu & Erichson (2025), and find that their synergy is able to empirically
replace the short causal convolution in language modeling which was previously hypothesized to be
essential for recurrent models.


**Complex-valued** **State-Space** **Model.** By viewing the underlying SSM of Mamba-3 as complexvalued, we enable a more expressive state update than Mamba-2’s. This change in update rule,
designed to be lightweight for training and inference, overcomes the lack of state-tracking ability
common in many current linear models. We emphasize that our complex-valued update rule is equivalent to a data-dependent rotary embedding and can be efficiently computed (Su et al., 2023).


**Multi-Input,** **Multi-Output** **SSM.** To improve FLOP-efficiency during decoding, we shift from
outer-product-based state update to matrix-multiplication-based state update . In view of the signal
processing foundations of SSMs, such a transition exactly coincides with the generalization from
a single-input single-output (SISO) sequence dynamic to a multiple-input multiple-output (MIMO)
one. Here, we found that MIMO is particularly suitable for inference, as the extra expressivity allows
for more compute during state update, without increasing the state size and hence compromising
speed.


These three SSM-centric methodological changes are core to our **Mamba-3** mixer primitive. We
also make adjustments to the overall architecture to ensure more similarity to the baseline Transformer architecture. Mamba-3 swaps the pre-output projection norm with the more common QKnormalization (Team et al., 2025; OLMo et al., 2025) and makes the short convolution, a common
component found in many other sub-quadratic models (Gu & Dao, 2024; Yang et al., 2025a; von
Oswald et al., 2025), optional.


We empirically validate our new model on a suite of synthetic and language-modeling tasks.


- **Better Quality.** Mamba-3 matches or outperforms Mamba-2 and other open-source architectures
on standard downstream language modeling evaluations. For example, Mamba-3-1.5B’s average
accuracy on all downstream tasks is better than that of its Transformer, Mamba-2, and Gated
DeltaNet counterparts.


- **New** **Capabilities.** Mamba-3’s complexification of the SSM state enables the model to solve
synthetic state-tracking tasks that Mamba-2 cannot. We empirically demonstrate that the efficient
RoPE-like calculation is able to near perfectly solve arithmetic tasks, while Mamba-3 without
RoPE and Mamba-2 perform not better than random guessing.


- **Stronger Inference Efficiency.** Mamba-3’s MIMO variant retains the same state size while enabling better hardware utilization compared to standard Mamba-3 and other models. Its improved
performance without increased memory requirements pushes the pareto-frontier of inference efficiency.


2 PRELIMINARIES


2.1 NOTATION


Scalars are denoted by plain-text letters (e.g., _x, y_ ). Tensors, including vectors and matrices, are
denoted by bold letters (e.g., _**h**_ _,_ **C** ). The shape of the tensor can be inferred from the context. We
denote the input sequence length as _T_, the model dimension as _D_, and the SSM state size as _N_ . For
time indices, we use subscripts (e.g., _xt_ for the input at time _t_ ). The Hadamard product between two
tensors is denoted by _⊙_ . For a vector of size _**v**_ _∈_ R _[d]_, we denote Diag( _**v**_ ) _∈_ R _[d][×][d]_ as the diagonal
matrix with the vector _**v**_ as the diagonal, and for products of scalars across time steps, we use the
notation _αt···s_ = _αt_ _[×]_ : _s_ [=][ �] _i_ _[t]_ = _s_ _[α][i]_ [.]


2


2.2 SSM PRELIMINARIES


State Space Models (SSMs) describe continuous-time linear dynamics via


_**h**_ ˙ ( _t_ ) = **A** ( _t_ ) _**h**_ ( _t_ ) + **B** ( _t_ ) _x_ ( _t_ ) _,_ _y_ ( _t_ ) = **C** ( _t_ ) _[⊤]_ _**h**_ ( _t_ ) _,_


where _**h**_ ( _t_ ) _∈_ R _[N]_ is the hidden state, _x_ ( _t_ ) _∈_ R the input, and **A** ( _t_ ) _∈_ R _[N]_ _[×][N]_, **B** ( _t_ ) _,_ **C** ( _t_ ) _∈_ R _[N]_ . For
discrete sequences with step size ∆ _t_, Euler’s discretization gives the recurrence


_**h**_ _t_ = _e_ [∆] _[t]_ **[A]** _[t]_ _**h**_ _t−_ 1 + ∆ _t_ **B** _t xt,_ _yt_ = **C** _[⊤]_ _t_ _**[h]**_ _[t][.]_


**Mamba-2’s parameterization.** Mamba-2 (Dao & Gu, 2024) makes the SSM _data-dependent_ and
hardware-efficient by (i) projecting _A_ = **A** _∈_ R _<_ 0, and **B** _,_ **C** _∈_ R _[N]_ from the current token and (ii)
choosing transition matrix _A_ = **A** as a data-dependent scalar. Writing _αt_ := _e_ [∆] _[t][A][t]_ _∈_ (0 _,_ 1) and
_γt_ := ∆ _t_, the update becomes


_**h**_ _t_ = _αt_ _**h**_ _t−_ 1 + _γt_ **B** _t xt,_ _yt_ = **C** _[⊤]_ _t_ _**[h]**_ _[t][.]_


The scalar _At_ _<_ 0 is an input-dependent _forget-gate_ _(decay)_ _αt_, and the parameter _selectivity_ ∆ _t_
jointly controls the forget-gate ( _αt_ = exp(∆ _tAt_ )) and the input-gate ( _γt_ = ∆ _t_ ): larger ∆ _t_ forgets
faster and up-weights the current token more strongly, while smaller ∆ _t_ retains the hidden state with
minimal contributions from the current token.


2.3 STRUCTURED MASKED REPRESENTATION AND STATE SPACE DUALITY


Dao & Gu (2024) show that a large class of SSMs admit a _matrix_ form that vectorizes the time-step
recurrence. For instance, Mamba-2’s recurrence can be vectorized as a masked matrix multiplication,



where **L** _∈_ R _[T][ ×][T]_ is the structured mask, **B** _,_ **C** _∈_ R _[T][ ×][N]_, **X** _∈_ R _[T][ ×][D]_ is the input to the SSM and
**Y** _∈_ R _[T][ ×][D]_ is its output. Within this form, Mamba-2 can be viewed as a type of linear attention by
setting **Q** = **C**, **K** = **B**, **V** = **X** and viewing **L** as a causal, data-dependent mask. When all _α_ = 1,
the expression reduces to (causal) linear attention (Katharopoulos et al., 2020). A more detailed
coverage of related linear-time sequence mixers can be found at Appendix A.


3 MODEL DESIGN FROM A STATE-SPACE VIEWPOINT


We introduce Mamba-3, with three new innovations rooted in classical state-space theory: trapezoidal discretization for more expressive dynamics, complex-valued state spaces for state-tracking,
and multi-input multi-output (MIMO) to improve hardware utilization. These advances address the
quality, capability, and efficiency limitations of current sub-quadratic architectures.


3.1 TRAPEZOIDAL DISCRETIZATION


Structured SSMs are naturally defined as continuous-time dynamical systems that map input functions, _x_ ( _t_ ) _∈_ R, to output functions, _y_ ( _t_ ) _∈_ R, for time _t_ _>_ 0. In sequence modeling, however,
the data is only observed at discrete time steps, which then requires applying a _discretization_ _step_
to the SSM to transform its continuous-time dynamics into a discrete recurrence. The preliminary
step in deriving Mamba-3’s discretization is to apply the Variation of Constants formula (Proposition 5), which decomposes the hidden state into an exponentially decay term and a state update term
“information” term dependent on the most recent inputs.


The first step in deriving the discretized recurrence is to approximate the “state-update” integral in
equation 10. A straightforward choice, used in Mamba-2, is applying _Euler’s rule_ (S¨uli & Mayers,
2003), which approximates the integral by holding the (right) endpoint constant throughout the
interval (Fig. 1). This yields Mamba-2’s recurrence,


_**h**_ _t_ = _e_ [∆] _[t][A][t]_ _**h**_ _t−_ 1 + ( _τt −_ _τt−_ 1) _e_ [(] _[τ][t][−][τ][t]_ [)] _[A][t]_ **B** _t xt_
_≈_ _e_ [∆] _[t][A][t]_ _**h**_ _t−_ 1 + ∆ _t_ **B** _t xt._ (2)


3















**Y** = ( **L** _⊙_ **CB** [¯] _[⊤]_ ) **X** =
















 (1)
 **[X]** _[,]_



1
_α_ 1 1
... ...
_αT..._ 1 _· · ·_ _αT_ 1



 _⊙_ **CB** _⊤_


Under review as a conference paper at ICLR 2026



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/13549_Mamba_3_Improved_Sequenc_extracted/images/13549_Mamba_3_Improved_Sequenc.pdf-3-3.png)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/13549_Mamba_3_Improved_Sequenc_extracted/images/13549_Mamba_3_Improved_Sequenc.pdf-3-0.png)

![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/13549_Mamba_3_Improved_Sequenc_extracted/images/13549_Mamba_3_Improved_Sequenc.pdf-3-1.png)

![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/13549_Mamba_3_Improved_Sequenc_extracted/images/13549_Mamba_3_Improved_Sequenc.pdf-3-4.png)

![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/13549_Mamba_3_Improved_Sequenc_extracted/images/13549_Mamba_3_Improved_Sequenc.pdf-3-6.png)

Here, the first factor is precisely the lower-triangular decay mask from Mamba-2, while the second
factor encodes the size two convolution induced by the trapezoidal rule through the coefficients
( _βt, γt_ ). We provide a rigorous proof for this decomposition in Appendix B.1.

3.2 COMPLEX-VALUED SSMS


Modern SSMs are designed with efficiency as the central goal, motivated by the need to scale to
larger models and longer sequences. For instance, successive architectures have progressively simplified the state transition matrix: S4 (Gu et al., 2022a) used complex-valued Normal plus Low Rank
(NPLR) matrices, Mamba (Gu & Dao, 2024) reduced this to a diagonal of reals, and Mamba-2 (Dao
& Gu, 2024) further simplified it to a single scalar. Although these simplifications largely maintain
language modeling performance, recent works (Merrill et al., 2025; Sarrof et al., 2024; Grazzi et al.,
2025) have shown that they degrade the capabilities of the model on simple state-tracking tasks such
as parity and modular arithmetic, which can be solved by a one-layer LSTM.


4




## ℳ [=]













𝑡!"# 𝑡! 𝑡!"# 𝑡!



Figure 1: **Left:** The structured mask induced by the generalized trapezoid rule is a product of the
decay and convolutional mask. **Right:** Euler (hold endpoint) vs trapezoidal rule (average endpoints).


However, Euler’s rule provides only a first-order approximation to the “state-update” integral: local
truncation error is _O_ (∆ [2] _t_ [)][, which accumulates across steps to yield a global error of] _[ O]_ [(∆] _[t]_ [)][ over the]
sequence. In contrast, we adopt a _generalized trapezoidal rule_, which provides a second-order accurate approximation of the integral, offering improved accuracy over the Euler’s rule. Specifically,
it approximates the integral with a _data-dependent, convex combination of both interval endpoints_ .
This generalization extends the classical trapezoidal rule (S¨uli & Mayers, 2003), which simply averages the interval endpoints, by allowing for a _data-dependent convex combination_ (Fig. 1).


**Proposition** **1** (Generalized Trapezoidal Discretization) **.** _Approximating_ _the_ _state-update_ _integral_
_in equation 10 by the general trapezoidal rule yields the recurrence,_


_**h**_ _t_ = _e_ [∆] _[t][A][t]_ _**h**_ _t−_ 1 + (1 _−_ _λt_ )∆ _te_ [∆] _[t][A][t]_ **B** _t−_ 1 _xt−_ 1 + _λt_ ∆ _t_ **B** _txt,_ (3)
:= _αt_ _**h**_ _t−_ 1 + _βt_ **B** _t−_ 1 _xt−_ 1 + _γt_ **B** _txt,_ (4)


_where λt_ _∈_ [0 _,_ 1] _is a data-dependent scalar, αt_ := _e_ [∆] _[t][A][t]_ _, βt_ := (1 _−_ _λt_ )∆ _te_ [∆] _[t][A][t]_ _, γt_ := _λt_ ∆ _t._


_Remark_ 1 (Expressivity) _._ Our scheme is a generalization of a) The classical trapezoid rule which is
recovered when _λt_ = [1] 2 [.] [b) Mamba-2’s Euler’s rule, which is recovered when] _[ λ][t]_ [= 1][.]

_Remark_ 2 (Error Rate) _._ This is a second-order discretization with local truncation error _O_ (∆ [3] _t_ [)]
and global error _O_ (∆ [2] _t_ [)] [over] [the] [sequence] [under] [standard] [stability] [assumptions][,] [provided] [that] [the]
trapezoidal parameter satisfies _λt_ = [1] 2 [+] _[ O]_ [(∆] _[t]_ [)][.] [However, our ablations indicate that not enforcing]

this constraint is the best for empirical performance. See Appendix B.2,B.3 for details.

3.1.1 TRAPEZOIDAL DISCRETIZATION IS A CONVOLUTIONAL MASK


We can view the generalized trapezoidal discretization as applying a _data-dependent_ convolution
of size two on the projected input, **B** _txt_, to the SSM. We now show that a similar vectorization to
Equation (1) holds with the generalized trapezoidal discretization. Unrolling the recurrence starting
from _**h**_ 0 = _γ_ 0 **B** 0 _x_ 0 results in _**h**_ _T_ = _αT ···_ 2( _γ_ 0 _α_ 1 + _β_ 1) **B** 0 _x_ 0 + _· · ·_ + _γT_ **B** _T xT ._


Unrolling these rows shows that the mask induced by the trapezoidal update is no longer a fixed averaging of endpoints (as in the classical trapezoidal rule), but a _data-dependent convex combination_
of the two interval endpoints. In the SSD representation, this corresponds to a mask **L** :

     



_γ_ 0
( _γ_ 0 _α_ 1 + _β_ 1)
_α_ 2( _γ_ 0 _α_ 1 + _β_ 1) _γ_ 2
... ...
_αT ···_ 2( _γ_ 0 _α_ 1 + _β_ 1) _· · ·_ _γT_



























=








1
_α_ 1 1
_α_ 2 _α_ 1
... ...
_αT ···_ 1 _· · ·_ 1











_γ_ 0
_β_ 1
0 _γ_ 2
... ...
0 _· · ·_ _γT_



_._ (5)



This limitation, formalized in Theorem-1 of (Grazzi et al., 2024), arises from restricting the eigenvalues of the transition matrix to real numbers, which cannot represent “rotational” hidden state dynamics. For instance, consider the parity function on binary inputs _{_ 0 _,_ 1 _}_, defined as [�] _t_ _[x][t]_ [mod 2][.]

This task can be performed using update: _**h**_ _t_ = **R** ( _πxt_ ) _**h**_ _t−_ 1, where **R** ( _·_ ) is a 2-D rotation matrix.
Such rotational dynamics cannot be expressed with real eigenvalues.


To recover this capability, we begin with complex SSMs (6), which are capable of representing
state-tracking dynamics. We show that, under discretization (Proposition 5), complex SSMs can
be formulated as a real SSMs with a _block-diagonal_ _transition_ _matrix_ _composed_ _of_ 2 _×_ 2 _rotation_
_matrices_ (Proposition 2). We then show that this is equivalent to applying _data-dependent_ _rotary_
_embeddings_ on both the input and output projections **B** _,_ **C** respectively. This result establishes a
theoretical connection between complex SSMs and data-dependent RoPE embeddings (Proposition
3). Finally, this allows for an efficient implementation of the complex-valued SSM via the “RoPE
trick”, enabling efficient complex-valued state transition matrix with minimal computational overhead over real-valued SSMs.


**Proposition 2** (Complex-to-Real SSM Equivalence) **.** _Consider a complex-valued SSM_


_**h**_ ˙ ( _t_ ) = Diag� _A_ ( _t_ ) + _i_ _**θ**_ ( _t_ )� _**h**_ ( _t_ ) +       - **B** ( _t_ ) + _i_ **B** [ˆ] ( _t_ )� _x_ ( _t_ ) _,_ (6)

_y_ ( _t_ ) = Re�� **C** ( _t_ ) + _i_ **C** [ˆ] ( _t_ )� _⊤_ _**h**_ ( _t_ )� _,_


_where_ _**h**_ ( _t_ ) _∈_ C _[N/]_ [2] _,_ _**θ**_ ( _t_ ) _,_ **B** ( _t_ ) _,_ **B** [ˆ] ( _t_ ) _,_ **C** ( _t_ ) _,_ **C** [ˆ] ( _t_ ) _∈_ R _[N/]_ [2] _,_ _and_ _x_ ( _t_ ) _, A_ ( _t_ ) _∈_ R _._ _Under_ _Euler_
_discretization, this system is equivalent to a real-valued SSM_


_**h**_ _t_ = _e_ [∆] _[t][A][t]_ **R** _t_ _**h**_ _t−_ 1 + ∆ _t_ **B** _txt,_ (7)

_yt_ = **C** _[⊤]_ _t_ _**[h]**_ _[t][,]_


_with state_ _**h**_ _t_ _∈_ R _[N]_ _, projections_



_where_ _the_ _matrix_ _production_ _represents_ _right_ _matrix_ _multiplication,_ _e.g.,_ [�] _i_ [1] =0 **[R]** _[i]_ [=] **[R]** [0] **[R]** [1] _[.]_ _[We]_
_denote employing the vanilla SSM to compute the Complex SSM as “RoPE trick”._


The proof is in Appendix C.2.


To observe the connection of complex SSMs to RoPE embeddings, note that in the above proposition, the data-dependent rotations **R** _i_ are aggregated across time-steps and applied to **C** _,_ **B**, which,
by the State Space Duality of Dao & Gu (2024), correspond to the Query ( **Q** ) and Key ( **K** ) components of Attention. Analogously, vanilla RoPE (Su et al., 2023) applies _data-independent_ rotation
matrices, where the rotation angles follow a fixed frequency schedule _**θ**_ [ _i_ ] = 10000 _[−]_ [2] _[i/N]_ .


5




_∈_ R _[N]_ _,_




   - **B** _t_
**B** _t_ = **B** ˆ _t_




- - **C** _t_
_∈_ R _[N]_ _,_ **C** _t_ = _−_ **C** [ˆ] _t_



_and a transition matrix_


        -        - �cos(Θ) _−_ sin(Θ)�
**R** _t_ = _Block_ _{R_ (∆ _t_ _**θt**_ [ _i_ ]) _}_ _[N/]_ _i_ =1 [2] _∈_ R _[N]_ _[×][N]_ _,_ _R_ (Θ) = sin(Θ) cos(Θ) _._


The proof is in Appendix C.1.


Proposition 2 shows that the discretized complex SSM has an equivalent real SSM with doubled
state dimension ( _N_ ), and a block-diagonal transition matrix multiplied with a scalar decay, where
each 2 _×_ 2 block is a data-dependent rotation matrix ( _e_ [∆] _t_ _[t][A]_ **R** _t_ ). We now show that the rotations can
equivalently be absorbed into the input and output projections **B** _t,_ **C** _t_, yielding an equivalent view
that _complex SSMs are real SSMs equipped with data-dependent rotary embeddings (RoPE)_ .


**Proposition 3** (Complex SSM, Data-Dependent RoPE Equivalence) **.** _Under the notation established_
_in_ _Proposition_ _2,_ _consider_ _the_ _real_ _SSM_ _defined_ _in_ _Eq._ _7_ _unrolled_ _for_ _T_ _time-steps._ _The_ _output_ _of_
_the above SSM is equivalent to that of a vanilla scalar transition matrix-based SSM (Eq._ _2) with a_
_data-dependent rotary embedding applied on the_ **B** _,_ **C** _components of the SSM defined as:_



_t_




_t_





- **R** _[⊤]_ _i_ [)] **[C]** _[t]_

_i_ =0




         
- **R** _[⊤]_ _i_ [)] **[B]** _[t][x][t][,]_ _**y**_ _t_ = (

_i_ =0




- _⊤_
_**h**_ _t_ (8)



_**h**_ _t_ = _e_ [∆] _[t][A][t]_ _**h**_ _t−_ 1 + (



_Remark_ 3 (Generality) _._ Proposition 3 extends to the fully general case where the transition is given
by any complex matrix. By the complex diagonalization theorem, such a matrix is unitarily equivalent to a complex diagonal matrix, Diag� **A** ( _t_ ) + _i_ _**θ**_ ( _t_ )� with **A** ( _t_ ) _∈_ R _[N]_ . However, in practice,
we restrict **A** ( _t_ ) to a scalar, mirroring the simplification from Mamba to Mamba-2, to enable faster
implementation by avoiding GPU memory bottlenecks.


**Proposition** **4** (Rotary Embedding Equivalence with Trapezoidal Discretization) **.** _Discretizing_ _a_
_complex SSM with the trapezoidal rule (Proposition 1) yields the recurrence_



Figure 2: Arithmetic Intensity for (a) SISO, (b) MIMO. Batch and head dimensions cancel out.


In light of this, we made the following simple adjustment to our recurrent relation: instead of transforming the input **x** _t_ _∈_ R _[p]_ to state **H** _t_ _∈_ R _[n][×][p]_ via an outer product, i.e., **H** _t_ _←_ _at_ **H** _t−_ 1+ **b** _t⊗_ **x** _t_, we
made such a transformation via a matrix product, i.e., **H** _t_ _←_ _at_ **H** _t−_ 1 + **B** _t_ **X** _[⊤]_ _t_ [, where] **[ B]** _[t]_ _[∈]_ [R] _[n][×][r]_
and **X** _t_ _∈_ R _[p][×][r]_ are now matrices with an additional rank _r_ . The emission from state to output
similarly acquire an extra rank _r_, i.e., **Y** _t_ _∈_ R _[r][×][p]_ _←_ **C** _[⊤]_ _t_ **[H]** _[t]_ [,] [where] **[C]** _[t]_ _[∈]_ [R] _[n][×][r][,]_ **[ H]** _[t]_ _[∈]_ [R] _[n][×][p]_ [.]
This simple change increases the arithmetic intensity of recurrence, which now scales with the rank


6











_**h**_ _t_ = _αt_ _**h**_ _t−_ 1 + _βt_




- _t−_ 1

 - **R** _[⊤]_ _i_


_i_ =0

 - _⊤_



**B** _t−_ 1 _xt−_ 1 + _γt_




- _t_

 - **R** _[⊤]_ _i_


_i_ =0



**B** _txt,_



_**h**_ _t._ (9)



_**y**_ _t_ =




- _t_

 -  



- **R** _[⊤]_ _i_ [)] **[C]** _[t]_

_i_ =0



_Here_ **R** _t is the block-diagonal rotation matrix defined in Proposition 3._


The proof is in Appendix C.3.


_Remark_ 4 (RoPE Trick) _._ Complex SSMs discretized with the general trapezoidal rule of a complex
SSM naturally admit the RoPE trick we established for SSMs discretized with Euler’s rule.


3.3 MULTI-INPUT, MULTI-OUTPUT


During the decoding phase of autoregressive inference, outputs are generated one token at a time, and
performance is typically measured using in _Tokens generated Per Second (TPS)_ . In this metric, subquadratic models, such as Mamba-2 (Dao & Gu, 2024), have a significant advantage over standard
Transformer-style attention, since they feature a fixed-size hidden state (Equation (2)) rather than
maintaining a key–value (KV) cache that grows linearly with the sequence length.


TPS, however, does not explicitly factor in hardware efficiency, where we aim to be in a computebound regime (as opposed to memory-bound) in order to fully utilize on-chip accelerators. To
better characterize hardware efficiency, we would need to consider the arithmetic intensity of token
generation. Recall that arithmetic intensity is defined as FLOPs divided by the number of inputoutput bytes, for a given op. In order to fully utilize both the accelerators and the bandwidth, we
would like the arithmetic intensity to match the ops:byte ratio of the hardware, which in the case
of NVIDIA H100-SXM5, is 295.2 bfloat16 ops per second with respect to the DRAM, and 31.9
bfloat16 ops per second with respect to the SRAM [Fleetwood].


Table 2(a) shows the arithmetic intensity for a single generation in the SSM component of Mamba
(with respect to 2-byte data). We see that it falls far short of a compute-bound regime, and moreover
it is not clear how one can adjust the existing parameters in Mamba to mitigate the lack of hardware
efficiency. We note that this observation applies generally to other sub-quadratic models, such as
causal linear attention.



**Input** **Output** **FLOPs** **Arithmetic**
**Intensity**



**Input** **Output** **FLOPs** **Arithmetic**
**Intensity**



(b) MIMO (2-byte data).



_Ht_ : ( _n, p_ )
_xt_ : ( _p_ )
_at_ : (1)
_bt_ : ( _n_ )
_ct_ : ( _n_ )



5 _pn_
_yt_ : ( _p_ ) 5 _pn_ 2(1 + 2 _n_ + _p_ + _np_ )
_≈_ 2 _._ 5 = Θ(1)


(a) SISO (2-byte data).



_Ht_ : ( _n, p_ )
_xt_ : ( _p, r_ )
_at_ : (1)
_bt_ : ( _n, r_ )
_ct_ : ( _n, r_ )



_yt_ : 4 _nrp_ +
( _p, r_ ) 2 _np_



_p_ (4 _nr_ + 2 _n_ )
2(1 + 2 _nr_ + _pr_ + _np_ )
_≈_ 2 _r_ = Θ( _r_ )

_r_ (Figure 2(b)). Hence, by increasing _r_, arithmetic intensity improves and shifts decode generation
towards a more compute-bound regime. This increase in FLOPs during decode does not compromise
runtime, as the operation is bounded by the I/O of state **H** _t_ _∈_ R _[n][×][p]_ .


Moreover, moving from outer-product-based state update to matrix-product-based coincides exactly
with generalizing from SISO to MIMO SSM, with the rank _r_ being the MIMO rank. Such a generalization recovers a key expressive feature of SSMs in classical literature; indeed, there has been
previous work, namely Smith et al. (2023), that explored MIMO SSM as a drop-in replacement of
attention, albeit not in the context of Mamba and not necessarily with inference in view. We note
that training and prefilling is generally compute bound, resulting in MIMO incurring increased costs
during these stages, while decoding, a memory-bound operation, sees very little increase in latency
when utilizing MIMO over SISO.


Details of the MIMO formulation for Mamba-3 are provided in Appendix D.


3.4 MAMBA-3 ARCHITECTURE


The Mamba-3 block retains the overall layout of its predecessor while introducing several key modifications. Most notably, the SSD layer is replaced with the more expressive trapezoidal SSM defined
in Proposition 4. The extra normalization layer, first introduced between Mamba-1 and Mamba-2 for
training stability, is repositioned to follow the **B** _,_ **C** projection, mirroring the QK-Norm commonly
used in modern Transformers (Henry et al., 2020; Wortsman et al., 2023). Inspired by the findings
of Yu & Erichson (2025), which prove adding channel-specific bias to **B** in a blockwise variant
of Mamba-1 grants universal approximation capabilities, Mamba-3 incorporates a head-specific,
channel-wise bias into both the **B** and **C** components after its normalization. These learnable biases are data-independent parameters that are initialized to all ones and independent across **B** and
**C** (ablations for bias parameterization can be found in Appendix G). Our trapezoidal discretization
complements this bias, empirically eliminating the need for the original short causal convolution and
its accompanying activation function (Section 4.3). Mamba-3 employs the SISO SSM by default,
though we view its MIMO variant as a flexible option that can be toggled depending on inference
requirements. The overall architecture follows the Llama design (Grattafiori et al., 2024), alternating
Mamba-3 and SwiGLU blocks with pre-normalization.


4 EMPIRICAL VALIDATION


We empirically validate our SSM-centric methodological changes through the Mamba-3 model on
a host of synthetic and real world tasks. Section 4.1 compares our SISO-variant of Mamba-3 on
language modeling and retrieval-based tasks, while Section 4.2 demonstrates inference efficiency of
Mamba-3 and MIMO Mamba-3’s benefits over SISO Mamba-3 under fixed inference compute. We
ablate the impact of our new discretization and BC bias on performance and show that complexification of the SSM leads capabilities that prior SSMs such as Mamba-2 lacked in Section 4.3.


4.1 LANGUAGE MODELING


All models are pretrained with 100B tokens of the FineWeb-Edu dataset (Penedo et al., 2024) with
the Llama-3.1 tokenizer (Grattafiori et al., 2024) at a 2K context length with the same standard
training protocol. Training and evaluation details can be found in Appendix E.


Across all four model scales, Mamba-3 outperforms popular baselines at various downstream tasks
(Table 1). We highlight that Mamba-3 does not utilize the short convolution that has been empirically
identified as an important component in many performant linear models (Allen-Zhu, 2025).


4.1.1 RETRIEVAL CAPABILITIES


Beyond standard language modeling, an important measure for linear models is their retrieval ability

- how well they can recall information from earlier in the sequence (Arora et al., 2025a;b). Unlike
attention models, which can freely revisit past context with the growing KV cache, linear models
must compress context into a fixed-size state. This trade-off is reflected in the Transformer baseline’s
substantially stronger retrieval scores. To evaluate Mamba-3 under this lens, Table 2 compares it
against baselines on both real-world and synthetic needle-in-a-haystack (NIAH) tasks (Hsieh et al.,
2024), using our pretrained 1.5B models from Section 4.1. We restrict the task sequence length to
2K tokens to match the training setup and adopt the cloze-style format for our real-world tasks to
mirror the next-token-prediction objective, following Arora et al. (2025b; 2024).


Mamba-3 is competitive on real-world associative recall and question-answering but struggles when
extracting information from semi-structured or unstructured data. On synthetic NIAH tasks, how

7

Table 1: Downstream language modeling evaluations on models trained with 100B FineWeb-Edu
tokens. Best results for each size are **bolded**, and second best are underlined. All models are trained
with the same procedure. Mamba-3 outperforms Mamba-2 and others at every model scale.


**Model** FW-Edu LAMB. LAMB. HellaS. PIQA Arc-E Arc-C WinoGr. OBQA Average
ppl _↓_ ppl _↓_ acc _↑_ acc ~~n~~ _↑_ acc _↑_ acc _↑_ acc ~~n~~ _↑_ acc _↑_ acc _↑_ acc _↑_


Transformer-180M 16 _._ 89 45 _._ 0 32 _._ 5 39 _._ 0 **67** _**.**_ **1** 59 _._ 8 27 _._ 9 51 _._ 2 21 _._ 8 42 _._ 8
Gated DeltaNet-180M 16 _._ 61 **35** _**.**_ **9** **33** _**.**_ **7** 40 _._ 2 66 _._ 8 59 _._ 6 **28** _**.**_ **5** 51 _._ 2 21 _._ 6 43 _._ 1
Mamba-2-180M 16 _._ 76 41 _._ 8 30 _._ 9 40 _._ 1 66 _._ 8 60 _._ 1 27 _._ 3 **52** _**.**_ **0** **23** _**.**_ **2** 42 _._ 9
**Mamba-3-180M** (SISO) **16** _**.**_ **59** 37 _._ 7 32 _._ 5 **40** _**.**_ **8** 66 _._ 1 **61** _**.**_ **5** 27 _._ 9 **52** _**.**_ **0** 22 _._ 8 **43** _**.**_ **4**


Transformer-440M 13 _._ 03 21 _._ 2 **41** _**.**_ **7** 50 _._ 5 69 _._ 9 67 _._ 6 34 _._ 6 **56** _**.**_ **7** **26** _**.**_ **0** 49 _._ 6
Gated DeltaNet-440M 13 _._ 12 **19** _**.**_ **0** 40 _._ 4 50 _._ 5 70 _._ 5 67 _._ 5 34 _._ 0 55 _._ 3 25 _._ 8 49 _._ 1
Mamba-2-440M 13 _._ 00 19 _._ 6 40 _._ 8 **51** _**.**_ **7** 70 _._ 6 68 _._ 8 **35** _**.**_ **0** 54 _._ 1 **26** _**.**_ **0** 49 _._ 6
**Mamba-3-440M** (SISO) **12** _**.**_ **87** 19 _._ 6 40 _._ 2 **51** _**.**_ **7** **71** _**.**_ **9** **68** _**.**_ **9** 34 _._ 4 55 _._ 8 **26** _**.**_ **0** **49** _**.**_ **8**


Transformer-880M 11 _._ 42 15 _._ 0 44 _._ 7 57 _._ 2 72 _._ 6 71 _._ 6 39 _._ 2 57 _._ 7 26 _._ 8 52 _._ 8
Gated DeltaNet-880M 11 _._ 39 **12** _**.**_ **7** 47 _._ 1 57 _._ 5 72 _._ 6 72 _._ 5 38 _._ 8 57 _._ 9 **30** _**.**_ **6** 53 _._ 9
Mamba-2-880M 11 _._ 35 13 _._ 8 45 _._ 0 58 _._ 1 72 _._ 5 72 _._ 3 38 _._ 7 56 _._ 8 30 _._ 2 53 _._ 4
**Mamba-3-880M** (SISO) **11** _**.**_ **23** 12 _._ 9 **47** _**.**_ **2** **58** _**.**_ **8** **73** _**.**_ **6** **72** _**.**_ **7** **40** _**.**_ **2** **58** _**.**_ **4** 30 _._ 0 **54** _**.**_ **4**


Transformer-1.5B 10 _._ 51 11 _._ 1 **50** _**.**_ **3** 60 _._ 6 73 _._ 8 74 _._ 0 40 _._ 4 58 _._ 7 29 _._ 6 55 _._ 4
Gated DeltaNet-1.5B 10 _._ 51 **10** _**.**_ **8** 49 _._ 9 60 _._ 5 **74** _**.**_ **3** 73 _._ 3 40 _._ 4 **61** _**.**_ **5** 30 _._ 4 55 _._ 7
Mamba-2-1.5B 10 _._ 47 12 _._ 0 47 _._ 8 61 _._ 4 73 _._ 6 75 _._ 3 41 _._ 8 57 _._ 5 **32** _**.**_ **6** 55 _._ 7
**Mamba-3-1.5B** (SISO) **10** _**.**_ **35** 10 _._ 9 49 _._ 4 **61** _**.**_ **9** 73 _._ 6 **75** _**.**_ **9** **42** _**.**_ **7** 59 _._ 4 32 _._ 0 **56** _**.**_ **4**


Table 2: Retrieval capabilities measured by a mixture of real-world and synthetic retrieval tasks. Real-world retrieval tasks utilize cloze variants of the original datasets and are truncated to 2K length. Mamba-3 demonstrates
strong associative recall and question-answering but suffers with information extraction of semi-structured and
unstructured data. Mamba-3 has strong needle-in-a-haystack (NIAH) accuracy and generalizes outside its
trained context.


**Model (1.5B)** SWDE SQUAD FDA TQA NQ Drop NIAH-Single-1 NIAH-Single-2 NIAH-Single-3


Context Length 2048 1024 2048 4096 1024 2048 4096 1024 2048 4096


Transformer 48 _._ 9 46 _._ 6 58 _._ 4 67 _._ 5 31 _._ 7 26 _._ 4 100 _._ 0 100 _._ 0 0 _._ 0 92 _._ 2 100 _._ 0 0 _._ 0 98 _._ 6 99 _._ 4 0 _._ 0


Gated DeltaNet **32** _**.**_ **7** 40 _._ 0 **28** _**.**_ **3** 63 _._ 5 25 _._ 7 24 _._ 5 **100** _**.**_ **0** **100** _**.**_ **0** **99** _**.**_ **8** **100** _**.**_ **0** 93 _._ 8 49 _._ 8 83 _._ 8 68 _._ 4 **34** _**.**_ **2**
Mamba-2 30 _._ 7 39 _._ 1 23 _._ 7 64 _._ 3 25 _._ 1 **28** _**.**_ **5** **100** _**.**_ **0** 99 _._ 6 62 _._ 0 **100** _**.**_ **0** 53 _._ 8 11 _._ 8 **95** _**.**_ **8** **87** _**.**_ **4** 13 _._ 4
**Mamba-3** (SISO) 28 _._ 5 **40** _**.**_ **1** 23 _._ 4 **64** _**.**_ **5** **26** _**.**_ **5** 27 _._ 4 **100** _**.**_ **0** **100** _**.**_ **0** 88 _._ 2 **100** _**.**_ **0** **95** _**.**_ **4** **50** _**.**_ **6** 92 _._ 4 81 _._ 4 **34** _**.**_ **2**


ever, Mamba-3 surpasses or matches baselines on most cases and notably demonstrates markedly
better out-of-distribution retrieval abilities than its Mamba-2 predecessor.


4.2 INFERENCE EFFICIENCY


In this section, we investigate our methodological changes in the context of inference performance.
We first present our inference benchmark in Section 4.2.1; we then establish a framework for comparing the inference performance in Section 4.2.2. Finally, we focus on the effectiveness of MIMO
in Section 4.2.3.


4.2.1 FAST MAMBA-3 KERNELS


We complement Mamba-3’s methodological advances with optimized kernels that deliver fast inference in practical settings. Specifically, we implement a new series of inference kernels for Mamba3—using Triton for the forward (prefill) path and CuTe-DSL for decode—and compare their pertoken decode latency against the released Triton kernels for Mamba-2 and Gated DeltaNet (GDN) [1]
in Table 3. The evaluation uses the setting: a decode step at batch size 128 on a single H100 for
1.5B-parameter models with model dimension 2048, state dimension _∈{_ 64 _,_ 128 _}_ in both FP32 and
BF16 datatypes. Across all configurations, SISO achieves the lowest latency amongst baselines,
while MIMO incurs only a minor overhead relative to SISO. This indicates that our CuTe-DSL decode implementation is competitive and that the additional components of Mamba-3 (trapezoidal
update, complex-valued state, and MIMO projections) are lightweight. This supports our overall
inference-first perspective: the Mamba-3 admits **simple,** **low-latency** **implementation** while providing strong empirical performance. A thorough analysis, including prefill and prefill with decode
results are provided in Appendix H.


8


![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/13549_Mamba_3_Improved_Sequenc_extracted/images/13549_Mamba_3_Improved_Sequenc.pdf-8-0.png)

![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/13549_Mamba_3_Improved_Sequenc_extracted/images/13549_Mamba_3_Improved_Sequenc.pdf-8-1.png)

10 [5]

Relative Total State Size



**Model** **FP32** **BF16**


_d_ state = 64 _d_ state = 128 _d_ state = 64 _d_ state = 128


Mamba-2 0 _._ 295 0 _._ 409 0 _._ 127 0 _._ 203
Gated DeltaNet 0 _._ 344 0 _._ 423 0 _._ 176 0 _._ 257
Mamba-3 (SISO) 0 _._ 261 0 _._ 356 0 _._ 106 0 _._ 152
Mamba-3 (MIMO) 0 _._ 285 0 _._ 392 0 _._ 136 0 _._ 185



4.2.2 PARETO FRONTIER FOR INFERENCE EFFICIENCY


For Mamba and many variants of sub-quadratic models, the generation of tokens during decoding is
heavily dominated by memory I/O due to the low arithmetic intensity of computing the recurrent update (c.f. Section 3.3). Furthermore, among the data being transferred, the latent state **Ht** dominates
in terms of size. Indeed, from Table 3, we see that the runtime scales with _d_ state, which configures
the size of the hidden state.


As _d_ state dominates the decode runtime for the subquadratic models considered in this paper, we
opt to use it as a proxy for inference speed. By plotting the validation perplexity (itself a proxy
for model performance) as a function of _d_ state, we aim to formulate a holistic picture about how the
subquadratic models can trade off performance with inference speed.


Figure 3 shows such a Pareto front for the Mamba variants models considered in this paper. For each
data point, we train a 440M parameter model to 2 _×_ Chinchilla optimal tokens on the Fineweb-Edu
dataset, where the model is configured with a _d_ state of _{_ 16 _,_ 32 _,_ 64 _,_ 128 _}_ . As expected, we observe
an inverse correlation between validation loss and _d_ state; moreover, we noticed a general downward
shift on the Pareto front moving from Mamba-2 to Mamba-3. A further downward shift is observed
when moving from the SISO variant of Mamba-3 to the MIMO variant of Mamba-3 (where we set
the Mimo rank _r_ = 4 and decrease our MLP inner dimension to parameter match the SISO variants).
We expand the comparison to include the Gated DeltaNet baseline in Figure 7. The results highlight
both the expressivity gain coming our methodology change as well as the effectiveness of the MIMO
mechanism in improving decoding efficiency.


4.2.3 MIMO ENHANCES INFERENCE EFFICIENCY


MIMO, with its higher arithmetic intensity, increases the decoding FLOPs without significantly
increasing decode runtime (Table 3) [2] The implication is that any performance gain from MIMO
translates into efficiency gain in decoding: a conclusion supported by the downward shift of the
MIMO pareto curve we observed in Section 4.2.2.


We aim to further verify the gain from MIMO by investigating its language-modeling capabilities.
To that end, we train a 440M and 820M parameter MIMO models with MIMO rank _r_ = 4 on 100B
tokens on Fineweb-Edu (i.e., same setting as the 440M parameter run in Section 4.1; we are currently
training the 1.5B model). To ensure the total parameter count equals SISO, we decrease the inner
dimension of the MLP layers to compensate for the increase due to the MIMO projections.


On both validation perplexity and our suite of language evaluation tasks (Table 6), we see significant
gain when moving from SISO to MIMO. Namely, we attain a perplexity gain of 0 _._ 16 on the 100B
tokens run, and Figure 3 illustrates the downward shift in our validation loss. On the language
evaluation front, we see significant gain on most tasks when compared to SISO, resulting in an
overall gain of 1.2 point over SISO. This strongly supports MIMO as a SSM-centric technique to
improve model quality without compromising decoding speed.


1Details on each kernel DSL and the exact kernel fusion structure is provided in Appendix H.
2The kernel for MIMO Mamba-3 in fact fuses the MIMO projection, and so the reported wall clock time is
actually an overestimate for the pure SSM update.


9



15.2


15.0


14.8


14.6



Relative Total State Size vs Pretraining Perplexity





Table 3: Latency (in milliseconds) comparison across models, precision, and _d_ state values. Both Mamba-3 SISO and MIMO are
faster than the Mamba-2 and Gated DeltaNet
at the commonly used bf16, _d_ state = 128 setting.



Figure 3: Exploration of state size (inference
speed proxy) versus pretraining perplexity (performance proxy) across different Mamba variants.
Mamba-3 MIMO drives the-Pareto frontier without increasing state size.




Table 4: **Left** : Ablations on core modeling components of Mamba-3, results on test split of dataset. A
combination of our BC bias and trapezoidal discretization makes the convolution optional. **Right** : Formal
language evaluation (scaled accuracy, %). Higher is better. Models are trained on short sequences and evaluated
on longer lengths to test length generalization. For Gated DeltaNet we report the variant with eigenvalue range

[ _−_ 1 _,_ 1].



4.3 SSM-CENTRIC METHODOLOGICAL ABLATIONS


Table 4a ablates the changes made to the core SSM component, mainly the introduction of BC bias
and trapezoidal discretization. We report the pretraining test perplexity on models at the 440M scale,
trained for Chinchilla optimal tokens. We find that the bias and trapezoidal SSM synergize well and
make the short convolution utilized by many current linear models redundant.


We empirically demonstrate that data-dependent RoPE in Mamba-3 enables state tracking. Following Grazzi et al. (2025), we evaluate on tasks from the Chomsky hierarchy—Parity, Modular Arithmetic (without brackets), and Modular Arithmetic (with brackets)—and report scaled accuracies in
Table 4b. Mamba-3 solves Parity and Modular Arithmetic (without brackets), and nearly closes the
accuracy gap on Modular Arithmetic (with brackets). In contrast, Mamba-3 without RoPE, Mamba3 with standard RoPE (Su et al., 2023), and Mamba-2 fail to learn these tasks. We use the statetracking–enabled _Gated_ _DeltaNet_ variant of and observe that _Mamba-3_ is competitive—matching
parity and approaching its performance on both modular-arithmetic tasks. Experimental settings are
covered in Appendix E.


5 CONCLUSION AND FUTURE WORK


We introduce Mamba-3, an SSM model with three axes of improvement rooted in SSM principles: (i) _improved_ _quality_, via trapezoidal discretization; (ii) _new_ _capabilities_, through complex
SSMs that recover state-tracking; and (iii) _higher_ _inference_ _efficiency_, with a MIMO formulation
that raises arithmetic intensity. Mamba-3 delivers strong language modeling results and establishes
a new Pareto frontier on the performance-efficiency axes with respect to strong baseline models. A
limitation remains in retrieval, where fixed-state architectures lags attention-based models. We see
**hybrid Mamba-3 architectures** that integrate retrieval mechanisms as a promising path, alongside
broader application of our design principles to linear-time sequence models.


10



**Model Variant** (SISO) ppl _↓_


Mamba-3 _−_ bias _−_ trap 16 _._ 68
Mamba-3 _−_ bias 16 _._ 49
Mamba-3 **15** _**.**_ **72**
Mamba-3 + conv 15 _._ 85

(a) Component ablation (350M).



Arith. w/o _↑_ Arith. w/ _↑_
**Model** Parity _↑_
brackets brackets


Mamba-3 100 _._ 00 98 _._ 51 87 _._ 75
Mamba-3 (w/o RoPE) 2 _._ 27 1 _._ 49 0 _._ 72
Mamba-3 (w/ Std. RoPE) 1 _._ 56 20 _._ 70 2 _._ 62
Mamba-2 0 _._ 90 47 _._ 81 0 _._ 88
Gated DeltaNet [-1,1] 100 _._ 00 99 _._ 25 93 _._ 50

(b) Performance comparison on formal language tasks. Results show that unlike Mamba-2, Mamba-3 features state
tracking ability stemming from data-dependent RoPE embeddings. We used Mamba-3 (SISO) for these ablations.



REFERENCES


Zeyuan Allen-Zhu. Physics of Language Models: Part 4.1, Architecture Design and the Magic
of Canon Layers. _SSRN_ _Electronic_ _Journal_, May 2025. [https://ssrn.com/abstract=](https://ssrn.com/abstract=5240330)
[5240330.](https://ssrn.com/abstract=5240330)


Aryaman Arora, Neil Rathi, Nikil Roashan Selvam, R´obert Csord´as, Dan Jurafsky, and Christopher
Potts. Mechanistic evaluation of transformers and state space models, 2025a. URL [https:](https://arxiv.org/abs/2505.15105)
[//arxiv.org/abs/2505.15105.](https://arxiv.org/abs/2505.15105)


Simran Arora, Aman Timalsina, Aaryan Singhal, Benjamin Spector, Sabri Eyuboglu, Xinyi Zhao,
Ashish Rao, Atri Rudra, and Christopher R´e. Just read twice: closing the recall gap for recurrent
language models, 2024. [URL https://arxiv.org/abs/2407.05483.](https://arxiv.org/abs/2407.05483)


Simran Arora, Sabri Eyuboglu, Michael Zhang, Aman Timalsina, Silas Alberti, Dylan Zinsley,
James Zou, Atri Rudra, and Christopher R´e. Simple linear attention language models balance
the recall-throughput tradeoff, 2025b. [URL https://arxiv.org/abs/2402.18668.](https://arxiv.org/abs/2402.18668)


Aviv Bick, Kevin Y. Li, Eric P. Xing, J. Zico Kolter, and Albert Gu. Transformers to ssms: Distilling quadratic knowledge to subquadratic models, 2025a. [URL https://arxiv.org/abs/](https://arxiv.org/abs/2408.10189)
[2408.10189.](https://arxiv.org/abs/2408.10189)


Aviv Bick, Eric Xing, and Albert Gu. Understanding the skill gap in recurrent language models:
The role of the gather-and-aggregate mechanism, 2025b. [URL https://arxiv.org/abs/](https://arxiv.org/abs/2504.18574)
[2504.18574.](https://arxiv.org/abs/2504.18574)


Yonatan Bisk, Rowan Zellers, Ronan Le Bras, Jianfeng Gao, and Yejin Choi. Piqa: Reasoning about
physical commonsense in natural language, 2019. [URL https://arxiv.org/abs/1911.](https://arxiv.org/abs/1911.11641)
[11641.](https://arxiv.org/abs/1911.11641)


Krzysztof Choromanski, Valerii Likhosherstov, David Dohan, Xingyou Song, Andreea Gane, Tamas
Sarlos, Peter Hawkins, Jared Davis, Afroz Mohiuddin, Lukasz Kaiser, David Belanger, Lucy
Colwell, and Adrian Weller. Rethinking attention with performers, 2022. URL [https://](https://arxiv.org/abs/2009.14794)
[arxiv.org/abs/2009.14794.](https://arxiv.org/abs/2009.14794)


Peter Clark, Isaac Cowhey, Oren Etzioni, Tushar Khot, Ashish Sabharwal, Carissa Schoenick, and
Oyvind Tafjord. Think you have solved question answering? try arc, the ai2 reasoning challenge,
2018. [URL https://arxiv.org/abs/1803.05457.](https://arxiv.org/abs/1803.05457)


Tri Dao and Albert Gu. Transformers are ssms: Generalized models and efficient algorithms through
structured state space duality, 2024. [URL https://arxiv.org/abs/2405.21060.](https://arxiv.org/abs/2405.21060)


Dheeru Dua, Yizhong Wang, Pradeep Dasigi, Gabriel Stanovsky, Sameer Singh, and Matt Gardner.
Drop: A reading comprehension benchmark requiring discrete reasoning over paragraphs, 2019.
[URL https://arxiv.org/abs/1903.00161.](https://arxiv.org/abs/1903.00161)


Christopher Fleetwood. Domain specific architectures for ai inference. URL [https://](https://fleetwood.dev/posts/domain-specific-architectures)
[fleetwood.dev/posts/domain-specific-architectures.](https://fleetwood.dev/posts/domain-specific-architectures)


Leo Gao, Jonathan Tow, Baber Abbasi, Stella Biderman, Sid Black, Anthony DiPofi, Charles Foster, Laurence Golding, Jeffrey Hsu, Alain Le Noac’h, Haonan Li, Kyle McDonell, Niklas Muennighoff, Chris Ociepa, Jason Phang, Laria Reynolds, Hailey Schoelkopf, Aviya Skowron, Lintang
Sutawika, Eric Tang, Anish Thite, Ben Wang, Kevin Wang, and Andy Zou. The language model
evaluation harness, 07 2024. [URL https://zenodo.org/records/12608602.](https://zenodo.org/records/12608602)


Madan Gopal. _Modern control system theory_ . New Age International, 1993.


Aaron Grattafiori, Abhimanyu Dubey, Abhinav Jauhri, Abhinav Pandey, Abhishek Kadian, Ahmad
Al-Dahle, Aiesha Letman, Akhil Mathur, Alan Schelten, Alex Vaughan, Amy Yang, Angela Fan,
Anirudh Goyal, Anthony Hartshorn, Aobo Yang, Archi Mitra, Archie Sravankumar, Artem Korenev, Arthur Hinsvark, Arun Rao, Aston Zhang, and et. al. The llama 3 herd of models, 2024.
[URL https://arxiv.org/abs/2407.21783.](https://arxiv.org/abs/2407.21783)


11


Riccardo Grazzi, Julien Siems, Simon Schrodi, Thomas Brox, and Frank Hutter. Is mamba capable
of in-context learning?, 2024. [URL https://arxiv.org/abs/2402.03170.](https://arxiv.org/abs/2402.03170)


Riccardo Grazzi, Julien Siems, Arber Zela, J¨org K. H. Franke, Frank Hutter, and Massimiliano
[Pontil. Unlocking state-tracking in linear rnns through negative eigenvalues, 2025. URL https:](https://arxiv.org/abs/2411.12537)
[//arxiv.org/abs/2411.12537.](https://arxiv.org/abs/2411.12537)


Albert Gu and Tri Dao. Mamba: Linear-time sequence modeling with selective state spaces, 2024.
[URL https://arxiv.org/abs/2312.00752.](https://arxiv.org/abs/2312.00752)


Albert Gu, Karan Goel, and Christopher R´e. Efficiently modeling long sequences with structured
state spaces, 2022a. [URL https://arxiv.org/abs/2111.00396.](https://arxiv.org/abs/2111.00396)


Albert Gu, Ankit Gupta, Karan Goel, and Christopher R´e. On the parameterization and initialization
of diagonal state space models. _arXiv_ _preprint_ _arXiv:2206.11893_, 2022b. URL [https://](https://arxiv.org/abs/2206.11893)
[arxiv.org/abs/2206.11893.](https://arxiv.org/abs/2206.11893)


Ankit Gupta, Albert Gu, and Jonathan Berant. Diagonal state spaces are as effective as structured
state spaces, 2022. [URL https://arxiv.org/abs/2203.14343.](https://arxiv.org/abs/2203.14343)


Alex Henry, Prudhvi Raj Dachapally, Shubham Pawar, and Yuxuan Chen. Query-key normalization
for transformers, 2020. [URL https://arxiv.org/abs/2010.04245.](https://arxiv.org/abs/2010.04245)


Cheng-Ping Hsieh, Simeng Sun, Samuel Kriman, Shantanu Acharya, Dima Rekesh, Fei Jia, Yang
Zhang, and Boris Ginsburg. Ruler: What’s the real context size of your long-context language
models?, 2024. [URL https://arxiv.org/abs/2404.06654.](https://arxiv.org/abs/2404.06654)


Samy Jelassi, David Brandfonbrener, Sham M. Kakade, and Eran Malach. Repeat after me: Transformers are better than state space models at copying, 2024. URL [https://arxiv.org/](https://arxiv.org/abs/2402.01032)
[abs/2402.01032.](https://arxiv.org/abs/2402.01032)


Mandar Joshi, Eunsol Choi, Daniel S. Weld, and Luke Zettlemoyer. Triviaqa: A large scale distantly
supervised challenge dataset for reading comprehension, 2017. [URL https://arxiv.org/](https://arxiv.org/abs/1705.03551)
[abs/1705.03551.](https://arxiv.org/abs/1705.03551)


Rudolph Emil Kalman. A new approach to linear filtering and prediction problems. 1960.


Angelos Katharopoulos, Apoorv Vyas, Nikolaos Pappas, and Franc¸ois Fleuret. Transformers are
rnns: Fast autoregressive transformers with linear attention, 2020. URL [https://arxiv.](https://arxiv.org/abs/2006.16236)
[org/abs/2006.16236.](https://arxiv.org/abs/2006.16236)


Tom Kwiatkowski, Jennimaria Palomaki, Olivia Redfield, Michael Collins, Ankur Parikh, Chris
Alberti, Danielle Epstein, Illia Polosukhin, Jacob Devlin, Kenton Lee, Kristina Toutanova, Llion
Jones, Matthew Kelcey, Ming-Wei Chang, Andrew M. Dai, Jakob Uszkoreit, Quoc Le, and Slav
Petrov. Natural questions: A benchmark for question answering research. _Transactions_ _of_ _the_
_Association_ _for_ _Computational_ _Linguistics_, 7:452–466, 2019. doi: 10.1162/tacl ~~a~~ ~~0~~ 0276. URL
[https://aclanthology.org/Q19-1026/.](https://aclanthology.org/Q19-1026/)


Woosuk Kwon, Zhuohan Li, Siyuan Zhuang, Ying Sheng, Lianmin Zheng, Cody Hao Yu, Joseph E.
Gonzalez, Hao Zhang, and Ion Stoica. Efficient memory management for large language model
serving with pagedattention, 2023. [URL https://arxiv.org/abs/2309.06180.](https://arxiv.org/abs/2309.06180)


Baolin Li, Yankai Jiang, Vijay Gadepally, and Devesh Tiwari. Llm inference serving: Survey of
recent advances and opportunities, 2024. [URL https://arxiv.org/abs/2407.12391.](https://arxiv.org/abs/2407.12391)


William Merrill, Jackson Petty, and Ashish Sabharwal. The illusion of state in state-space models,
2025. [URL https://arxiv.org/abs/2404.08819.](https://arxiv.org/abs/2404.08819)


Todor Mihaylov, Peter Clark, Tushar Khot, and Ashish Sabharwal. Can a suit of armor conduct
electricity? a new dataset for open book question answering, 2018. URL [https://arxiv.](https://arxiv.org/abs/1809.02789)
[org/abs/1809.02789.](https://arxiv.org/abs/1809.02789)


12



Team OLMo, Pete Walsh, Luca Soldaini, Dirk Groeneveld, Kyle Lo, Shane Arora, Akshita Bhagia,
Yuling Gu, Shengyi Huang, Matt Jordan, Nathan Lambert, Dustin Schwenk, Oyvind Tafjord,
Taira Anderson, David Atkinson, Faeze Brahman, Christopher Clark, Pradeep Dasigi, Nouha
Dziri, Michal Guerquin, and et. al. 2 olmo 2 furious, 2025. URL [https://arxiv.org/](https://arxiv.org/abs/2501.00656)
[abs/2501.00656.](https://arxiv.org/abs/2501.00656)


Antonio Orvieto, Samuel L Smith, Albert Gu, Anushan Fernando, Caglar Gulcehre, Razvan Pascanu, and Soham De. Resurrecting recurrent neural networks for long sequences, 2023. URL
[https://arxiv.org/abs/2303.06349.](https://arxiv.org/abs/2303.06349)


Daniele Paliotta, Junxiong Wang, Matteo Pagliardini, Kevin Y. Li, Aviv Bick, J. Zico Kolter, Albert
Gu, Franc¸ois Fleuret, and Tri Dao. Thinking slow, fast: Scaling inference compute with distilled
reasoners, 2025. [URL https://arxiv.org/abs/2502.20339.](https://arxiv.org/abs/2502.20339)


Denis Paperno, Germ´an Kruszewski, Angeliki Lazaridou, Quan Ngoc Pham, Raffaella Bernardi,
Sandro Pezzelle, Marco Baroni, Gemma Boleda, and Raquel Fern´andez. The lambada dataset:
Word prediction requiring a broad discourse context, 2016. URL [https://arxiv.org/](https://arxiv.org/abs/1606.06031)
[abs/1606.06031.](https://arxiv.org/abs/1606.06031)


Jongho Park, Jaeseung Park, Zheyang Xiong, Nayoung Lee, Jaewoong Cho, Samet Oymak, Kangwook Lee, and Dimitris Papailiopoulos. Can mamba learn how to learn? a comparative study on
in-context learning tasks, 2024. [URL https://arxiv.org/abs/2402.04248.](https://arxiv.org/abs/2402.04248)


Guilherme Penedo, Hynek Kydl´ıˇcek, Loubna Ben allal, Anton Lozhkov, Margaret Mitchell, Colin
Raffel, Leandro Von Werra, and Thomas Wolf. The fineweb datasets: Decanting the web for the
finest text data at scale, 2024. [URL https://arxiv.org/abs/2406.17557.](https://arxiv.org/abs/2406.17557)


Bo Peng, Ruichong Zhang, Daniel Goldstein, Eric Alcaide, Xingjian Du, Haowen Hou, Jiaju Lin,
Jiaxing Liu, Janna Lu, William Merrill, Guangyu Song, Kaifeng Tan, Saiteja Utpala, Nathan
Wilce, Johan S. Wind, Tianyi Wu, Daniel Wuttke, and Christian Zhou-Zheng. Rwkv-7 ”goose”
with expressive dynamic state evolution, 2025. URL [https://arxiv.org/abs/2503.](https://arxiv.org/abs/2503.14456)
[14456.](https://arxiv.org/abs/2503.14456)


Pranav Rajpurkar, Jian Zhang, and Percy Liang. Know what you don’t know: Unanswerable questions for squad. In _ACL 2018_, 2018.


Yuval Ran-Milo, Eden Lumbroso, Edo Cohen-Karlik, Raja Giryes, Amir Globerson, and Nadav
Cohen. Provable benefits of complex parameterizations for structured state space models, 2024.
[URL https://arxiv.org/abs/2410.14067.](https://arxiv.org/abs/2410.14067)


Keisuke Sakaguchi, Ronan Le Bras, Chandra Bhagavatula, and Yejin Choi. Winogrande: An adversarial winograd schema challenge at scale, 2019. [URL https://arxiv.org/abs/1907.](https://arxiv.org/abs/1907.10641)
[10641.](https://arxiv.org/abs/1907.10641)


Yash Sarrof, Yana Veitsman, and Michael Hahn. The expressive capacity of state space models: A
formal language perspective, 2024. [URL https://arxiv.org/abs/2405.17394.](https://arxiv.org/abs/2405.17394)


Imanol Schlag, Kazuki Irie, and J¨urgen Schmidhuber. Linear transformers are secretly fast weight
programmers, 2021. [URL https://arxiv.org/abs/2102.11174.](https://arxiv.org/abs/2102.11174)


Julien Siems, Timur Carstensen, Arber Zela, Frank Hutter, Massimiliano Pontil, and Riccardo
Grazzi. Deltaproduct: Improving state-tracking in linear rnns via householder products, 2025.
[URL https://arxiv.org/abs/2502.10297.](https://arxiv.org/abs/2502.10297)


Jimmy T. H. Smith, Andrew Warrington, and Scott W. Linderman. Simplified state space layers for
sequence modeling, 2023. [URL https://arxiv.org/abs/2208.04933.](https://arxiv.org/abs/2208.04933)


Charlie Snell, Jaehoon Lee, Kelvin Xu, and Aviral Kumar. Scaling llm test-time compute optimally
can be more effective than scaling model parameters, 2024. URL [https://arxiv.org/](https://arxiv.org/abs/2408.03314)
[abs/2408.03314.](https://arxiv.org/abs/2408.03314)


Jianlin Su, Yu Lu, Shengfeng Pan, Ahmed Murtadha, Bo Wen, and Yunfeng Liu. Roformer: En[hanced transformer with rotary position embedding, 2023. URL https://arxiv.org/abs/](https://arxiv.org/abs/2104.09864)
[2104.09864.](https://arxiv.org/abs/2104.09864)


13

Yutao Sun, Li Dong, Shaohan Huang, Shuming Ma, Yuqing Xia, Jilong Xue, Jianyong Wang, and
Furu Wei. Retentive network: A successor to transformer for large language models, 2023. URL
[https://arxiv.org/abs/2307.08621.](https://arxiv.org/abs/2307.08621)


Endre S¨uli and David F. Mayers. _An_ _Introduction_ _to_ _Numerical_ _Analysis_ . Cambridge University
Press, 2003.


Gemma Team, Aishwarya Kamath, Johan Ferret, Shreya Pathak, Nino Vieillard, Ramona Merhej,
Sarah Perrin, Tatiana Matejovicova, Alexandre Ram´e, Morgane Rivi`ere, Louis Rouillard, Thomas
Mesnard, Geoffrey Cideron, Jean bastien Grill, Sabela Ramos, Edouard Yvinec, Michelle Casbon,
Etienne Pot, Ivo Penchev, Ga¨el Liu, and et. al. Gemma 3 technical report, 2025. [URL https:](https://arxiv.org/abs/2503.19786)
[//arxiv.org/abs/2503.19786.](https://arxiv.org/abs/2503.19786)


M. Tenenbaum and H. Pollard. _Ordinary Differential Equations:_ _An Elementary Textbook for Stu-_
_dents of Mathematics, Engineering, and the Sciences_ . Dover Books on Mathematics. Dover Publications, 1985. ISBN 9780486649405. [URL https://books.google.com/books?id=](https://books.google.com/books?id=iU4zDAAAQBAJ)
[iU4zDAAAQBAJ.](https://books.google.com/books?id=iU4zDAAAQBAJ)


Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N Gomez,
Łukasz Kaiser, and Illia Polosukhin. Attention is all you need. In _Advances in neural information_
_processing systems_, pp. 5998–6008, 2017. [URL http://arxiv.org/abs/1706.03762.](http://arxiv.org/abs/1706.03762)


Johannes von Oswald, Nino Scherrer, Seijin Kobayashi, Luca Versari, Songlin Yang, Maximilian Schlegel, Kaitlin Maile, Yanick Schimpf, Oliver Sieberling, Alexander Meulemans, Rif A.
Saurous, Guillaume Lajoie, Charlotte Frenkel, Razvan Pascanu, Blaise Ag¨uera y Arcas, and Jo˜ao
Sacramento. Mesanet: Sequence modeling by locally optimal test-time training, 2025. URL
[https://arxiv.org/abs/2506.05233.](https://arxiv.org/abs/2506.05233)


Mitchell Wortsman, Peter J. Liu, Lechao Xiao, Katie Everett, Alex Alemi, Ben Adlam, John D. CoReyes, Izzeddin Gur, Abhishek Kumar, Roman Novak, Jeffrey Pennington, Jascha Sohl-dickstein,
Kelvin Xu, Jaehoon Lee, Justin Gilmer, and Simon Kornblith. Small-scale proxies for large-scale
transformer training instabilities, 2023. [URL https://arxiv.org/abs/2309.14322.](https://arxiv.org/abs/2309.14322)


Yangzhen Wu, Zhiqing Sun, Shanda Li, Sean Welleck, and Yiming Yang. Inference scaling laws:
An empirical analysis of compute-optimal inference for problem-solving with language models,
2025. [URL https://arxiv.org/abs/2408.00724.](https://arxiv.org/abs/2408.00724)


Songlin Yang, Jan Kautz, and Ali Hatamizadeh. Gated delta networks: Improving mamba2 with
delta rule, 2025a. [URL https://arxiv.org/abs/2412.06464.](https://arxiv.org/abs/2412.06464)


Songlin Yang, Bailin Wang, Yu Zhang, Yikang Shen, and Yoon Kim. Parallelizing linear transformers with the delta rule over sequence length, 2025b. [URL https://arxiv.org/abs/](https://arxiv.org/abs/2406.06484)
[2406.06484.](https://arxiv.org/abs/2406.06484)


Annan Yu and N. Benjamin Erichson. Block-biased mamba for long-range sequence processing,
2025. [URL https://arxiv.org/abs/2505.09022.](https://arxiv.org/abs/2505.09022)


Rowan Zellers, Ari Holtzman, Yonatan Bisk, Ali Farhadi, and Yejin Choi. Hellaswag: Can a machine really finish your sentence?, 2019. [URL https://arxiv.org/abs/1905.07830.](https://arxiv.org/abs/1905.07830)


14

**LLM Usage.** We utilized Large Language Models to polish the writing in our submission as well as
generate latex code for formatting tables and figures.

A RELATED WORK


**Linear-time sequence mixers.** State-space models (SSMs) provide linear-time sequence mixing
through explicit dynamical states and efficient scan/convolution implementations, offering significant computational advantages over quadratic-time attention mechanisms (Gu et al., 2022a; Smith
et al., 2023; Gupta et al., 2022). Mamba-1 (Gu & Dao, 2024) introduced input-dependent selectivity
to SSMs, while Mamba-2 (Dao & Gu, 2024) formalized the connection between SSMs and attention
via structured state-space duality (SSD) (Katharopoulos et al., 2020; Choromanski et al., 2022). Despite matching transformers on standard language understanding benchmarks, these recurrent models exhibit limitations on tasks requiring precise algorithmic reasoning. Recent evaluations identified
gaps in capabilities such as associative retrieval (Bick et al., 2025b; Arora et al., 2025a), exact copying (Jelassi et al., 2024), and in-context learning (Park et al., 2024; Grazzi et al., 2024). To address
these limitations, DeltaNet enhances linear attention by replacing additive updates with delta-rule
recurrence (Schlag et al., 2021), with recent work developing hardware-efficient, sequence-parallel
training algorithms for this architecture (Yang et al., 2025b). This has catalyzed a broader effort
to improve the algorithmic capabilities of linear-time models through architectural innovations including gating mechanisms, improved state transition dynamics, and hybrid approaches (Peng et al.,
2025; Siems et al., 2025; Yang et al., 2025a; Paliotta et al., 2025; Bick et al., 2025a).


**Expressivity** **and** **state** **tracking** **in** **recurrent** **mixers.** Recent work characterizes the types of
state that recurrent, constant-memory mixers can maintain, revealing algorithmic deficiencies in
previous SSM-based models. Merrill et al. (2025) show that under finite precision, practical SSMs
collapse to TC [0], leading to failures on tasks like permutation composition over _S_ 5 unless the primitive is extended. Similarly, Yu & Erichson (2025) prove that a single-layer Mamba is not a universal
approximator. Several modifications have been proposed to improve expressivity. For instance,
the same work shows that a block-biased variant regains the universal approximation property with
only minor changes, either through block decomposition or a channel-specific bias. Allowing negative eigenvalues or non-triangular transitions enables linear RNNs—including diagonal and Householder/DeltaNet forms—to capture parity and, under mild assumptions, regular languages (Grazzi
et al., 2025). Complex-valued parameterizations provide another avenue for enhanced expressivity.
Diagonal LTI SSMs demonstrate effectiveness for language modeling (Gu et al., 2022b; Orvieto
et al., 2023), with complex variants achieving equivalent functions using smaller, well-conditioned
parameters (Ran-Milo et al., 2024). However, the introduction of selectivity—the central innovation
of modern SSMs (Gu & Dao, 2024)—narrowed the performance gap with Transformers by enabling
input-dependent dynamics and achieving state-of-the-art results on language modeling benchmarks,
leading practitioners to abandon complex states in favor of simpler real-valued architectures. We
extend this line of work by reintroducing complex-valued state evolution that yields a real SSM with
doubled dimensionality and block-diagonal rotations applied to the update rule—analogous through
SSD (Dao & Gu, 2024) to how RoPE (Su et al., 2023) applies complex rotations to queries and
keys in attention. The resulting data-dependent rotational structure expands stable dynamics to include oscillatory modes, enabling richer states while maintaining constant memory and linear-time
complexity.

B TRAPEZOIDAL DISCRETIZATION


**Proposition 5** (Variation of Constants (Tenenbaum & Pollard, 1985)) **.** _Consider the linear SSM_


_**h**_ ˙ ( _t_ ) = _A_ ( _t_ ) _**h**_ ( _t_ ) + **B** ( _t_ ) _x_ ( _t_ ) _,_


_where_ _**h**_ ( _t_ ) _∈_ R _[N]_ _, A_ ( _t_ ) _∈_ R _is a scalar decay, and_ **B** ( _t_ ) _x_ ( _t_ ) _∈_ R _[N]_ _._ _For_ ∆ _t_ _discretized time grid_
_τt_ = _τt−_ 1 + ∆ _t, the hidden state satisfies_

                 - _τt_
_**h**_ _t_ _≈_ _e_ [∆] _[t][A][t]_ _**h**_ _t−_ 1 + _e_ [(] _[τ][t][−][τ]_ [)] _[A][t]_ **B** ( _τ_ ) _x_ ( _τ_ ) _dτ._ (10)

_τt−_ 1


_Proof._ Since _A_ ( _t_ ) is scalar, the homogeneous system _**h**_ [˙] ( _t_ ) = _A_ ( _t_ ) _**h**_ ( _t_ ) has solution


�� _t_                    _**h**_ ( _t_ ) = _ϕ_ ( _t, s_ ) _**h**_ ( _s_ ) _,_ _ϕ_ ( _t, s_ ) = exp _A_ ( _ξ_ ) _dξ_ _._

_s_


15


The Variation of Constants formula gives us,


                  - _t_
_**h**_ ( _t_ ) = _ϕ_ ( _t, s_ ) _**h**_ ( _s_ ) + _ϕ_ ( _t, τ_ ) **B** ( _τ_ ) _x_ ( _τ_ ) _dτ._

_s_

Setting ( _s, t_ ) = ( _tk−_ 1 _, tk_ ) yields the exact _**h**_ _t_ given _**h**_ _t−_ 1. We approximate - _st_ _[A]_ [(] _[ξ]_ [)] _[ dξ]_ [by] [setting]
_A_ ( _τ_ ) _≈_ _Ak_ over [ _tk−_ 1 _, tk_ ], which gives us,



Substituting these approximations in the Variation of Constants integral, we get the approximation

                 - _τt_
_**h**_ _t_ _≈_ _e_ [∆] _[t][A][t]_ _**h**_ _t−_ 1 + _e_ [(] _[τ][t][−][τ]_ [)] _[A][t]_ **B** ( _τ_ ) _x_ ( _τ_ ) _dτ._

_τt−_ 1


B.1 TRAPEZOID DISCRETIZATION’S MASK MATRIX


_Proof._ When viewing the tensor contraction form, let us call _C_ = ( _T, N_ ) _, B_ = ( _S, N_ ) _, L_ =
( _T, S_ ) _, X_ = ( _S, P_ ) based on the Mamba-2 paper. With this decomposition of our mask, we can
view _L_ = contract( _TZ, ZS_ _→_ _TS_ )( _L_ 1 _, L_ 2).


The original contraction can be seen as


contract( _TN, SN, TS, SP_ _→_ _TP_ )( _C, B, L, X_ )


We can now view it as


contract( _TN, SN, TJ, JS, SP_ _→_ _TP_ )( _C, B, L_ 1 _, L_ 2 _, X_ )


This can be broken into the following:


_Z_ = contract( _SN, SP_ _→_ _SNP_ )( _B, X_ )

_Z_ _[′]_ = contract( _JS, SNP_ _→_ _JNP_ )( _L_ 2 _, Z_ )

_H_ = contract( _TJ, JNP_ _→_ _TNP_ )( _L_ 1 _, Z_ _[′]_ )
_Y_ = contract( _TN, TNP_ _→_ _TP_ )( _C, H_ )


Thus, we can view this step: contract( _ZS, SNP_ _→_ _ZNP_ )( _L_ 2 _, Z_ ) as a conv of size two applied on
Bx with the traditional SSD _L_ = _L_ 1 matrix.


B.2 TRAPEZOIDAL DISCRETIZATION ERROR RATE


**Standard assumptions.** We assume that: _A_ ( _t_ ) _,_ **B** ( _t_ ) _, x_ ( _t_ ) are bounded and _C_ [2] on each timestep,
so that _g_ ( _τ_ ) has two bounded derivatives; the map _**h**_ _�→_ _A_ ( _t_ ) _**h**_ + **B** ( _t_ ) _x_ ( _t_ ) is Lipschitz in _**h**_ which
is true for linear systems; _λt_ lies in a bounded interval so that the update is zero-stable.


_Proof._ Let _**g**_ ( _τ_ ) := _e_ [(] _[t][k][−][τ]_ [)] _[A][k]_ **B** ( _τ_ ) _x_ ( _τ_ ) denote the integrand in the second term of Proposition 5.
Since _A_ ( _t_ ) _,_ **B** ( _t_ ) _, x_ ( _t_ ) are _C_ [2] on [ _tk−_ 1 _, tk_ ], the function _g_ has two bounded derivatives. A secondorder Taylor expansion of _g_ around _tk−_ 1 gives us,

     - _tk_

_g_ ( _τ_ ) _dτ_ = ∆ _t g_ ( _tk−_ 1) + [∆] _t_ [2] [∆] _t_ [3] _t_ [)] _[.]_
_tk−_ 1 2 _[g][′]_ [(] _[t][k][−]_ [1][) +] 6 _[g][′′]_ [(] _[t][k][−]_ [1][) +] _[ O]_ [(∆][4]


Recall that the trapezoidal approximation to this integral is given by,


                 -                 _Qλ_ = ∆ _t_ (1 _−_ _λt_ ) _g_ ( _tk−_ 1) + _λt g_ ( _tk_ ) _._


_t_
Expanding _g_ ( _tk_ ) using Taylor expansion: _g_ ( _tk_ ) = _g_ ( _tk−_ 1) + ∆ _tg_ _[′]_ ( _tk−_ 1) + [∆] 2 [2] _[g][′′]_ [(] _[t][k][−]_ [1][) +] _[ O]_ [(∆] _t_ [3][)][.]
Substituting this into _Qλ_,


            -            _Qλ_ = ∆ _t_ (1 _−_ _λt_ ) _g_ ( _tk−_ 1) + _λtg_ ( _tk_ )

= ∆ _tg_ ( _tk−_ 1) + _λt_ ∆ [2] _t_ _[g][′]_ [(] _[t][k][−]_ [1][) +] _[ λ][t]_ ∆ [3] _t_ _t_ [)] _[.]_
2 _[g][′′]_ [(] _[t][k][−]_ [1][) +] _[ O]_ [(∆][4]


16



�� _t_
_ϕ_ ( _tk, tk−_ 1) = exp



_t_ - �� _t_

_A_ ( _ξ_ ) _dξ_ _≈_ exp
_s_ _s_




   _Ak dξ_ = _e_ [∆] _[k][A][k]_ _,_
_s_



_and a transition matrix_

        -        - �cos(Θ) _−_ sin(Θ)�
**R** _t_ = _Block_ _{R_ (∆ _t_ _**θt**_ [ _i_ ]) _}_ _[N/]_ _i_ =1 [2] _∈_ R _[N]_ _[×][N]_ _,_ _R_ (Θ) = sin(Θ) cos(Θ) _._


_Proof._ We first present the derivation for _N_ = 2; the block-diagonal structure for general even _N_
follows by grouping pairs of coordinates.

Let _ht_ + _ih_ [ˆ] _t_ denote the complexified hidden state, with parameters _A_ ( _t_ )+ _iθ_ ( _t_ ) and _B_ ( _t_ )+ _iB_ [ˆ] ( _t_ ) for
the transition and input, respectively. By the variation of constants formula (Proposition 5), applying
zero–order hold and Euler’s rule over a step [ _tk−_ 1 _, tk_ ] gives

_hk_ + _ih_ [ˆ] _k_ = _e_ [∆] _[t]_ [(] _[A][t]_ [+] _[iθ][t]_ [)] ( _hk−_ 1 + _ih_ [ˆ] _k−_ 1) + ∆ _t_ ( _Bt_ + _iB_ [ˆ] _t_ ) _xt._


17



Hence, the error is given by:

   - _tk_



2 _[t]_ �∆ [3] _t_ _[g][′′]_ [(] _[t][k][−]_ [1][) +] _[ O]_ [(∆][4] _t_ [)] _[.]_



_g_ ( _τ_ ) _dτ_ _−_ _Qλ_ =   - 21 _[−]_ _[λ][t]_ �∆ [2] _t_ _[g][′]_ [(] _[t][k][−]_ [1][) +]   - 16 _[−]_ _[λ]_ 2 _[t]_
_tk−_ 1



Under the assumption that _λt_ = [1]




[1] 2 [+] _[ c][t]_ [∆] _[t]_ [, where] _[ c][t]_ [=] _[O]_ [(1)][, then] 2 [1]



Under the assumption that _λt_ = 2 [+] _[ c][t]_ [∆] _[t]_ [, where] _[ c][t]_ [=] _[O]_ [(1)][, then] 2 _[−]_ _[λ][t]_ [=] _[−][c][t]_ [∆] _[t]_ [=] _[O]_ [(∆] _[t]_ [)][ and]

thus the ∆ [2] _t_ [term is] _[ O]_ [(∆] _t_ [3][)][.] [Therefore,]

             - _tk_



_g_ ( _τ_ ) _dτ_ _−_ _Qλ_ = _O_ (∆ [3] _t_ [)] _[,]_
_tk−_ 1



which yields an _O_ (∆ [3] _t_ [)] [local] [truncation] [error.] [Since] [the] [update] _**[h]**_ _[k]_ [=] _[e]_ [∆] _[t][A][k]_ _**[h]**_ _[k][−]_ [1] [+] _[ Q][λ]_ [is] [line][ar]
and zero–stable for bounded _λt_, standard numerical ODE results imply an _O_ (∆ [2] _t_ [)][ global error.]


B.3 TRAPEZOIDAL PARAMETERIZATION


**Parameterization** **Form of** _λt_ **ppl** _↓_


**Default** _σ_ ( _ut_ ) **15.72**

Fixed 1 _/_ 2 12 15.76


No trapezoid (Euler) 1 15.81


Table 5: **Ablations on** _λt_ **parameterization in the trapezoidal update.**


**Setting:** All runs use the Mamba-3 (SISO) 440M model trained at Chinchilla scale, with the other
architectural and optimization hyperparameters being the same as in Table 1.


The default model uses a data-dependent gate _λt_ = _σ_ ( _ut_ ), where _ut_ is a learned projection of the
current input token. In Table 5, we try different parameterizations for _λt_ and find that the default parameterization empirically performs the best. Hence we choose the simpler default parameterization
that does _not_ enforce the _O_ ( [1] 2 [+ ∆] _[t]_ [)][.]

C COMPLEX SSM PROOFS


C.1 PROOF OF PROPOSITION 2


**Proposition 2** (Complex-to-Real SSM Equivalence) **.** _Consider a complex-valued SSM_
_**h**_ ˙ ( _t_ ) = Diag� _A_ ( _t_ ) + _i_ _**θ**_ ( _t_ )� _**h**_ ( _t_ ) +       - **B** ( _t_ ) + _i_ **B** [ˆ] ( _t_ )� _x_ ( _t_ ) _,_ (6)

_y_ ( _t_ ) = Re�� **C** ( _t_ ) + _i_ **C** [ˆ] ( _t_ )� _⊤_ _**h**_ ( _t_ )� _,_


_where_ _**h**_ ( _t_ ) _∈_ C _[N/]_ [2] _,_ _**θ**_ ( _t_ ) _,_ **B** ( _t_ ) _,_ **B** [ˆ] ( _t_ ) _,_ **C** ( _t_ ) _,_ **C** [ˆ] ( _t_ ) _∈_ R _[N/]_ [2] _,_ _and_ _x_ ( _t_ ) _, A_ ( _t_ ) _∈_ R _._ _Under_ _Euler_
_discretization, this system is equivalent to a real-valued SSM_

_**h**_ _t_ = _e_ [∆] _[t][A][t]_ **R** _t_ _**h**_ _t−_ 1 + ∆ _t_ **B** _txt,_ (7)

_yt_ = **C** _[⊤]_ _t_ _**[h]**_ _[t][,]_

_with state_ _**h**_ _t_ _∈_ R _[N]_ _, projections_




   - **B** _t_
**B** _t_ = **B** ˆ _t_




- - **C** _t_
_∈_ R _[N]_ _,_ **C** _t_ = _−_ **C** [ˆ] _t_




_∈_ R _[N]_ _,_



Expanding the exponential,


                         _e_ [∆] _[t]_ [(] _[A][t]_ [+] _[iθ][t]_ [)] = _e_ [∆] _[t][A][t]_ [�] cos(∆ _tθt_ ) + _i_ sin(∆ _tθt_ ) _,_



_t_ _t_

- **R** _s_ = - 

_s_ = _i_ +1 _s_ =0




           - _ht_           so in real coordinates _**h**_ _t_ = _h_ ˆ _t_ _∈_ R [2] the recurrence becomes



_**h**_ _t_ = _e_ [∆] _[t][A][t]_ �cos(∆sin(∆ _ttθθtt_ )) _−_ cos(∆sin(∆ _tθtθt_ ) _t_ )�



_**h**_ _t_ = _e_ [∆] _[t][A][t]_ �cos(∆sin(∆ _ttθθtt_ )) _−_ cos(∆sin(∆ _tθtθt_ ) _t_ )




_xt._



_**h**_ _t−_ 1 + ∆ _t_




- _Bt_
_B_ ˆ _t_




              - ��               _R_ (∆ _tθt_ )


Stacking across _N/_ 2 such pairs yields the block-diagonal transition


_**h**_ _t_ = _e_ [∆] _[t][A][t]_ Block� _{R_ (∆ _tθt_ [ _i_ ]) _}_ _[N/]_ _i_ =1 [2]       - _**h**_ _t−_ 1 + ∆ _t_


For the output,




- **B** _t_
**B** ˆ _t_




_xt._




   -   -   - **C** _t_   - _⊤_
_yt_ = Re ( **C** _t_ + _i_ **C** [ˆ] _t_ ) _[⊤]_ ( _ht_ + _ih_ [ˆ] _t_ ) = _**h**_ _t,_

_−_ **C** [ˆ] _t_



which defines the real projection **C** _t_ _∈_ R _[N]_ in the proposition. This proves the equivalence between
complex SSM and the real block-diagonal system with rotations.


C.2 PROOF OF PROPOSITION 3


**Proposition 3** (Complex SSM, Data-Dependent RoPE Equivalence) **.** _Under the notation established_
_in_ _Proposition_ _2,_ _consider_ _the_ _real_ _SSM_ _defined_ _in_ _Eq._ _7_ _unrolled_ _for_ _T_ _time-steps._ _The_ _output_ _of_
_the above SSM is equivalent to that of a vanilla scalar transition matrix-based SSM (Eq._ _2) with a_
_data-dependent rotary embedding applied on the_ **B** _,_ **C** _components of the SSM defined as:_



_t_




_t_





- **R** _[⊤]_ _i_ [)] **[C]** _[t]_

_i_ =0




         
- **R** _[⊤]_ _i_ [)] **[B]** _[t][x][t][,]_ _**y**_ _t_ = (

_i_ =0




- _⊤_
_**h**_ _t_ (8)



_**h**_ _t_ = _e_ [∆] _[t][A][t]_ _**h**_ _t−_ 1 + (



_where_ _the_ _matrix_ _production_ _represents_ _right_ _matrix_ _multiplication,_ _e.g.,_ [�] _i_ [1] =0 **[R]** _[i]_ [=] **[R]** [0] **[R]** [1] _[.]_ _[We]_
_denote employing the vanilla SSM to compute the Complex SSM as “RoPE trick”._


_Proof._ Consider the SSM


_**h**_ _t_ = _e_ [∆] _[t][A][t]_ **R** _t_ _**h**_ _t−_ 1 + **B** _txt,_ _**y**_ _t_ = **C** _[⊤]_ _t_ _**[h]**_ _[t][,]_ (11)


where (as in Proposition 3) _At_ _∈_ R is a scalar (so that _e_ [∆] _[t][A][t]_ is a scalar and commutes with rotations), and **R** _t_ is block-diagonal orthogonal/unitary, hence **R** _[−]_ _t_ [1] = **R** _[⊤]_ _t_ [.]


Unrolling the recurrence with the convention that an empty product is the identity,




- _t_

 - _e_ [∆] _[s][A][s]_ **R** _s_


_s_ = _i_ +1




- _t_

 



**B** _ixi._ (12)



_**h**_ _t_ =



_t_



_i_ =0



Thus


_**y**_ _t_ = **C** _[⊤]_ _t_ _**[h]**_ _[t]_ [=]


Using unitarity property,



_t_

- **C** _[⊤]_ _t_


_i_ =0




- _t_

 - _e_ [∆] _[s][A][s]_ **R** _s_


_s_ = _i_ +1




**B** _ixi._ (13)



_t_




_t_ _i_

- **R** _s_ �� 

_s_ =0 _s_ =0



_i_ _t_

- **R** _s_ - _−_ 1 = - 

_s_ =0 _s_ =0



_t_ _i_

- **R** _s_ �� 

_s_ =0 _s_ =0




- **R** _[⊤]_ _s_ - _._

_s_ =0



18


Since _e_ [∆] _[s][A][s]_ are scalars, they commute with rotations; hence




   - **B** _t_
**B** _t_ = **B** ˆ _t_



_t_

_**y**_ _t_ = - **C** _[⊤]_ _t_


_i_ =0




- _t_

 - **R** _s_


_s_ =0




- _t_

 


�� _t_

 


_t_ �� _i_

- _e_ [∆] _[s][A][s]_ 

_s_ = _i_ +1 _s_ =0




- **R** _[⊤]_ _s_

_s_ =0




**B** _ixi_ (14)



_t_
= �� - **R** _[⊤]_ _s_ - **C** _t_

_s_ =0




- _⊤_ _t_

 

_i_ =0




- **R** _[⊤]_ _s_

_s_ =0




**B** _ixi._ (15)




- _t_

 


_t_ �� _i_

- _e_ [∆] _[s][A][s]_ 

_s_ = _i_ +1 _s_ =0



Define the rotated parameters **C** [¯] _t_ := �� _ts_ =0 **[R]** _s_ _[⊤]_ - **C** _t_ and **B** [¯] _i_ := �� _is_ =0 **[R]** _s_ _[⊤]_ - **B** _i._ Then




- _t_ 
 - _e_ [∆] _[s][A][s]_ **B** ¯ _ixi._ (16)


_s_ = _i_ +1



_**y**_ _t_ = **C** [¯] _[⊤]_ _t_



_t_



_i_ =0



Equivalently, introducing the rotated state _**h**_ [˜] _t_ := �� _ts_ =0 **[R]** _s_ _[⊤]_ - _**h**_ _t_,

_**h**_ ˜ _t_ = _e_ [∆] _t_ _[A]_ _t_ _**h**_ ˜ _t−_ 1 + **B** ¯ _txt,_ _**y**_ _t_ = **C** [¯] _[⊤]_ _t_ _**[h]**_ [˜] _[t][,]_ (17)


C.3 PROOF OF PROPOSITION 4


**Proposition** **4** (Rotary Embedding Equivalence with Trapezoidal Discretization) **.** _Discretizing_ _a_
_complex SSM with the trapezoidal rule (Proposition 1) yields the recurrence_







**B** _txt,_



_**h**_ _t_ = _αt_ _**h**_ _t−_ 1 + _βt_




- _t−_ 1 
 - **R** _[⊤]_ _i_


_i_ =0

 - _⊤_



**B** _t−_ 1 _xt−_ 1 + _γt_




- _t_

 - **R** _[⊤]_ _i_


_i_ =0




- _t_

 



- _t_

 -  


_**h**_ _t._ (9)



_**y**_ _t_ =




- **R** _[⊤]_ _i_ [)] **[C]** _[t]_

_i_ =0



_Here_ **R** _t is the block-diagonal rotation matrix defined in Proposition 3._


_Proof._ We begin from the complex SSM (as in Prop. 2)


_**h**_ ˙ ( _t_ ) = Diag       - _A_ ( _t_ ) + _i_ _**θ**_ ( _t_ )� _**h**_ ( _t_ ) +       - **B** ( _t_ ) + _i_ **B** [ˆ] ( _t_ )� _x_ ( _t_ ) _,_

_y_ ( _t_ ) = Re �( **C** ( _t_ ) + _i_ **C** [ˆ] ( _t_ )) _[⊤]_ _**h**_ ( _t_ )� _,_


where _A_ ( _t_ ) _∈_ R is a scalar and _**θ**_ ( _t_ ) _,_ **B** ( _t_ ) _,_ **B** [ˆ] ( _t_ ) _,_ **C** ( _t_ ) _,_ **C** [ˆ] ( _t_ ) _∈_ R _[N/]_ [2] .


Recall from Prop. 5,


               - _τt_
_**h**_ _t_ _≈_ _e_ [∆] _[t]_ [(] _[A][t]_ [+] _[i]_ _**[θ]**_ _[t]_ [)] _**h**_ _t−_ 1 + _e_ [(] _[τ][t][−][τ]_ [)(] _[A][t]_ [+] _[i]_ _**[θ]**_ _[t]_ [)][�] **B** ( _τ_ ) + _i_ **B** [ˆ] ( _τ_ )� _x_ ( _τ_ ) _dτ._

_τt−_ 1


Applying Prop. 1 to the above integral, we get

_**h**_ _t_ = _e_ [∆] _[t]_ [(] _[A][t]_ [+] _[i]_ _**[θ]**_ _[t]_ [)] _**h**_ _t−_ 1 + _βt e_ _[i]_ [∆] _[t]_ _**[θ]**_ _[t]_ [�] **B** _t−_ 1 + _i_ **B** [ˆ] _t−_ 1� _xt−_ 1 + _γt_    - **B** _t_ + _i_ **B** [ˆ] _t_    - _xt,_ (18)


wherem
_αt_ := _e_ [∆] _[t][A][t]_ _,_ _βt_ := (1 _−_ _λt_ )∆ _te_ [∆] _[t][A][t]_ _,_ _γt_ := _λt_ ∆ _t,_


Since _e_ [∆] _[t]_ [(] _[A][t]_ [+] _[i]_ _**[θ]**_ _[t]_ [)] = _αt e_ _[i]_ [∆] _[t]_ _**[θ]**_ _[t]_ and as shown in Prop. 2, multiplication by _e_ _[i]_ [∆] _[t]_ _**[θ]**_ _[t]_ is a block-diagonal
rotation in real coordinates, we get the real _N_ -dimensional recurrence


_**h**_ _t_ = _αt_ **R** _t_ _**h**_ _t−_ 1 + _βt_ **R** _t_ **B** _t−_ 1 _xt−_ 1 + _γt_ **B** _t xt,_ (19)

_yt_ = **C** _[⊤]_ _t_ _**[h]**_ _[t][,]_

where **R** _t_ = Block� _{R_ (∆ _t_ _**θ**_ _t_ [ _i_ ]) _}_ _[N/]_ _i_ =1 [2] - where _R_ (Θ) = �cos Θsin Θ _−_ cos Θsin Θ� _,_ and projections




- - **C** _t_
_,_ **C** _t_ = _−_ **C** [ˆ] _t_




_._ Note that **R** _t_ is orthogonal, so **R** _[−]_ _t_ [1] = **R** _[⊤]_ _t_ [.]


19


|X|B|C|Col4|Col5|Col6|
|---|---|---|---|---|---|
|X||**Ro**|**PE**|**PE**|**PE**|
|X|**N**||**N**|**N**|**N**|
|||||||


|N<br>X<br>Y<br>SSM<br>A XB C<br>! !<br>Conv|Col2|
|---|---|
|B C<br>X<br>~~X~~<br>!<br>**Conv**<br>**SSM**<br>A<br>**N**<br>Y<br>!||
|||


|X<br>Y<br>SSM<br>AX B C<br>RoPE !<br>N N &|Col2|
|---|---|
|||



Left-multiplying equation 19 by [�] _s_ _[t]_ =0 **[R]** _s_ _[⊤]_ [and using] **[ R]** _t_ _[⊤]_ **[R]** _[t]_ [=] _[ I]_ [,]

_**h**_ ˜ _t_ = _αt_ ˜ _**h**_ _t−_ 1 + _βt_ **B** ¯ _t−_ 1 _xt−_ 1 + _γt_ **B** ¯ _t xt,_

_yt_ = **C** [¯] _[⊤]_ _t_ _**[h]**_ [˜] _[t][.]_


This is a vanilla scalar-transition SSM with data-dependent rotary embeddings absorbed into **B** _,_ **C**
via cumulative products of **R** _[⊤]_ _s_ [.]


D MIMO FOR MAMBA-3


With hindsight from Mamba and with inference in mind, we propose the following MIMO formulation:


**Mamba** **with** **MIMO.** With a given batch, head, and sequence position _t_, consider the input
**U** _t_ _∈_ R _[D]_ . Also denote _P, R_ _∈_ N as the head dimension and MIMO rank, respectively. We
first obtain SSM parameters via a set of projections defined in terms of tensor contraction notation
as follows:


**B** _t_ = contract( _DNR, D_ _→_ _NR_ )( **WB** _,_ **U** _t_ ) **C** _t_ = contract( _DNR, D_ _→_ _NR_ )( **WC** _,_ **U** _t_ ) _,_

**X** _[′]_ _t_ [=][ contract][(] _[PD, D]_ _[→]_ _[P]_ [)(] **[W]** **X** _[′][,]_ **[ U]** _t_ [)] **X** _t_ = contract( _PR, P_ _→_ _PR_ )( **WX** _,_ **X** _[′]_ _t_ [)] _[,]_


where **WB** _,_ **WC** _,_ **WX** _′,_ **WX** are model parameters. Additionally, we obtain the residual term **Z** _t_
in the same manner as **X** _t_ with weights **WZ** _[′]_ and **WZ** . The state update and the SSM output is then
computed via the following MIMO SSM:

**H** _t_ = _at_ **H** _t−_ 1 + **B** _t_ **X** _[⊤]_ _t_ _[∈]_ [R] _[N]_ _[×][P][,]_ **Y** _t_ = **H** _[⊤]_ _t_ **[C]** _[t]_ _[∈]_ [R] _[P][ ×][R][.]_

The intermediate output **Y** _[′]_ _t_ is obtained via some residual function _ϕ_, **Y** _[′]_ _t_ _←_ _ϕ_ ( **Y** _t,_ **Z** _t_ ). Finally,
the layer output **O** _t_ _∈_ R _[D]_ is computed via the following down projections:

**O** _[′]_ _t_ [=][ contract][(] _[PR, R][ →]_ _[P]_ [)(] **[W]** **O** _[′][,]_ **[ Y]** _[′]_ _t_ [)] **O** _t_ = contract( _P, PD_ _→_ _D_ )( **WO** _,_ **O** _[′]_ _t_ [)] _[.]_


20

















Linear projection


Sequence transformation


MIMO projection (optional)

Nonlinearity (activation,
normalization, multiplication, etc.)





**Mamba-2 Block**



**Mamba-3 Block**



Figure 4: Contrasting Mamba-2 and Mamba-3 Architectures: Key updates include trapezoidal discretization, data-dependent RoPE embeddings, MIMO projections, QK normalization, and learnable
biases.


We define the following,



_t_ _t_

- **R** _[⊤]_ _s_ - _**h**_ _t,_ **B** ¯ _t_ := - 
_s_ =0 _s_ =0



_t_
_**h**_ ˜ _t_ := - 


_t_ _t_

- **R** _[⊤]_ _s_ - **B** _t,_ **C** ¯ _t_ := - 
_s_ =0 _s_ =0




- **R** _[⊤]_ _s_ - **C** _t._

_s_ =0



This formulation enhances the existing Mamba3 architecture by providing a lightweight parameterization that transforms the set of independent SISO SSMs within each head into a set of MIMO
SSMs. Here, we note that the hardware-efficient chunking technique employed by Mamba2 for pretraining can be applied with little change, as the MIMO dimension _r_ is orthogonal to the sequence
dimension.


E EXPERIMENTAL DETAILS


**Language** **Modeling.** Our pretraining procedures follow that of Dao & Gu (2024)’s section D.2.
All models at each scale follow the same procedure and were trained with bfloat16. The Mamba
family of models were trained using the standard expand factor of 2 and a dstate of 128 and head
dimension of 64. The Transformer baselines follows Dao & Gu (2024), and the Gated DeltaNet
baselines follow (Yang et al., 2025a). We utilize the Llama-3.1 tokenizer (Grattafiori et al., 2024)
for all models.


We utilize LM Evaluation Harness (Gao et al., 2024) to test the zero-shot languag modeling capabilities of our pretrained model on LAMBADA (OpenAI version) (Paperno et al., 2016), HellaSwag (Zellers et al., 2019), PIQA (Bisk et al., 2019), Arc-Easy/Arc-Challenge (Clark et al., 2018),
WinoGrande (Sakaguchi et al., 2019), and OpenBookQA(Mihaylov et al., 2018).


**Real-World and Synthetic Retrieval.** For our real-world retrieval tasks, we evaluate on the common suite consisting of SWDE (Arora et al., 2025b), SQUAD (Rajpurkar et al., 2018), FDA (Arora
et al., 2025b), TriviaQA (Joshi et al., 2017), NQ (Kwiatkowski et al., 2019), and DROP (Dua et al.,
2019). We utilize the cloze-formatted version of the aforementioned tasks provided by Arora et al.
(2025b; 2024), as the original datasets are in a question-answering format, making it challenge for
solely pretrained models. All tasks were truncated to match the training context length. The synthetic NIAH tasks (Hsieh et al., 2024) were also run with LM Evaluation Harness.


**State-Tracking Synthetics.** Training follows a sequence length curriculum that progresses from 3
-40 to 160, evaluated at 256. Each curriculum runs for 10 [4] steps with batch size 256. We use 1 layer
models for Parity and 3 layer models for Modular-arithmetic tasks. The state size is chosen to be
64, and we sweep _d_ model _∈{_ 32 _,_ 64 _}_ and 8 learning rates logarithmically spaced between 10 _[−]_ [4] and
10 _[−]_ [2], reporting the best validation accuracy.


F ADDITIONAL EXPERIMENTAL RESULTS


Context Length Extrapolation



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/13549_Mamba_3_Improved_Sequenc_extracted/images/13549_Mamba_3_Improved_Sequenc.pdf-20-0.png)

Figure 5: Pretrained 1.5B models’ performance on the held-out FineWeb-Edu test set at varying
context lengths. Mamba-3 exhibits strong length extrapolation while Mamba-2 falters at longer
contexts.


21



10.8


10.6


10.4


10.2


10.0



1K 2K 4K 8K 16K 32K
Context length



Table 6: Downstream language modeling evaluations on parameter-matched pretrained models, including Mamba-3 MIMO. Mamba-3 MIMO’s average accuracy on all tasks is more than 1 percentage point better than the next best (Mamba-3 SISO).


**Model** FW-Edu LAMB. LAMB. HellaS. PIQA Arc-E Arc-C WinoGr. OBQA Average
ppl _↓_ ppl _↓_ acc _↑_ acc ~~n~~ _↑_ acc _↑_ acc _↑_ acc ~~n~~ _↑_ acc _↑_ acc _↑_ acc _↑_


Transformer-440M 13 _._ 03 21 _._ 2 41 _._ 7 50 _._ 5 69 _._ 9 67 _._ 6 34 _._ 6 **56** _**.**_ **7** 26 _._ 0 49 _._ 6
Gated DeltaNet-440M 13 _._ 12 19 _._ 0 40 _._ 4 50 _._ 5 70 _._ 5 67 _._ 5 34 _._ 0 55 _._ 3 25 _._ 8 49 _._ 1
Mamba-2-440M 13 _._ 00 19 _._ 6 40 _._ 8 51 _._ 7 70 _._ 6 68 _._ 8 35 _._ 0 54 _._ 1 26 _._ 0 49 _._ 6
**Mamba-3-440M** 12 _._ 87 19 _._ 6 40 _._ 2 51 _._ 7 **71** _**.**_ **9** 68 _._ 9 34 _._ 4 55 _._ 8 26 _._ 0 49 _._ 8
**Mamba-3-MIMO-440M** **12** _**.**_ **72** **17** _**.**_ **1** **43** _**.**_ **4** **52** _**.**_ **8** 70 _._ 8 **69** _**.**_ **6** **35** _**.**_ **6** 56 _._ 3 **28** _**.**_ **4** **51** _**.**_ **0**


Transformer-880M 11 _._ 42 15 _._ 0 44 _._ 7 57 _._ 2 72 _._ 6 71 _._ 6 39 _._ 2 57 _._ 7 26 _._ 8 52 _._ 8
Gated DeltaNet-880M 11 _._ 39 12 _._ 7 47 _._ 1 57 _._ 5 72 _._ 6 72 _._ 5 38 _._ 8 57 _._ 9 **30** _**.**_ **6** 53 _._ 9
Mamba-2-880M 11 _._ 35 13 _._ 8 45 _._ 0 58 _._ 1 72 _._ 5 72 _._ 3 38 _._ 7 56 _._ 8 30 _._ 2 53 _._ 4
**Mamba-3-880M** 11 _._ 23 12 _._ 9 47 _._ 2 58 _._ 8 73 _._ 6 72 _._ 7 40 _._ 2 58 _._ 4 30 _._ 0 54 _._ 4
**Mamba-3-MIMO-880M** **11** _**.**_ **11** **11** _**.**_ **8** **49** _**.**_ **5** **59** _**.**_ **2** **73** _**.**_ **7** **74** _**.**_ **7** **41** _**.**_ **2** **59** _**.**_ **9** 28 _._ 6 **55** _**.**_ **3**


|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Mamba-3<br>Mamba-3<br>Llama|MIMO<br>SISO|
|---|---|---|---|---|---|---|---|---|---|
|||||||||||
|||||||||||
|||||||||GatedDe<br>Mamba-2|ltaNet<br>|
|||||||||||
|||||||||||
|||||||||||
|||||||||||
|||||||||||
|||||||||||
|||||||||||
|||||||||||
|||||||||||



Figure 6: Mamba-3 demonstrates superior performance compared to strong baselines like Mamba-2,
Llama, and Gated Deltanet. These are 440M models, trained and evaluated on FineWeb-Edu.


We also compare the effectiveness of state size usage of Mamba variants to a Gated DeltaNet baseline in Figure 7. We highlight the difficulty of directly comparing GDN versus Mamba-style models
due to the differing head structure, multi-head compared to multi-value respectively. Our experiments hold GDN’s v ~~e~~ xpand to 2 and decrease the head dimension accordingly to vary the relative
total state size. Similar to Figure 3, we train 440M models to 2 _×_ Chinchilla tokens and sweep
across _d_ state = _{_ 32 _,_ 64 _,_ 128 _}_ for the Mamba models and _d_ head dim = _{_ 32 _,_ 64 _,_ 128 _}_ for GDN. We
parameter match all models.


22



16.0


15.5


15.0


14.5


14.0


13.5


13.0


12.5


12.0



Mamba-3 Validation Perplexity


0 25000 50000 75000 100000 125000 150000 175000
Global Step

Relative Total State Size vs Pretraining Perplexity



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/13549_Mamba_3_Improved_Sequenc_extracted/images/13549_Mamba_3_Improved_Sequenc.pdf-22-0.png)

Table 7: Ablations on _B, C_ bias initialization (left) and presence (right) for Mamba-3.


H INFERENCE KERNEL LATENCY ANALYSIS


H.1 KERNEL IMPLEMENTATIONS AND FUSION STRUCTURE


In Table 3, we detail the DSL (Triton, CuTe, PyTorch) and the fusion level of the kernels used in our
latency analysis. For Mamba-2 and Gated DeltaNet (GDN), we directly use the publicly released
Triton kernels from the respective authors. For Mamba-3, we implement new inference kernels with
a comparable fusion structure: the forward uses a Triton kernel fused with rotary position embeddings, while the decode path uses a CuTe kernel fused with gating and MIMO projection.


In Tables 8 and 9, we abbreviate IP = input projection, Conv = 1D convolution, Gate = gating, OP =
output projection. Colors indicate implementation backend (Torch, Triton, CuTe).


23



15.0

14.9

14.8

14.7

14.6

14.5





10 [5]

Relative Total State Size



Figure 7: Exploration of state size (inference speed proxy) versus pretraining perplexity (performance proxy). Mamba-3 and Mamba-3 MIMO continue set the Pareto frontier.


G ARCHITECTURE ABLATIONS


We explore our model architecture’s ablation in this section. All models are trained at the 440M
scale to Chinchilla optimal number of tokens (20 _×_ tokens to parameters) with the same experimental
procedures as our pretrained models as covered in Appendix E unless otherwise stated.


**B,C Bias Parameterization.** The Mamba-3 model’s separate _B_ and _C_ biases are head-specific and
channel-wise and added to both **B** and **C** after the QK-Norm. While the biases in the final Mamba-3
model are trainable, data-independent parameters and initialized to all ones, we explore various bias
parameterizations in Table 7a. We find our models are not very sensitive to the initialization of the
biases as long as they are positive. We choose the all-ones initialization due to it’s simplicity.


We also explore the impact removing the _B_ or _C_ bias on performance in Table 7b (bias is initialized
with our default parameterization when utilized). Unlike in Yu & Erichson (2025), which finds that
_B_ bias by itself is able to improve performance on Mamba-1, our experiments find that only having
_B_ bias hurts performance slightly and that _B_ and _C_ biases have synergetic properties.



**Bias Init.** **Trainable** **ppl** _↓_


1.0 ✓ 15.72
0.0 ✓ 16.57
1.0 _×_ 15.80
_U_ (0 _,_ 1) ✓ 15.76
_U_ ( _−_ 1 _,_ 1) ✓ 16.07


(a) Effect of parameterization of the _B_ and _C_ bias
on model performance, measured by pretraining
perplexity. We find our default initialization of allones (first row) provides the best performance, but
performance is not sensitive as long as biases are
positive.



**B Bias** **C Bias** **ppl** _↓_


_×_ _×_ 16.52
✓ _×_ 16.68
_×_ ✓ 15.98
✓ ✓ 15.69


(b) Applying a bias to both _B_ and _C_ leads to the
best performance. Only applying _B_ bias (BlockBiased (Yu & Erichson, 2025) Mamba-3 variant)
does not provide significant gains over the no-bias
baseline.


Table 8: Kernel DSL and fusion structure for **forward** (prefill) kernels.


**Model (Forward)** **Kernel DSL** **Fusion Level**


Mamba-2 Triton IP, Conv, SSM, Gate+OP

Gated DeltaNet Triton IP, Conv, Chunked Delta, Gate+OP

Mamba-3 (SISO) Triton IP, SSM+Rotary, Gate+OP

Mamba-3 (MIMO) Triton IP, SSM+Rotary, Gate+OP


Table 9: Kernel DSL and fusion structure for **decode** kernels.


**Model (Decode)** **Kernel DSL** **Fusion Level**


Mamba-2 Triton IP, Conv, SSM, Gate+OP

Gated DeltaNet Triton IP, Conv, Recurrent Delta, Gate+OP

Mamba-3 (SISO) CuTe + Triton IP, Rotary, SSM+Gate+OP

Mamba-3 (MIMO) CuTe + Triton IP, Rotary, SSM+Gate+OP+MIMO


H.2 EXTENDED PREFILL AND PREFILL+DECODE LATENCY MEASUREMENTS


**Models.** We benchmark Mamba-3 1.5B (SISO), Mamba-2 1.5B, Gated DeltaNet (GDN) 1.5B, and
a strong Transformer baseline implemented via the vLLM engine (v0.11.0) with Llama-3.2 1B. [3] All
recurrent models are trained at the 1.5B scale with _d_ model = 2048 and 24 layers. For Mamba variants
we set state size as 128 and head dimension 64; for GDN we use QK head dimension as 128.


**Setting.** Sequence lengths were swept over _L_ _∈{_ 512 _,_ 1024 _,_ 2048 _,_ 4096 _,_ 16384 _}_ for prefill, with
an equal number of tokens decoded. For sequence lengths _{_ 512 _,_ 1024 _,_ 2048 _,_ 4096 _}_, we use batch
size of 128; for sequence lengths _{_ 16384 _}_, we use batch size of 16. We use a single H100-SXM
80GB GPU and report wall-clock times (in seconds) over 3 repetitions.


Table 10: Prefill and Prefill+Decode latency across sequence lengths.


**Model** **512 tokens** **1024 tokens** **2048 tokens** **4096 tokens** **16384 tokens**


Prefill Prefill+Dec Prefill Prefill+Dec Prefill Prefill+Dec Prefill Prefill+Dec Prefill Prefill+Dec


vLLM (Llama-3.2-1B) **0.26** 4.45 **0.52** 9.60 **1.08** 20.37 **2.08** 58.64 **1.52** 122.06
Gated DeltaNet 0.48 4.52 0.95 9.04 1.90 18.07 3.79 36.14 1.91 71.66
Mamba-2 0.48 4.62 0.96 9.24 1.91 18.48 3.81 36.94 1.92 57.90
Mamba-3 (SISO) 0.48 **4.33** 0.95 **8.64** 1.90 **17.29** 3.80 **34.57** 1.91 **53.97**


We observe that (i) Mamba-3 adds minimal forward-pass cost showing that the trapezoidal update,
complex state tracking, and MIMO parameterization remain lightweight; (ii) decode latency is competitive across recurrent models; and (iii) recurrent mixers scale more gently with context length
than vLLM Llama-3.2-1B, which grows much faster with _L_ due to KV-cache overhead.


[3https://huggingface.co/meta-llama/Llama-3.2-1B](https://huggingface.co/meta-llama/Llama-3.2-1B)


24


