Under review as a conference paper at ICLR 2026

MAMBA-3: IMPROVED SEQUENCE MODELING USING
STATE SPACE PRINCIPLES

Anonymous authors
Paper under double-blind review

ABSTRACT

The recent scaling of test-time compute for LLMs has restricted the practical de-
ployment of models to those with strong capabilities that can generate high-quality
outputs in an inference-efficient manner. While current Transformer-based mod-
els are the standard, their quadratic compute and linear memory bottlenecks have
spurred the development of sub-quadratic models with linear-scaling compute
with constant memory requirements. However, many recent linear-style models
lack certain capabilities or lag behind in quality, and even their linear-time infer-
ence is not hardware-efficient. Guided by an inference-first perspective, we intro-
duce three core methodological improvements inspired by the state-space model
viewpoint of linear models. We combine a: 1) more expressive recurrence derived
from discretization , 2) complex-valued state update rule that enables richer
state tracking, and 3) multi-input, multi-output formulation together, resulting
Together with architectural refinements, our Mamba-3
in a stronger model.
model achieves significant gains across retrieval, state-tracking, and downstream
language modeling tasks. Our new architecture sets the Pareto-frontier for per-
formance under a fixed inference budget and outperforms strong baselines in a
head-to-head comparison.

INTRODUCTION

1
Test-time compute has emerged as a key driver of progress in AI, with techniques like chain-of-
thought reasoning and iterative refinement demonstrating that inference-time scaling can unlock
new capabilities (Wu et al., 2025; Snell et al., 2024). This paradigm shift makes inference effi-
ciency (Kwon et al., 2023; Li et al., 2024) paramount, as the practical impact of AI systems now
depends critically on their ability to perform large-scale inference during deployment. Model archi-
tecture design plays a fundamental role in determining inference efficiency, as architectural choices
directly dictate the computational and memory requirements during generation. While Transformer-
based models (Vaswani et al., 2017) are the current industry standard, they are fundamentally bottle-
necked by linearly increasing memory demands through the KV cache and quadratically increasing
compute requirements through the self-attention mechanism. These drawbacks have motivated re-
cent lines of work on sub-quadratic models, e.g., state-space models (SSMs), which, despite utilizing
only constant memory and linear compute, have comparable or better performance than their Trans-
former counterparts. Models that benefit the most from this new scaling paradigm perform well on
the following three axes: (i) quality, (ii) capability, and (iii) inference efficiency.

Recent model architectures have tried to strike a balance between the three, but many fall short on
at least one of these three axes. In particular, Mamba-2 and Gated DeltaNet (GDN), which have
gained significant traction and adoption due to their inference efficiency, made architectural design
choices that enable their linear compute requirements but sacrifice quality and capabilities (Dao &
Gu, 2024; Yang et al., 2025a). For example, Mamba-2 was developed to improve training speed
and simplicity over Mamba-1 (Gu & Dao, 2024), opting out of more expressive parameterizations
of the underlying SSM and hindering the quality of the model (Dao & Gu, 2024). Linear attention-
style models (Katharopoulos et al., 2020) have also been shown to lack certain capabilities, with
poor state-tracking abilities, e.g., determining parity of bit sequences, being one of the most no-
table (Grazzi et al., 2025; Sarrof et al., 2024). In addition, despite these sub-quadratic models being
prized for theoretically efficient inference, these inference algorithms are not hardware efficient. In
particular, because these algorithms were developed from a training perspective, their decoding
phase has low arithmetic intensity (the ratio of FLOPs to memory traffic), resulting in large portions
of hardware remaining idle.

1

000
001

002
003
004
005
006
007

008
009
010
011
012
013

014
015
016
017
018

019
020
021
022
023
024

025
026
027
028
029
030

031
032
033
034
035
036

037
038
039
040
041

042
043
044
045
046
047

048
049
050
051
052
053

Under review as a conference paper at ICLR 2026

To develop more performant models from an inference-first paradigm, we introduce three core
methodological changes on top of Mamba-2, influenced by a SSM-centric viewpoint of sub-
quadratic models. While many recent models fall into the linear attention framework (Dao &
Gu, 2024; Yang et al., 2025a; Sun et al., 2023), we find that the classical SSM toolbox (Kalman,
1960; Gopal, 1993) leads to natural interpretations and improvements on modeling.

Trapezoidal Discretization. We discretize the underlying continuous-time dynamical system with
a trapezoidal methodology. The final recurrence is a more expressive superset of Mamba-2’s recur-
rence and can be viewed as a convolution. We combine this new discretization with applied biases
on the B, C, inspired by Yu & Erichson (2025), and find that their synergy is able to empirically
replace the short causal convolution in language modeling which was previously hypothesized to be
essential for recurrent models.

Complex-valued State-Space Model. By viewing the underlying SSM of Mamba-3 as complex-
valued, we enable a more expressive state update than Mamba-2’s. This change in update rule,
designed to be lightweight for training and inference, overcomes the lack of state-tracking ability
common in many current linear models. We emphasize that our complex-valued update rule is equiv-
alent to a data-dependent rotary embedding and can be efficiently computed (Su et al., 2023).

Multi-Input, Multi-Output SSM. To improve FLOP-efficiency during decoding, we shift from
outer-product-based state update to matrix-multiplication-based state update . In view of the signal
processing foundations of SSMs, such a transition exactly coincides with the generalization from
a single-input single-output (SISO) sequence dynamic to a multiple-input multiple-output (MIMO)
one. Here, we found that MIMO is particularly suitable for inference, as the extra expressivity allows
for more compute during state update, without increasing the state size and hence compromising
speed.

These three SSM-centric methodological changes are core to our Mamba-3 mixer primitive. We
also make adjustments to the overall architecture to ensure more similarity to the baseline Trans-
former architecture. Mamba-3 swaps the pre-output projection norm with the more common QK-
normalization (Team et al., 2025; OLMo et al., 2025) and makes the short convolution, a common
component found in many other sub-quadratic models (Gu & Dao, 2024; Yang et al., 2025a; von
Oswald et al., 2025), optional.

We empirically validate our new model on a suite of synthetic and language-modeling tasks.

• Better Quality. Mamba-3 matches or outperforms Mamba-2 and other open-source architectures
on standard downstream language modeling evaluations. For example, Mamba-3-1.5B’s average
accuracy on all downstream tasks is better than that of its Transformer, Mamba-2, and Gated
DeltaNet counterparts.

• New Capabilities. Mamba-3’s complexification of the SSM state enables the model to solve
synthetic state-tracking tasks that Mamba-2 cannot. We empirically demonstrate that the efficient
RoPE-like calculation is able to near perfectly solve arithmetic tasks, while Mamba-3 without
RoPE and Mamba-2 perform not better than random guessing.

• Stronger Inference Efficiency. Mamba-3’s MIMO variant retains the same state size while en-
abling better hardware utilization compared to standard Mamba-3 and other models. Its improved
performance without increased memory requirements pushes the pareto-frontier of inference ef-
ficiency.

2 PRELIMINARIES

2.1 NOTATION

Scalars are denoted by plain-text letters (e.g., x, y). Tensors, including vectors and matrices, are
denoted by bold letters (e.g., h, C). The shape of the tensor can be inferred from the context. We
denote the input sequence length as T , the model dimension as D, and the SSM state size as N . For
time indices, we use subscripts (e.g., xt for the input at time t). The Hadamard product between two
tensors is denoted by ⊙. For a vector of size v ∈ Rd, we denote Diag(v) ∈ Rd×d as the diagonal
matrix with the vector v as the diagonal, and for products of scalars across time steps, we use the
notation αt···s = α×

t:s = (cid:81)t

i=s αi.

2

054
055

056
057
058
059
060
061

062
063
064
065
066
067

068
069
070
071
072

073
074
075
076
077
078

079
080
081
082
083
084

085
086
087
088
089
090

091
092
093
094
095

096
097
098
099
100
101

102
103
104
105
106
107

Under review as a conference paper at ICLR 2026

2.2 SSM PRELIMINARIES

State Space Models (SSMs) describe continuous-time linear dynamics via

˙h(t) = A(t) h(t) + B(t) x(t),

y(t) = C(t)⊤h(t),

where h(t) ∈ RN is the hidden state, x(t) ∈ R the input, and A(t) ∈ RN ×N , B(t), C(t) ∈ RN . For
discrete sequences with step size ∆t, Euler’s discretization gives the recurrence

ht = e∆tAt ht−1 + ∆t Bt xt,

yt = C⊤

t ht.

Mamba-2’s parameterization. Mamba-2 (Dao & Gu, 2024) makes the SSM data-dependent and
hardware-efficient by (i) projecting A = A ∈ R<0, and B, C ∈ RN from the current token and (ii)
choosing transition matrix A = A as a data-dependent scalar. Writing αt := e∆tAt ∈ (0, 1) and
γt := ∆t, the update becomes

ht = αt ht−1 + γt Bt xt,

yt = C⊤

t ht.

The scalar At < 0 is an input-dependent forget-gate (decay) αt, and the parameter selectivity ∆t
jointly controls the forget-gate (αt = exp(∆tAt)) and the input-gate (γt = ∆t): larger ∆t forgets
faster and up-weights the current token more strongly, while smaller ∆t retains the hidden state with
minimal contributions from the current token.

2.3 STRUCTURED MASKED REPRESENTATION AND STATE SPACE DUALITY

Dao & Gu (2024) show that a large class of SSMs admit a matrix form that vectorizes the time-step
recurrence. For instance, Mamba-2’s recurrence can be vectorized as a masked matrix multiplica-
tion,

Y = (L ⊙ C ¯B⊤)X =













1
α1
...
αT...1

1

. . .
· · · αT







X,

⊙ CB⊤






1

(1)

where L ∈ RT ×T is the structured mask, B, C ∈ RT ×N , X ∈ RT ×D is the input to the SSM and
Y ∈ RT ×D is its output. Within this form, Mamba-2 can be viewed as a type of linear attention by
setting Q = C, K = B, V = X and viewing L as a causal, data-dependent mask. When all α = 1,
the expression reduces to (causal) linear attention (Katharopoulos et al., 2020). A more detailed
coverage of related linear-time sequence mixers can be found at Appendix A.

3 MODEL DESIGN FROM A STATE-SPACE VIEWPOINT
We introduce Mamba-3, with three new innovations rooted in classical state-space theory: trape-
zoidal discretization for more expressive dynamics, complex-valued state spaces for state-tracking,
and multi-input multi-output (MIMO) to improve hardware utilization. These advances address the
quality, capability, and efficiency limitations of current sub-quadratic architectures.

3.1 TRAPEZOIDAL DISCRETIZATION

Structured SSMs are naturally defined as continuous-time dynamical systems that map input func-
tions, x(t) ∈ R, to output functions, y(t) ∈ R, for time t > 0. In sequence modeling, however,
the data is only observed at discrete time steps, which then requires applying a discretization step
to the SSM to transform its continuous-time dynamics into a discrete recurrence. The preliminary
step in deriving Mamba-3’s discretization is to apply the Variation of Constants formula (Proposi-
tion 5), which decomposes the hidden state into an exponentially decay term and a state update term
“information” term dependent on the most recent inputs.

The first step in deriving the discretized recurrence is to approximate the “state-update” integral in
equation 10. A straightforward choice, used in Mamba-2, is applying Euler’s rule (S¨uli & Mayers,
2003), which approximates the integral by holding the (right) endpoint constant throughout the
interval (Fig. 1). This yields Mamba-2’s recurrence,

ht = e∆tAt ht−1 + (τt − τt−1)e(τt−τt)At Bt xt

≈ e∆tAt ht−1 + ∆t Bt xt.

(2)

3

108
109

110
111
112
113
114
115

116
117
118
119
120
121

122
123
124
125
126

127
128
129
130
131
132

133
134
135
136
137
138

139
140
141
142
143
144

145
146
147
148
149

150
151
152
153
154
155

156
157
158
159
160
161

Under review as a conference paper at ICLR 2026

Figure 1: Left: The structured mask induced by the generalized trapezoid rule is a product of the
decay and convolutional mask. Right: Euler (hold endpoint) vs trapezoidal rule (average endpoints).

However, Euler’s rule provides only a first-order approximation to the “state-update” integral: local
truncation error is O(∆2
t ), which accumulates across steps to yield a global error of O(∆t) over the
sequence. In contrast, we adopt a generalized trapezoidal rule, which provides a second-order ac-
curate approximation of the integral, offering improved accuracy over the Euler’s rule. Specifically,
it approximates the integral with a data-dependent, convex combination of both interval endpoints.
This generalization extends the classical trapezoidal rule (S¨uli & Mayers, 2003), which simply aver-
ages the interval endpoints, by allowing for a data-dependent convex combination (Fig. 1).

Proposition 1 (Generalized Trapezoidal Discretization). Approximating the state-update integral
in equation 10 by the general trapezoidal rule yields the recurrence,

ht = e∆tAtht−1 + (1 − λt)∆te∆tAtBt−1xt−1 + λt∆tBtxt,

:= αtht−1 + βtBt−1xt−1 + γtBtxt,

(3)
(4)

2 . b) Mamba-2’s Euler’s rule, which is recovered when λt = 1.

where λt ∈ [0, 1] is a data-dependent scalar, αt := e∆tAt, βt := (1 − λt)∆te∆tAt, γt := λt∆t.
Remark 1 (Expressivity). Our scheme is a generalization of a) The classical trapezoid rule which is
recovered when λt = 1
Remark 2 (Error Rate). This is a second-order discretization with local truncation error O(∆3
t )
and global error O(∆2
t ) over the sequence under standard stability assumptions, provided that the
trapezoidal parameter satisfies λt = 1
2 + O(∆t). However, our ablations indicate that not enforcing
this constraint is the best for empirical performance. See Appendix B.2,B.3 for details.
3.1.1 TRAPEZOIDAL DISCRETIZATION IS A CONVOLUTIONAL MASK
We can view the generalized trapezoidal discretization as applying a data-dependent convolution
of size two on the projected input, Btxt, to the SSM. We now show that a similar vectorization to
Equation (1) holds with the generalized trapezoidal discretization. Unrolling the recurrence starting
from h0 = γ0B0x0 results in hT = αT ···2(γ0α1 + β1) B0x0 + · · · + γT BT xT .
Unrolling these rows shows that the mask induced by the trapezoidal update is no longer a fixed av-
eraging of endpoints (as in the classical trapezoidal rule), but a data-dependent convex combination
of the two interval endpoints. In the SSD representation, this corresponds to a mask L:











1

γ2







γ0
(γ0α1 + β1)
α2(γ0α1 + β1)
...
αT ···2(γ0α1 + β1)

1
α1
α2α1
...
αT ···1
Here, the first factor is precisely the lower-triangular decay mask from Mamba-2, while the second
factor encodes the size two convolution induced by the trapezoidal rule through the coefficients
(βt, γt). We provide a rigorous proof for this decomposition in Appendix B.1.
3.2 COMPLEX-VALUED SSMS

. . .
· · · γT

. . .
· · · γT

γ0
β1
0
...
0






1

. . .
· · ·

























. (5)

γ2

=



Modern SSMs are designed with efficiency as the central goal, motivated by the need to scale to
larger models and longer sequences. For instance, successive architectures have progressively sim-
plified the state transition matrix: S4 (Gu et al., 2022a) used complex-valued Normal plus Low Rank
(NPLR) matrices, Mamba (Gu & Dao, 2024) reduced this to a diagonal of reals, and Mamba-2 (Dao
& Gu, 2024) further simplified it to a single scalar. Although these simplifications largely maintain
language modeling performance, recent works (Merrill et al., 2025; Sarrof et al., 2024; Grazzi et al.,
2025) have shown that they degrade the capabilities of the model on simple state-tracking tasks such
as parity and modular arithmetic, which can be solved by a one-layer LSTM.

4

162
163

164
165
166
167
168
169

170
171
172
173
174
175

176
177
178
179
180

181
182
183
184
185
186

187
188
189
190
191
192

193
194
195
196
197
198

199
200
201
202
203

204
205
206
207
208
209

210
211
212
213
214
215

𝑡!"#𝑡!"#𝑡!𝑡!!𝑒!!(#!$%)		𝐵𝜏𝑥𝜏𝑑𝜏	𝑡!"#	𝑡!≈𝛼!:!	×𝛼%:!	×𝛼&:!	×𝛼%:%	×𝛼&:%	×𝛼&:&	×1111𝛾'𝛾!𝛾%𝛾&ℳ=𝛽!𝛽%𝛽&Under review as a conference paper at ICLR 2026

216
217

218
219
220
221
222
223

224
225
226
227
228
229

230
231
232
233
234

235
236
237
238
239
240

241
242
243
244
245
246

247
248
249
250
251
252

253
254
255
256
257

258
259
260
261
262
263

264
265
266
267
268
269

This limitation, formalized in Theorem-1 of (Grazzi et al., 2024), arises from restricting the eigen-
values of the transition matrix to real numbers, which cannot represent “rotational” hidden state dy-
namics. For instance, consider the parity function on binary inputs {0, 1}, defined as (cid:80)
t xt mod 2.
This task can be performed using update: ht = R(πxt)ht−1, where R(·) is a 2-D rotation matrix.
Such rotational dynamics cannot be expressed with real eigenvalues.

To recover this capability, we begin with complex SSMs (6), which are capable of representing
state-tracking dynamics. We show that, under discretization (Proposition 5), complex SSMs can
be formulated as a real SSMs with a block-diagonal transition matrix composed of 2 × 2 rotation
matrices (Proposition 2). We then show that this is equivalent to applying data-dependent rotary
embeddings on both the input and output projections B, C respectively. This result establishes a
theoretical connection between complex SSMs and data-dependent RoPE embeddings (Proposition
3). Finally, this allows for an efficient implementation of the complex-valued SSM via the “RoPE
trick”, enabling efficient complex-valued state transition matrix with minimal computational over-
head over real-valued SSMs.

Proposition 2 (Complex-to-Real SSM Equivalence). Consider a complex-valued SSM

˙h(t) = Diag(cid:0)A(t) + iθ(t)(cid:1) h(t) + (cid:0)B(t) + i ˆB(t)(cid:1) x(t),

(6)

y(t) = Re

(cid:16)(cid:0)C(t) + i ˆC(t)(cid:1)⊤

(cid:17)

,

h(t)

where h(t) ∈ CN/2, θ(t), B(t), ˆB(t), C(t), ˆC(t) ∈ RN/2, and x(t), A(t) ∈ R. Under Euler
discretization, this system is equivalent to a real-valued SSM

ht = e∆tAt Rt ht−1 + ∆tBtxt,
yt = C⊤

t ht,

(7)

with state ht ∈ RN , projections

Bt =

(cid:21)

(cid:20)Bt
ˆBt

∈ RN ,

Ct =

(cid:21)

(cid:20) Ct
− ˆCt

∈ RN ,

and a transition matrix
(cid:16)

Rt = Block

{R(∆tθt[i])}N/2
i=1

(cid:17)

∈ RN ×N ,

R(Θ) =

(cid:20)cos(Θ) − sin(Θ)
cos(Θ)
sin(Θ)

(cid:21)

.

The proof is in Appendix C.1.

Proposition 2 shows that the discretized complex SSM has an equivalent real SSM with doubled
state dimension (N ), and a block-diagonal transition matrix multiplied with a scalar decay, where
each 2 × 2 block is a data-dependent rotation matrix (e∆tA
t Rt). We now show that the rotations can
equivalently be absorbed into the input and output projections Bt, Ct, yielding an equivalent view
that complex SSMs are real SSMs equipped with data-dependent rotary embeddings (RoPE).

Proposition 3 (Complex SSM, Data-Dependent RoPE Equivalence). Under the notation established
in Proposition 2, consider the real SSM defined in Eq. 7 unrolled for T time-steps. The output of
the above SSM is equivalent to that of a vanilla scalar transition matrix-based SSM (Eq. 2) with a
data-dependent rotary embedding applied on the B, C components of the SSM defined as:

ht = e∆tAtht−1 + (

t
(cid:89)

i=0

R⊤

i )Btxt,

yt =

t
(cid:89)

(cid:18)
(

i=0

R⊤

i )Ct

(cid:19)⊤

ht

(8)

where the matrix production represents right matrix multiplication, e.g., (cid:81)1
denote employing the vanilla SSM to compute the Complex SSM as “RoPE trick”.

i=0 Ri = R0R1. We

The proof is in Appendix C.2.

To observe the connection of complex SSMs to RoPE embeddings, note that in the above proposi-
tion, the data-dependent rotations Ri are aggregated across time-steps and applied to C, B, which,
by the State Space Duality of Dao & Gu (2024), correspond to the Query (Q) and Key (K) compo-
nents of Attention. Analogously, vanilla RoPE (Su et al., 2023) applies data-independent rotation
matrices, where the rotation angles follow a fixed frequency schedule θ[i] = 10000−2i/N .

5

Under review as a conference paper at ICLR 2026

Remark 3 (Generality). Proposition 3 extends to the fully general case where the transition is given
by any complex matrix. By the complex diagonalization theorem, such a matrix is unitarily equiv-
alent to a complex diagonal matrix, Diag(cid:0)A(t) + iθ(t)(cid:1) with A(t) ∈ RN . However, in practice,
we restrict A(t) to a scalar, mirroring the simplification from Mamba to Mamba-2, to enable faster
implementation by avoiding GPU memory bottlenecks.

Proposition 4 (Rotary Embedding Equivalence with Trapezoidal Discretization). Discretizing a
complex SSM with the trapezoidal rule (Proposition 1) yields the recurrence
(cid:33)
(cid:32)t−1
(cid:89)

(cid:32) t
(cid:89)

(cid:33)

ht = αtht−1 + βt

R⊤
i

Bt−1xt−1 + γt

R⊤
i

Btxt,

i=0
(cid:33)⊤

R⊤

i )Ct

ht.

yt =

(cid:32)
(cid:0)

t
(cid:89)

i=0

i=0

(9)

Here Rt is the block-diagonal rotation matrix defined in Proposition 3.
The proof is in Appendix C.3.

Remark 4 (RoPE Trick). Complex SSMs discretized with the general trapezoidal rule of a complex
SSM naturally admit the RoPE trick we established for SSMs discretized with Euler’s rule.

3.3 MULTI-INPUT, MULTI-OUTPUT

During the decoding phase of autoregressive inference, outputs are generated one token at a time, and
performance is typically measured using in Tokens generated Per Second (TPS). In this metric, sub-
quadratic models, such as Mamba-2 (Dao & Gu, 2024), have a significant advantage over standard
Transformer-style attention, since they feature a fixed-size hidden state (Equation (2)) rather than
maintaining a key–value (KV) cache that grows linearly with the sequence length.

TPS, however, does not explicitly factor in hardware efficiency, where we aim to be in a compute-
bound regime (as opposed to memory-bound) in order to fully utilize on-chip accelerators. To
better characterize hardware efficiency, we would need to consider the arithmetic intensity of token
generation. Recall that arithmetic intensity is defined as FLOPs divided by the number of input-
output bytes, for a given op. In order to fully utilize both the accelerators and the bandwidth, we
would like the arithmetic intensity to match the ops:byte ratio of the hardware, which in the case
of NVIDIA H100-SXM5, is 295.2 bfloat16 ops per second with respect to the DRAM, and 31.9
bfloat16 ops per second with respect to the SRAM [Fleetwood].

Table 2(a) shows the arithmetic intensity for a single generation in the SSM component of Mamba
(with respect to 2-byte data). We see that it falls far short of a compute-bound regime, and moreover
it is not clear how one can adjust the existing parameters in Mamba to mitigate the lack of hardware
efficiency. We note that this observation applies generally to other sub-quadratic models, such as
causal linear attention.

Input

Output

FLOPs Arithmetic

yt : (p)

5pn

Intensity

5pn
2(1 + 2n + p + np)
≈ 2.5 = Θ(1)

Ht : (n, p)
xt : (p)
at : (1)
bt : (n)
ct : (n)

Input

Output

FLOPs Arithmetic

yt :
(p, r)

4nrp+
2np

Intensity

p(4nr + 2n)
2(1 + 2nr + pr + np)
≈ 2r = Θ(r)

Ht : (n, p)
xt : (p, r)
at : (1)
bt : (n, r)
ct : (n, r)

(a) SISO (2-byte data).

(b) MIMO (2-byte data).

Figure 2: Arithmetic Intensity for (a) SISO, (b) MIMO. Batch and head dimensions cancel out.

In light of this, we made the following simple adjustment to our recurrent relation: instead of trans-
forming the input xt ∈ Rp to state Ht ∈ Rn×p via an outer product, i.e., Ht ← atHt−1+bt⊗xt, we
t , where Bt ∈ Rn×r
made such a transformation via a matrix product, i.e., Ht ← atHt−1 + BtX⊤
and Xt ∈ Rp×r are now matrices with an additional rank r. The emission from state to output
similarly acquire an extra rank r, i.e., Yt ∈ Rr×p ← C⊤
t Ht, where Ct ∈ Rn×r, Ht ∈ Rn×p.
This simple change increases the arithmetic intensity of recurrence, which now scales with the rank

6

270
271

272
273
274
275
276
277

278
279
280
281
282
283

284
285
286
287
288

289
290
291
292
293
294

295
296
297
298
299
300

301
302
303
304
305
306

307
308
309
310
311

312
313
314
315
316
317

318
319
320
321
322
323

Under review as a conference paper at ICLR 2026

324
325

326
327
328
329
330
331

332
333
334
335
336
337

338
339
340
341
342

343
344
345
346
347
348

349
350
351
352
353
354

355
356
357
358
359
360

361
362
363
364
365

366
367
368
369
370
371

372
373
374
375
376
377

r (Figure 2(b)). Hence, by increasing r, arithmetic intensity improves and shifts decode generation
towards a more compute-bound regime. This increase in FLOPs during decode does not compromise
runtime, as the operation is bounded by the I/O of state Ht ∈ Rn×p.
Moreover, moving from outer-product-based state update to matrix-product-based coincides exactly
with generalizing from SISO to MIMO SSM, with the rank r being the MIMO rank. Such a gen-
eralization recovers a key expressive feature of SSMs in classical literature; indeed, there has been
previous work, namely Smith et al. (2023), that explored MIMO SSM as a drop-in replacement of
attention, albeit not in the context of Mamba and not necessarily with inference in view. We note
that training and prefilling is generally compute bound, resulting in MIMO incurring increased costs
during these stages, while decoding, a memory-bound operation, sees very little increase in latency
when utilizing MIMO over SISO.

Details of the MIMO formulation for Mamba-3 are provided in Appendix D.

3.4 MAMBA-3 ARCHITECTURE

The Mamba-3 block retains the overall layout of its predecessor while introducing several key modi-
fications. Most notably, the SSD layer is replaced with the more expressive trapezoidal SSM defined
in Proposition 4. The extra normalization layer, first introduced between Mamba-1 and Mamba-2 for
training stability, is repositioned to follow the B, C projection, mirroring the QK-Norm commonly
used in modern Transformers (Henry et al., 2020; Wortsman et al., 2023). Inspired by the findings
of Yu & Erichson (2025), which prove adding channel-specific bias to B in a blockwise variant
of Mamba-1 grants universal approximation capabilities, Mamba-3 incorporates a head-specific,
channel-wise bias into both the B and C components after its normalization. These learnable bi-
ases are data-independent parameters that are initialized to all ones and independent across B and
C (ablations for bias parameterization can be found in Appendix G). Our trapezoidal discretization
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
ablate the impact of our new discretization and BC bias on performance and show that complexifica-
tion of the SSM leads capabilities that prior SSMs such as Mamba-2 lacked in Section 4.3.

4.1 LANGUAGE MODELING

All models are pretrained with 100B tokens of the FineWeb-Edu dataset (Penedo et al., 2024) with
the Llama-3.1 tokenizer (Grattafiori et al., 2024) at a 2K context length with the same standard
training protocol. Training and evaluation details can be found in Appendix E.

Across all four model scales, Mamba-3 outperforms popular baselines at various downstream tasks
(Table 1). We highlight that Mamba-3 does not utilize the short convolution that has been empirically
identified as an important component in many performant linear models (Allen-Zhu, 2025).

4.1.1 RETRIEVAL CAPABILITIES

Beyond standard language modeling, an important measure for linear models is their retrieval ability
— how well they can recall information from earlier in the sequence (Arora et al., 2025a;b). Unlike
attention models, which can freely revisit past context with the growing KV cache, linear models
must compress context into a fixed-size state. This trade-off is reflected in the Transformer baseline’s
substantially stronger retrieval scores. To evaluate Mamba-3 under this lens, Table 2 compares it
against baselines on both real-world and synthetic needle-in-a-haystack (NIAH) tasks (Hsieh et al.,
2024), using our pretrained 1.5B models from Section 4.1. We restrict the task sequence length to
2K tokens to match the training setup and adopt the cloze-style format for our real-world tasks to
mirror the next-token-prediction objective, following Arora et al. (2025b; 2024).

Mamba-3 is competitive on real-world associative recall and question-answering but struggles when
extracting information from semi-structured or unstructured data. On synthetic NIAH tasks, how-

7

Under review as a conference paper at ICLR 2026

378
379

380
381
382
383
384
385

386
387
388
389
390
391

392
393
394
395
396

397
398
399
400
401
402

403
404
405
406
407
408

409
410
411
412
413
414

415
416
417
418
419

420
421
422
423
424
425

426
427
428
429
430
431

Table 1: Downstream language modeling evaluations on models trained with 100B FineWeb-Edu
tokens. Best results for each size are bolded, and second best are underlined. All models are trained
with the same procedure. Mamba-3 outperforms Mamba-2 and others at every model scale.

Model

FW-Edu LAMB. LAMB. HellaS. PIQA Arc-E Arc-C WinoGr. OBQA Average

Transformer-180M
Gated DeltaNet-180M
Mamba-2-180M
Mamba-3-180M (SISO)

Transformer-440M
Gated DeltaNet-440M
Mamba-2-440M
Mamba-3-440M (SISO)

Transformer-880M
Gated DeltaNet-880M
Mamba-2-880M
Mamba-3-880M (SISO)

Transformer-1.5B
Gated DeltaNet-1.5B
Mamba-2-1.5B
Mamba-3-1.5B (SISO)

ppl ↓

16.89
16.61
16.76
16.59

13.03
13.12
13.00
12.87

11.42
11.39
11.35
11.23

10.51
10.51
10.47
10.35

ppl ↓

45.0
35.9
41.8
37.7

21.2
19.0
19.6
19.6

15.0
12.7
13.8
12.9

11.1
10.8
12.0
10.9

acc ↑

32.5
33.7
30.9
32.5

41.7
40.4
40.8
40.2

44.7
47.1
45.0
47.2

50.3
49.9
47.8
49.4

acc n ↑

acc ↑

acc ↑

acc n ↑

39.0
40.2
40.1
40.8

50.5
50.5
51.7
51.7

57.2
57.5
58.1
58.8

60.6
60.5
61.4
61.9

67.1
66.8
66.8
66.1

69.9
70.5
70.6
71.9

72.6
72.6
72.5
73.6

73.8
74.3
73.6
73.6

59.8
59.6
60.1
61.5

67.6
67.5
68.8
68.9

71.6
72.5
72.3
72.7

74.0
73.3
75.3
75.9

27.9
28.5
27.3
27.9

34.6
34.0
35.0
34.4

39.2
38.8
38.7
40.2

40.4
40.4
41.8
42.7

acc ↑

51.2
51.2
52.0
52.0

56.7
55.3
54.1
55.8

57.7
57.9
56.8
58.4

58.7
61.5
57.5
59.4

acc ↑

21.8
21.6
23.2
22.8

26.0
25.8
26.0
26.0

26.8
30.6
30.2
30.0

29.6
30.4
32.6
32.0

acc ↑

42.8
43.1
42.9
43.4

49.6
49.1
49.6
49.8

52.8
53.9
53.4
54.4

55.4
55.7
55.7
56.4

Table 2: Retrieval capabilities measured by a mixture of real-world and synthetic retrieval tasks. Real-world re-
trieval tasks utilize cloze variants of the original datasets and are truncated to 2K length. Mamba-3 demonstrates
strong associative recall and question-answering but suffers with information extraction of semi-structured and
unstructured data. Mamba-3 has strong needle-in-a-haystack (NIAH) accuracy and generalizes outside its
trained context.

Model (1.5B)

SWDE SQUAD FDA TQA

NQ

Drop

NIAH-Single-1

NIAH-Single-2

NIAH-Single-3

Context Length

Transformer

Gated DeltaNet
Mamba-2
Mamba-3 (SISO)

48.9

32.7
30.7
28.5

46.6

40.0
39.1
40.1

2048

1024

2048

4096

1024

2048

4096

1024

2048

4096

58.4

67.5

31.7

26.4 100.0 100.0

0.0

92.2 100.0

0.0

98.6

99.4

0.0

28.3
23.7
23.4

25.7
63.5
64.3
25.1
64.5 26.5

49.8
24.5 100.0 100.0 99.8 100.0
62.0 100.0
28.5 100.0
11.8
99.6
27.4 100.0 100.0
88.2 100.0 95.4 50.6

93.8
53.8

83.8
68.4
95.8 87.4
81.4
92.4

34.2
13.4
34.2

ever, Mamba-3 surpasses or matches baselines on most cases and notably demonstrates markedly
better out-of-distribution retrieval abilities than its Mamba-2 predecessor.

4.2

INFERENCE EFFICIENCY

In this section, we investigate our methodological changes in the context of inference performance.
We first present our inference benchmark in Section 4.2.1; we then establish a framework for com-
paring the inference performance in Section 4.2.2. Finally, we focus on the effectiveness of MIMO
in Section 4.2.3.

4.2.1 FAST MAMBA-3 KERNELS

We complement Mamba-3’s methodological advances with optimized kernels that deliver fast infer-
ence in practical settings. Specifically, we implement a new series of inference kernels for Mamba-
3—using Triton for the forward (prefill) path and CuTe-DSL for decode—and compare their per-
token decode latency against the released Triton kernels for Mamba-2 and Gated DeltaNet (GDN)1
in Table 3. The evaluation uses the setting: a decode step at batch size 128 on a single H100 for
1.5B-parameter models with model dimension 2048, state dimension ∈ {64, 128} in both FP32 and
BF16 datatypes. Across all configurations, SISO achieves the lowest latency amongst baselines,
while MIMO incurs only a minor overhead relative to SISO. This indicates that our CuTe-DSL de-
code implementation is competitive and that the additional components of Mamba-3 (trapezoidal
update, complex-valued state, and MIMO projections) are lightweight. This supports our overall
inference-first perspective: the Mamba-3 admits simple, low-latency implementation while pro-
viding strong empirical performance. A thorough analysis, including prefill and prefill with decode
results are provided in Appendix H.

8

Under review as a conference paper at ICLR 2026

432
433

434
435
436
437
438
439

440
441
442
443
444
445

446
447
448
449
450

451
452
453
454
455
456

457
458
459
460
461
462

463
464
465
466
467
468

469
470
471
472
473

474
475
476
477
478
479

480
481
482
483
484
485

Model

FP32

BF16

dstate = 64

dstate = 128

dstate = 64

dstate = 128

Mamba-2
Gated DeltaNet
Mamba-3 (SISO)
Mamba-3 (MIMO)

0.295
0.344
0.261
0.285

0.409
0.423
0.356
0.392

0.127
0.176
0.106
0.136

0.203
0.257
0.152
0.185

Table 3: Latency (in milliseconds) compari-
son across models, precision, and dstate val-
ues. Both Mamba-3 SISO and MIMO are
faster than the Mamba-2 and Gated DeltaNet
at the commonly used bf16, dstate = 128 set-
ting.

Figure 3: Exploration of state size (inference
speed proxy) versus pretraining perplexity (per-
formance proxy) across different Mamba variants.
Mamba-3 MIMO drives the-Pareto frontier with-
out increasing state size.

4.2.2 PARETO FRONTIER FOR INFERENCE EFFICIENCY

For Mamba and many variants of sub-quadratic models, the generation of tokens during decoding is
heavily dominated by memory I/O due to the low arithmetic intensity of computing the recurrent up-
date (c.f. Section 3.3). Furthermore, among the data being transferred, the latent state Ht dominates
in terms of size. Indeed, from Table 3, we see that the runtime scales with dstate, which configures
the size of the hidden state.

As dstate dominates the decode runtime for the subquadratic models considered in this paper, we
opt to use it as a proxy for inference speed. By plotting the validation perplexity (itself a proxy
for model performance) as a function of dstate, we aim to formulate a holistic picture about how the
subquadratic models can trade off performance with inference speed.

Figure 3 shows such a Pareto front for the Mamba variants models considered in this paper. For each
data point, we train a 440M parameter model to 2× Chinchilla optimal tokens on the Fineweb-Edu
dataset, where the model is configured with a dstate of {16, 32, 64, 128}. As expected, we observe
an inverse correlation between validation loss and dstate; moreover, we noticed a general downward
shift on the Pareto front moving from Mamba-2 to Mamba-3. A further downward shift is observed
when moving from the SISO variant of Mamba-3 to the MIMO variant of Mamba-3 (where we set
the Mimo rank r = 4 and decrease our MLP inner dimension to parameter match the SISO variants).
We expand the comparison to include the Gated DeltaNet baseline in Figure 7. The results highlight
both the expressivity gain coming our methodology change as well as the effectiveness of the MIMO
mechanism in improving decoding efficiency.

4.2.3 MIMO ENHANCES INFERENCE EFFICIENCY

MIMO, with its higher arithmetic intensity, increases the decoding FLOPs without significantly
increasing decode runtime (Table 3)2 The implication is that any performance gain from MIMO
translates into efficiency gain in decoding: a conclusion supported by the downward shift of the
MIMO pareto curve we observed in Section 4.2.2.

We aim to further verify the gain from MIMO by investigating its language-modeling capabilities.
To that end, we train a 440M and 820M parameter MIMO models with MIMO rank r = 4 on 100B
tokens on Fineweb-Edu (i.e., same setting as the 440M parameter run in Section 4.1; we are currently
training the 1.5B model). To ensure the total parameter count equals SISO, we decrease the inner
dimension of the MLP layers to compensate for the increase due to the MIMO projections.

On both validation perplexity and our suite of language evaluation tasks (Table 6), we see significant
gain when moving from SISO to MIMO. Namely, we attain a perplexity gain of 0.16 on the 100B
tokens run, and Figure 3 illustrates the downward shift in our validation loss. On the language
evaluation front, we see significant gain on most tasks when compared to SISO, resulting in an
overall gain of 1.2 point over SISO. This strongly supports MIMO as a SSM-centric technique to
improve model quality without compromising decoding speed.

1Details on each kernel DSL and the exact kernel fusion structure is provided in Appendix H.
2The kernel for MIMO Mamba-3 in fact fuses the MIMO projection, and so the reported wall clock time is

actually an overestimate for the pure SSM update.

9

105Relative Total State Size14.614.815.015.2Pretraining PerplexityRelative Total State Size vs Pretraining PerplexityMamba-2Mamba-3 Mamba-3 MIMOUnder review as a conference paper at ICLR 2026

Table 4: Left: Ablations on core modeling components of Mamba-3, results on test split of dataset. A
combination of our BC bias and trapezoidal discretization makes the convolution optional. Right: Formal
language evaluation (scaled accuracy, %). Higher is better. Models are trained on short sequences and evaluated
on longer lengths to test length generalization. For Gated DeltaNet we report the variant with eigenvalue range
[−1, 1].

Model Variant (SISO)

Mamba-3 − bias − trap
Mamba-3 − bias
Mamba-3
Mamba-3 + conv

ppl ↓

16.68
16.49
15.72
15.85

(a) Component ablation (350M).

Model

Parity ↑

Arith. w/o ↑
brackets

Arith. w/ ↑
brackets

100.00
2.27
1.56
0.90
100.00

Mamba-3
Mamba-3 (w/o RoPE)
Mamba-3 (w/ Std. RoPE)
Mamba-2
Gated DeltaNet [-1,1]
(b) Performance comparison on formal language tasks. Re-
sults show that unlike Mamba-2, Mamba-3 features state
tracking ability stemming from data-dependent RoPE em-
beddings. We used Mamba-3 (SISO) for these ablations.

98.51
1.49
20.70
47.81
99.25

87.75
0.72
2.62
0.88
93.50

4.3 SSM-CENTRIC METHODOLOGICAL ABLATIONS

Table 4a ablates the changes made to the core SSM component, mainly the introduction of BC bias
and trapezoidal discretization. We report the pretraining test perplexity on models at the 440M scale,
trained for Chinchilla optimal tokens. We find that the bias and trapezoidal SSM synergize well and
make the short convolution utilized by many current linear models redundant.

We empirically demonstrate that data-dependent RoPE in Mamba-3 enables state tracking. Follow-
ing Grazzi et al. (2025), we evaluate on tasks from the Chomsky hierarchy—Parity, Modular Arith-
metic (without brackets), and Modular Arithmetic (with brackets)—and report scaled accuracies in
Table 4b. Mamba-3 solves Parity and Modular Arithmetic (without brackets), and nearly closes the
accuracy gap on Modular Arithmetic (with brackets). In contrast, Mamba-3 without RoPE, Mamba-
3 with standard RoPE (Su et al., 2023), and Mamba-2 fail to learn these tasks. We use the state-
tracking–enabled Gated DeltaNet variant of and observe that Mamba-3 is competitive—matching
parity and approaching its performance on both modular-arithmetic tasks. Experimental settings are
covered in Appendix E.

5 CONCLUSION AND FUTURE WORK
We introduce Mamba-3, an SSM model with three axes of improvement rooted in SSM princi-
ples: (i) improved quality, via trapezoidal discretization; (ii) new capabilities, through complex
SSMs that recover state-tracking; and (iii) higher inference efficiency, with a MIMO formulation
that raises arithmetic intensity. Mamba-3 delivers strong language modeling results and establishes
a new Pareto frontier on the performance-efficiency axes with respect to strong baseline models. A
limitation remains in retrieval, where fixed-state architectures lags attention-based models. We see
hybrid Mamba-3 architectures that integrate retrieval mechanisms as a promising path, alongside
broader application of our design principles to linear-time sequence models.

10

486
487

488
489
490
491
492
493

494
495
496
497
498
499

500
501
502
503
504

505
506
507
508
509
510

511
512
513
514
515
516

517
518
519
520
521
522

523
524
525
526
527

528
529
530
531
532
533

534
535
536
537
538
539

Under review as a conference paper at ICLR 2026

540
541

542
543
544
545
546
547

548
549
550
551
552
553

554
555
556
557
558

559
560
561
562
563
564

565
566
567
568
569
570

571
572
573
574
575
576

577
578
579
580
581

582
583
584
585
586
587

588
589
590
591
592
593

REFERENCES
Zeyuan Allen-Zhu. Physics of Language Models: Part 4.1, Architecture Design and the Magic
of Canon Layers. SSRN Electronic Journal, May 2025. https://ssrn.com/abstract=
5240330.

Aryaman Arora, Neil Rathi, Nikil Roashan Selvam, R´obert Csord´as, Dan Jurafsky, and Christopher
Potts. Mechanistic evaluation of transformers and state space models, 2025a. URL https:
//arxiv.org/abs/2505.15105.

Simran Arora, Aman Timalsina, Aaryan Singhal, Benjamin Spector, Sabri Eyuboglu, Xinyi Zhao,
Ashish Rao, Atri Rudra, and Christopher R´e. Just read twice: closing the recall gap for recurrent
language models, 2024. URL https://arxiv.org/abs/2407.05483.

Simran Arora, Sabri Eyuboglu, Michael Zhang, Aman Timalsina, Silas Alberti, Dylan Zinsley,
James Zou, Atri Rudra, and Christopher R´e. Simple linear attention language models balance
the recall-throughput tradeoff, 2025b. URL https://arxiv.org/abs/2402.18668.

Aviv Bick, Kevin Y. Li, Eric P. Xing, J. Zico Kolter, and Albert Gu. Transformers to ssms: Distill-
ing quadratic knowledge to subquadratic models, 2025a. URL https://arxiv.org/abs/
2408.10189.

Aviv Bick, Eric Xing, and Albert Gu. Understanding the skill gap in recurrent language models:
The role of the gather-and-aggregate mechanism, 2025b. URL https://arxiv.org/abs/
2504.18574.

Yonatan Bisk, Rowan Zellers, Ronan Le Bras, Jianfeng Gao, and Yejin Choi. Piqa: Reasoning about
physical commonsense in natural language, 2019. URL https://arxiv.org/abs/1911.
11641.

Krzysztof Choromanski, Valerii Likhosherstov, David Dohan, Xingyou Song, Andreea Gane, Tamas
Sarlos, Peter Hawkins, Jared Davis, Afroz Mohiuddin, Lukasz Kaiser, David Belanger, Lucy
Colwell, and Adrian Weller. Rethinking attention with performers, 2022. URL https://
arxiv.org/abs/2009.14794.

Peter Clark, Isaac Cowhey, Oren Etzioni, Tushar Khot, Ashish Sabharwal, Carissa Schoenick, and
Oyvind Tafjord. Think you have solved question answering? try arc, the ai2 reasoning challenge,
2018. URL https://arxiv.org/abs/1803.05457.

Tri Dao and Albert Gu. Transformers are ssms: Generalized models and efficient algorithms through

structured state space duality, 2024. URL https://arxiv.org/abs/2405.21060.

Dheeru Dua, Yizhong Wang, Pradeep Dasigi, Gabriel Stanovsky, Sameer Singh, and Matt Gardner.
Drop: A reading comprehension benchmark requiring discrete reasoning over paragraphs, 2019.
URL https://arxiv.org/abs/1903.00161.

Christopher Fleetwood. Domain specific architectures for ai inference. URL https://

fleetwood.dev/posts/domain-specific-architectures.

Leo Gao, Jonathan Tow, Baber Abbasi, Stella Biderman, Sid Black, Anthony DiPofi, Charles Fos-
ter, Laurence Golding, Jeffrey Hsu, Alain Le Noac’h, Haonan Li, Kyle McDonell, Niklas Muen-
nighoff, Chris Ociepa, Jason Phang, Laria Reynolds, Hailey Schoelkopf, Aviya Skowron, Lintang
Sutawika, Eric Tang, Anish Thite, Ben Wang, Kevin Wang, and Andy Zou. The language model
evaluation harness, 07 2024. URL https://zenodo.org/records/12608602.

Madan Gopal. Modern control system theory. New Age International, 1993.

Aaron Grattafiori, Abhimanyu Dubey, Abhinav Jauhri, Abhinav Pandey, Abhishek Kadian, Ahmad
Al-Dahle, Aiesha Letman, Akhil Mathur, Alan Schelten, Alex Vaughan, Amy Yang, Angela Fan,
Anirudh Goyal, Anthony Hartshorn, Aobo Yang, Archi Mitra, Archie Sravankumar, Artem Ko-
renev, Arthur Hinsvark, Arun Rao, Aston Zhang, and et. al. The llama 3 herd of models, 2024.
URL https://arxiv.org/abs/2407.21783.

11

Under review as a conference paper at ICLR 2026

594
595

596
597
598
599
600
601

602
603
604
605
606
607

608
609
610
611
612

613
614
615
616
617
618

619
620
621
622
623
624

625
626
627
628
629
630

631
632
633
634
635

636
637
638
639
640
641

642
643
644
645
646
647

Riccardo Grazzi, Julien Siems, Simon Schrodi, Thomas Brox, and Frank Hutter. Is mamba capable

of in-context learning?, 2024. URL https://arxiv.org/abs/2402.03170.

Riccardo Grazzi, Julien Siems, Arber Zela, J¨org K. H. Franke, Frank Hutter, and Massimiliano
Pontil. Unlocking state-tracking in linear rnns through negative eigenvalues, 2025. URL https:
//arxiv.org/abs/2411.12537.

Albert Gu and Tri Dao. Mamba: Linear-time sequence modeling with selective state spaces, 2024.

URL https://arxiv.org/abs/2312.00752.

Albert Gu, Karan Goel, and Christopher R´e. Efficiently modeling long sequences with structured

state spaces, 2022a. URL https://arxiv.org/abs/2111.00396.

Albert Gu, Ankit Gupta, Karan Goel, and Christopher R´e. On the parameterization and initialization
of diagonal state space models. arXiv preprint arXiv:2206.11893, 2022b. URL https://
arxiv.org/abs/2206.11893.

Ankit Gupta, Albert Gu, and Jonathan Berant. Diagonal state spaces are as effective as structured

state spaces, 2022. URL https://arxiv.org/abs/2203.14343.

Alex Henry, Prudhvi Raj Dachapally, Shubham Pawar, and Yuxuan Chen. Query-key normalization

for transformers, 2020. URL https://arxiv.org/abs/2010.04245.

Cheng-Ping Hsieh, Simeng Sun, Samuel Kriman, Shantanu Acharya, Dima Rekesh, Fei Jia, Yang
Zhang, and Boris Ginsburg. Ruler: What’s the real context size of your long-context language
models?, 2024. URL https://arxiv.org/abs/2404.06654.

Samy Jelassi, David Brandfonbrener, Sham M. Kakade, and Eran Malach. Repeat after me: Trans-
formers are better than state space models at copying, 2024. URL https://arxiv.org/
abs/2402.01032.

Mandar Joshi, Eunsol Choi, Daniel S. Weld, and Luke Zettlemoyer. Triviaqa: A large scale distantly
supervised challenge dataset for reading comprehension, 2017. URL https://arxiv.org/
abs/1705.03551.

Rudolph Emil Kalman. A new approach to linear filtering and prediction problems. 1960.

Angelos Katharopoulos, Apoorv Vyas, Nikolaos Pappas, and Franc¸ois Fleuret. Transformers are
rnns: Fast autoregressive transformers with linear attention, 2020. URL https://arxiv.
org/abs/2006.16236.

Tom Kwiatkowski, Jennimaria Palomaki, Olivia Redfield, Michael Collins, Ankur Parikh, Chris
Alberti, Danielle Epstein, Illia Polosukhin, Jacob Devlin, Kenton Lee, Kristina Toutanova, Llion
Jones, Matthew Kelcey, Ming-Wei Chang, Andrew M. Dai, Jakob Uszkoreit, Quoc Le, and Slav
Petrov. Natural questions: A benchmark for question answering research. Transactions of the
Association for Computational Linguistics, 7:452–466, 2019. doi: 10.1162/tacl a 00276. URL
https://aclanthology.org/Q19-1026/.

Woosuk Kwon, Zhuohan Li, Siyuan Zhuang, Ying Sheng, Lianmin Zheng, Cody Hao Yu, Joseph E.
Gonzalez, Hao Zhang, and Ion Stoica. Efficient memory management for large language model
serving with pagedattention, 2023. URL https://arxiv.org/abs/2309.06180.

Baolin Li, Yankai Jiang, Vijay Gadepally, and Devesh Tiwari. Llm inference serving: Survey of
recent advances and opportunities, 2024. URL https://arxiv.org/abs/2407.12391.

William Merrill, Jackson Petty, and Ashish Sabharwal. The illusion of state in state-space models,

2025. URL https://arxiv.org/abs/2404.08819.

Todor Mihaylov, Peter Clark, Tushar Khot, and Ashish Sabharwal. Can a suit of armor conduct
electricity? a new dataset for open book question answering, 2018. URL https://arxiv.
org/abs/1809.02789.

12

Under review as a conference paper at ICLR 2026

648
649

650
651
652
653
654
655

656
657
658
659
660
661

662
663
664
665
666

667
668
669
670
671
672

673
674
675
676
677
678

679
680
681
682
683
684

685
686
687
688
689

690
691
692
693
694
695

696
697
698
699
700
701

Team OLMo, Pete Walsh, Luca Soldaini, Dirk Groeneveld, Kyle Lo, Shane Arora, Akshita Bhagia,
Yuling Gu, Shengyi Huang, Matt Jordan, Nathan Lambert, Dustin Schwenk, Oyvind Tafjord,
Taira Anderson, David Atkinson, Faeze Brahman, Christopher Clark, Pradeep Dasigi, Nouha
Dziri, Michal Guerquin, and et. al. 2 olmo 2 furious, 2025. URL https://arxiv.org/
abs/2501.00656.

Antonio Orvieto, Samuel L Smith, Albert Gu, Anushan Fernando, Caglar Gulcehre, Razvan Pas-
canu, and Soham De. Resurrecting recurrent neural networks for long sequences, 2023. URL
https://arxiv.org/abs/2303.06349.

Daniele Paliotta, Junxiong Wang, Matteo Pagliardini, Kevin Y. Li, Aviv Bick, J. Zico Kolter, Albert
Gu, Franc¸ois Fleuret, and Tri Dao. Thinking slow, fast: Scaling inference compute with distilled
reasoners, 2025. URL https://arxiv.org/abs/2502.20339.

Denis Paperno, Germ´an Kruszewski, Angeliki Lazaridou, Quan Ngoc Pham, Raffaella Bernardi,
Sandro Pezzelle, Marco Baroni, Gemma Boleda, and Raquel Fern´andez. The lambada dataset:
Word prediction requiring a broad discourse context, 2016. URL https://arxiv.org/
abs/1606.06031.

Jongho Park, Jaeseung Park, Zheyang Xiong, Nayoung Lee, Jaewoong Cho, Samet Oymak, Kang-
wook Lee, and Dimitris Papailiopoulos. Can mamba learn how to learn? a comparative study on
in-context learning tasks, 2024. URL https://arxiv.org/abs/2402.04248.

Guilherme Penedo, Hynek Kydl´ıˇcek, Loubna Ben allal, Anton Lozhkov, Margaret Mitchell, Colin
Raffel, Leandro Von Werra, and Thomas Wolf. The fineweb datasets: Decanting the web for the
finest text data at scale, 2024. URL https://arxiv.org/abs/2406.17557.

Bo Peng, Ruichong Zhang, Daniel Goldstein, Eric Alcaide, Xingjian Du, Haowen Hou, Jiaju Lin,
Jiaxing Liu, Janna Lu, William Merrill, Guangyu Song, Kaifeng Tan, Saiteja Utpala, Nathan
Wilce, Johan S. Wind, Tianyi Wu, Daniel Wuttke, and Christian Zhou-Zheng. Rwkv-7 ”goose”
with expressive dynamic state evolution, 2025. URL https://arxiv.org/abs/2503.
14456.

Pranav Rajpurkar, Jian Zhang, and Percy Liang. Know what you don’t know: Unanswerable ques-

tions for squad. In ACL 2018, 2018.

Yuval Ran-Milo, Eden Lumbroso, Edo Cohen-Karlik, Raja Giryes, Amir Globerson, and Nadav
Cohen. Provable benefits of complex parameterizations for structured state space models, 2024.
URL https://arxiv.org/abs/2410.14067.

Keisuke Sakaguchi, Ronan Le Bras, Chandra Bhagavatula, and Yejin Choi. Winogrande: An adver-
sarial winograd schema challenge at scale, 2019. URL https://arxiv.org/abs/1907.
10641.

Yash Sarrof, Yana Veitsman, and Michael Hahn. The expressive capacity of state space models: A

formal language perspective, 2024. URL https://arxiv.org/abs/2405.17394.

Imanol Schlag, Kazuki Irie, and J¨urgen Schmidhuber. Linear transformers are secretly fast weight

programmers, 2021. URL https://arxiv.org/abs/2102.11174.

Julien Siems, Timur Carstensen, Arber Zela, Frank Hutter, Massimiliano Pontil, and Riccardo
Grazzi. Deltaproduct: Improving state-tracking in linear rnns via householder products, 2025.
URL https://arxiv.org/abs/2502.10297.

Jimmy T. H. Smith, Andrew Warrington, and Scott W. Linderman. Simplified state space layers for

sequence modeling, 2023. URL https://arxiv.org/abs/2208.04933.

Charlie Snell, Jaehoon Lee, Kelvin Xu, and Aviral Kumar. Scaling llm test-time compute optimally
can be more effective than scaling model parameters, 2024. URL https://arxiv.org/
abs/2408.03314.

Jianlin Su, Yu Lu, Shengfeng Pan, Ahmed Murtadha, Bo Wen, and Yunfeng Liu. Roformer: En-
hanced transformer with rotary position embedding, 2023. URL https://arxiv.org/abs/
2104.09864.

13

Under review as a conference paper at ICLR 2026

Yutao Sun, Li Dong, Shaohan Huang, Shuming Ma, Yuqing Xia, Jilong Xue, Jianyong Wang, and
Furu Wei. Retentive network: A successor to transformer for large language models, 2023. URL
https://arxiv.org/abs/2307.08621.

Endre S¨uli and David F. Mayers. An Introduction to Numerical Analysis. Cambridge University

Press, 2003.

Gemma Team, Aishwarya Kamath, Johan Ferret, Shreya Pathak, Nino Vieillard, Ramona Merhej,
Sarah Perrin, Tatiana Matejovicova, Alexandre Ram´e, Morgane Rivi`ere, Louis Rouillard, Thomas
Mesnard, Geoffrey Cideron, Jean bastien Grill, Sabela Ramos, Edouard Yvinec, Michelle Casbon,
Etienne Pot, Ivo Penchev, Ga¨el Liu, and et. al. Gemma 3 technical report, 2025. URL https:
//arxiv.org/abs/2503.19786.

M. Tenenbaum and H. Pollard. Ordinary Differential Equations: An Elementary Textbook for Stu-
dents of Mathematics, Engineering, and the Sciences. Dover Books on Mathematics. Dover Pub-
lications, 1985. ISBN 9780486649405. URL https://books.google.com/books?id=
iU4zDAAAQBAJ.

Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N Gomez,
Łukasz Kaiser, and Illia Polosukhin. Attention is all you need. In Advances in neural information
processing systems, pp. 5998–6008, 2017. URL http://arxiv.org/abs/1706.03762.

Johannes von Oswald, Nino Scherrer, Seijin Kobayashi, Luca Versari, Songlin Yang, Maximil-
ian Schlegel, Kaitlin Maile, Yanick Schimpf, Oliver Sieberling, Alexander Meulemans, Rif A.
Saurous, Guillaume Lajoie, Charlotte Frenkel, Razvan Pascanu, Blaise Ag¨uera y Arcas, and Jo˜ao
Sacramento. Mesanet: Sequence modeling by locally optimal test-time training, 2025. URL
https://arxiv.org/abs/2506.05233.

Mitchell Wortsman, Peter J. Liu, Lechao Xiao, Katie Everett, Alex Alemi, Ben Adlam, John D. Co-
Reyes, Izzeddin Gur, Abhishek Kumar, Roman Novak, Jeffrey Pennington, Jascha Sohl-dickstein,
Kelvin Xu, Jaehoon Lee, Justin Gilmer, and Simon Kornblith. Small-scale proxies for large-scale
transformer training instabilities, 2023. URL https://arxiv.org/abs/2309.14322.

Yangzhen Wu, Zhiqing Sun, Shanda Li, Sean Welleck, and Yiming Yang. Inference scaling laws:
An empirical analysis of compute-optimal inference for problem-solving with language models,
2025. URL https://arxiv.org/abs/2408.00724.

Songlin Yang, Jan Kautz, and Ali Hatamizadeh. Gated delta networks: Improving mamba2 with

delta rule, 2025a. URL https://arxiv.org/abs/2412.06464.

Songlin Yang, Bailin Wang, Yu Zhang, Yikang Shen, and Yoon Kim. Parallelizing linear trans-
formers with the delta rule over sequence length, 2025b. URL https://arxiv.org/abs/
2406.06484.

Annan Yu and N. Benjamin Erichson. Block-biased mamba for long-range sequence processing,

2025. URL https://arxiv.org/abs/2505.09022.

Rowan Zellers, Ari Holtzman, Yonatan Bisk, Ali Farhadi, and Yejin Choi. Hellaswag: Can a ma-
chine really finish your sentence?, 2019. URL https://arxiv.org/abs/1905.07830.

14

702
703

704
705
706
707
708
709

710
711
712
713
714
715

716
717
718
719
720

721
722
723
724
725
726

727
728
729
730
731
732

733
734
735
736
737
738

739
740
741
742
743

744
745
746
747
748
749

750
751
752
753
754
755

Under review as a conference paper at ICLR 2026

756
757

758
759
760
761
762
763

764
765
766
767
768
769

770
771
772
773
774

775
776
777
778
779
780

781
782
783
784
785
786

787
788
789
790
791
792

793
794
795
796
797

798
799
800
801
802
803

804
805
806
807
808
809

LLM Usage. We utilized Large Language Models to polish the writing in our submission as well as
generate latex code for formatting tables and figures.

A RELATED WORK
Linear-time sequence mixers. State-space models (SSMs) provide linear-time sequence mixing
through explicit dynamical states and efficient scan/convolution implementations, offering signifi-
cant computational advantages over quadratic-time attention mechanisms (Gu et al., 2022a; Smith
et al., 2023; Gupta et al., 2022). Mamba-1 (Gu & Dao, 2024) introduced input-dependent selectivity
to SSMs, while Mamba-2 (Dao & Gu, 2024) formalized the connection between SSMs and attention
via structured state-space duality (SSD) (Katharopoulos et al., 2020; Choromanski et al., 2022). De-
spite matching transformers on standard language understanding benchmarks, these recurrent mod-
els exhibit limitations on tasks requiring precise algorithmic reasoning. Recent evaluations identified
gaps in capabilities such as associative retrieval (Bick et al., 2025b; Arora et al., 2025a), exact copy-
ing (Jelassi et al., 2024), and in-context learning (Park et al., 2024; Grazzi et al., 2024). To address
these limitations, DeltaNet enhances linear attention by replacing additive updates with delta-rule
recurrence (Schlag et al., 2021), with recent work developing hardware-efficient, sequence-parallel
training algorithms for this architecture (Yang et al., 2025b). This has catalyzed a broader effort
to improve the algorithmic capabilities of linear-time models through architectural innovations in-
cluding gating mechanisms, improved state transition dynamics, and hybrid approaches (Peng et al.,
2025; Siems et al., 2025; Yang et al., 2025a; Paliotta et al., 2025; Bick et al., 2025a).

Expressivity and state tracking in recurrent mixers. Recent work characterizes the types of
state that recurrent, constant-memory mixers can maintain, revealing algorithmic deficiencies in
previous SSM-based models. Merrill et al. (2025) show that under finite precision, practical SSMs
collapse to TC0, leading to failures on tasks like permutation composition over S5 unless the primi-
tive is extended. Similarly, Yu & Erichson (2025) prove that a single-layer Mamba is not a universal
approximator. Several modifications have been proposed to improve expressivity. For instance,
the same work shows that a block-biased variant regains the universal approximation property with
only minor changes, either through block decomposition or a channel-specific bias. Allowing nega-
tive eigenvalues or non-triangular transitions enables linear RNNs—including diagonal and House-
holder/DeltaNet forms—to capture parity and, under mild assumptions, regular languages (Grazzi
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
keys in attention. The resulting data-dependent rotational structure expands stable dynamics to in-
clude oscillatory modes, enabling richer states while maintaining constant memory and linear-time
complexity.

B TRAPEZOIDAL DISCRETIZATION
Proposition 5 (Variation of Constants (Tenenbaum & Pollard, 1985)). Consider the linear SSM

˙h(t) = A(t) h(t) + B(t) x(t),
where h(t) ∈ RN , A(t) ∈ R is a scalar decay, and B(t)x(t) ∈ RN . For ∆t discretized time grid
τt = τt−1 + ∆t, the hidden state satisfies

ht ≈ e∆tAt ht−1 +

(cid:90) τt

τt−1

e(τt−τ )At B(τ )x(τ ) dτ.

(10)

Proof. Since A(t) is scalar, the homogeneous system ˙h(t) = A(t)h(t) has solution

h(t) = ϕ(t, s) h(s),

(cid:18)(cid:90) t

ϕ(t, s) = exp

(cid:19)

A(ξ) dξ

.

s

15

Under review as a conference paper at ICLR 2026

The Variation of Constants formula gives us,

h(t) = ϕ(t, s) h(s) +

(cid:90) t

s

ϕ(t, τ ) B(τ )x(τ ) dτ.

Setting (s, t) = (tk−1, tk) yields the exact ht given ht−1. We approximate (cid:82) t
A(τ ) ≈ Ak over [tk−1, tk], which gives us,

s A(ξ) dξ by setting

ϕ(tk, tk−1) = exp

(cid:19)

A(ξ) dξ

≈ exp

(cid:18)(cid:90) t

s

(cid:18)(cid:90) t

(cid:19)

Ak dξ

s

= e∆kAk ,

Substituting these approximations in the Variation of Constants integral, we get the approximation
(cid:90) τt

ht ≈ e∆tAt ht−1 +

e(τt−τ )At B(τ )x(τ ) dτ.

τt−1

B.1 TRAPEZOID DISCRETIZATION’S MASK MATRIX
Proof. When viewing the tensor contraction form, let us call C = (T, N ), B = (S, N ), L =
(T, S), X = (S, P ) based on the Mamba-2 paper. With this decomposition of our mask, we can
view L = contract(T Z, ZS → T S)(L1, L2).
The original contraction can be seen as

contract(T N, SN, T S, SP → T P )(C, B, L, X)

We can now view it as

contract(T N, SN, T J, JS, SP → T P )(C, B, L1, L2, X)

This can be broken into the following:

Z = contract(SN, SP → SN P )(B, X)
Z ′ = contract(JS, SN P → JN P )(L2, Z)
H = contract(T J, JN P → T N P )(L1, Z ′)
Y = contract(T N, T N P → T P )(C, H)
Thus, we can view this step: contract(ZS, SN P → ZN P )(L2, Z) as a conv of size two applied on
Bx with the traditional SSD L = L1 matrix.

B.2 TRAPEZOIDAL DISCRETIZATION ERROR RATE
Standard assumptions. We assume that: A(t), B(t), x(t) are bounded and C 2 on each timestep,
so that g(τ ) has two bounded derivatives; the map h (cid:55)→ A(t)h + B(t)x(t) is Lipschitz in h which
is true for linear systems; λt lies in a bounded interval so that the update is zero-stable.

Proof. Let g(τ ) := e(tk−τ )Ak B(τ )x(τ ) denote the integrand in the second term of Proposition 5.
Since A(t), B(t), x(t) are C 2 on [tk−1, tk], the function g has two bounded derivatives. A second-
order Taylor expansion of g around tk−1 gives us,
∆2
t
2

g(τ ) dτ = ∆t g(tk−1) +

g′′(tk−1) + O(∆4

g′(tk−1) +

∆3
t
6

(cid:90) tk

t ).

tk−1

Recall that the trapezoidal approximation to this integral is given by,
(cid:105)
(cid:104)
(1 − λt) g(tk−1) + λt g(tk)

Qλ = ∆t

.

Expanding g(tk) using Taylor expansion: g(tk) = g(tk−1) + ∆tg′(tk−1) + ∆2
Substituting this into Qλ,

t

2 g′′(tk−1) + O(∆3
t ).

Qλ = ∆t

(cid:104)
(1 − λt)g(tk−1) + λtg(tk)

(cid:105)

= ∆tg(tk−1) + λt∆2

t g′(tk−1) + λt

∆3
t
2

g′′(tk−1) + O(∆4

t ).

16

810
811

812
813
814
815
816
817

818
819
820
821
822
823

824
825
826
827
828

829
830
831
832
833
834

835
836
837
838
839
840

841
842
843
844
845
846

847
848
849
850
851

852
853
854
855
856
857

858
859
860
861
862
863

Under review as a conference paper at ICLR 2026

Hence, the error is given by:

(cid:90) tk

tk−1

g(τ ) dτ − Qλ =

(cid:16) 1

2 − λt

(cid:17)

∆2

t g′(tk−1) +

(cid:16) 1
6 − λt

2

(cid:17)

∆3

t g′′(tk−1) + O(∆4

t ).

Under the assumption that λt = 1
t term is O(∆3
thus the ∆2

t ). Therefore,
(cid:90) tk

2 + ct∆t, where ct = O(1), then 1

2 − λt = −ct∆t = O(∆t) and

g(τ ) dτ − Qλ = O(∆3

t ),

tk−1

which yields an O(∆3
and zero–stable for bounded λt, standard numerical ODE results imply an O(∆2

t ) local truncation error. Since the update hk = e∆tAk hk−1 + Qλ is linear

t ) global error.

B.3 TRAPEZOIDAL PARAMETERIZATION

Parameterization

Form of λt

ppl ↓

Default

Fixed 1/2

No trapezoid (Euler)

σ(ut)

1
2
1

15.72

15.76

15.81

Table 5: Ablations on λt parameterization in the trapezoidal update.

Setting: All runs use the Mamba-3 (SISO) 440M model trained at Chinchilla scale, with the other
architectural and optimization hyperparameters being the same as in Table 1.

The default model uses a data-dependent gate λt = σ(ut), where ut is a learned projection of the
current input token. In Table 5, we try different parameterizations for λt and find that the default pa-
rameterization empirically performs the best. Hence we choose the simpler default parameterization
that does not enforce the O( 1

2 + ∆t).
C COMPLEX SSM PROOFS

C.1 PROOF OF PROPOSITION 2
Proposition 2 (Complex-to-Real SSM Equivalence). Consider a complex-valued SSM

˙h(t) = Diag(cid:0)A(t) + iθ(t)(cid:1) h(t) + (cid:0)B(t) + i ˆB(t)(cid:1) x(t),

(6)

y(t) = Re

(cid:16)(cid:0)C(t) + i ˆC(t)(cid:1)⊤

(cid:17)

,

h(t)

where h(t) ∈ CN/2, θ(t), B(t), ˆB(t), C(t), ˆC(t) ∈ RN/2, and x(t), A(t) ∈ R. Under Euler
discretization, this system is equivalent to a real-valued SSM

ht = e∆tAt Rt ht−1 + ∆tBtxt,
yt = C⊤

t ht,

(7)

with state ht ∈ RN , projections

Bt =

(cid:21)

(cid:20)Bt
ˆBt

∈ RN ,

Ct =

(cid:21)

(cid:20) Ct
− ˆCt

∈ RN ,

and a transition matrix
(cid:16)

Rt = Block

{R(∆tθt[i])}N/2
i=1

(cid:17)

∈ RN ×N ,

R(Θ) =

(cid:20)cos(Θ) − sin(Θ)
cos(Θ)
sin(Θ)

(cid:21)

.

Proof. We first present the derivation for N = 2; the block-diagonal structure for general even N
follows by grouping pairs of coordinates.
Let ht +iˆht denote the complexified hidden state, with parameters A(t)+iθ(t) and B(t)+i ˆB(t) for
the transition and input, respectively. By the variation of constants formula (Proposition 5), applying
zero–order hold and Euler’s rule over a step [tk−1, tk] gives

hk + iˆhk = e∆t(At+iθt)(hk−1 + iˆhk−1) + ∆t(Bt + i ˆBt)xt.

17

864
865

866
867
868
869
870
871

872
873
874
875
876
877

878
879
880
881
882

883
884
885
886
887
888

889
890
891
892
893
894

895
896
897
898
899
900

901
902
903
904
905

906
907
908
909
910
911

912
913
914
915
916
917

Under review as a conference paper at ICLR 2026

Expanding the exponential,

e∆t(At+iθt) = e∆tAt

(cid:16)

cos(∆tθt) + i sin(∆tθt)

(cid:17)

,

so in real coordinates ht =

(cid:21)

(cid:20)ht
ˆht

∈ R2 the recurrence becomes

ht = e∆tAt

(cid:21)
(cid:20)cos(∆tθt) − sin(∆tθt)
cos(∆tθt)
sin(∆tθt)

(cid:124)

(cid:123)(cid:122)
R(∆tθt)

(cid:125)

ht−1 + ∆t

(cid:21)

(cid:20)Bt
ˆBt

xt.

Stacking across N/2 such pairs yields the block-diagonal transition

ht = e∆tAt Block(cid:0){R(∆tθt[i])}N/2

i=1

(cid:1)ht−1 + ∆t

(cid:21)

(cid:20)Bt
ˆBt

xt.

For the output,

(cid:16)
yt = Re

(cid:17)
(Ct + i ˆCt)⊤(ht + iˆht)

=

(cid:21)⊤

(cid:20) Ct
− ˆCt

ht,

which defines the real projection Ct ∈ RN in the proposition. This proves the equivalence between
complex SSM and the real block-diagonal system with rotations.

C.2 PROOF OF PROPOSITION 3
Proposition 3 (Complex SSM, Data-Dependent RoPE Equivalence). Under the notation established
in Proposition 2, consider the real SSM defined in Eq. 7 unrolled for T time-steps. The output of
the above SSM is equivalent to that of a vanilla scalar transition matrix-based SSM (Eq. 2) with a
data-dependent rotary embedding applied on the B, C components of the SSM defined as:

ht = e∆tAtht−1 + (

t
(cid:89)

i=0

R⊤

i )Btxt,

yt =

t
(cid:89)

(cid:18)
(

i=0

R⊤

i )Ct

(cid:19)⊤

ht

(8)

where the matrix production represents right matrix multiplication, e.g., (cid:81)1
denote employing the vanilla SSM to compute the Complex SSM as “RoPE trick”.

i=0 Ri = R0R1. We

Proof. Consider the SSM

ht = e∆tAt Rt ht−1 + Btxt,

yt = C⊤

t ht,

(11)

where (as in Proposition 3) At ∈ R is a scalar (so that e∆tAt is a scalar and commutes with rota-
tions), and Rt is block-diagonal orthogonal/unitary, hence R−1
Unrolling the recurrence with the convention that an empty product is the identity,

t = R⊤
t .

Thus

t
(cid:88)

(cid:18) t
(cid:89)

e∆sAsRs

(cid:19)

Bixi.

ht =

i=0

s=i+1

yt = C⊤

t ht =

t
(cid:88)

i=0

C⊤
t

(cid:18) t
(cid:89)

e∆sAs Rs

(cid:19)

Bixi.

s=i+1

(12)

(13)

Using unitarity property,

t
(cid:89)

s=i+1

Rs = (cid:0)

t
(cid:89)

s=0

(cid:1)(cid:0)

Rs

i
(cid:89)

s=0

(cid:1)−1

= (cid:0)

Rs

t
(cid:89)

s=0

(cid:1)(cid:0)

Rs

i
(cid:89)

s=0

R⊤
s

(cid:1).

18

918
919

920
921
922
923
924
925

926
927
928
929
930
931

932
933
934
935
936

937
938
939
940
941
942

943
944
945
946
947
948

949
950
951
952
953
954

955
956
957
958
959

960
961
962
963
964
965

966
967
968
969
970
971

Under review as a conference paper at ICLR 2026

Since e∆sAs are scalars, they commute with rotations; hence

t
(cid:88)

C⊤
t

(cid:18) t
(cid:89)

Rs

(cid:19)(cid:18) t
(cid:89)

e∆sAs

(cid:19)(cid:18) i
(cid:89)

(cid:19)

R⊤
s

Bixi

yt =

i=0
(cid:18)

(cid:0)

t
(cid:89)

s=0

=

s=0

s=i+1

(cid:19)⊤ t

(cid:88)

(cid:18) t
(cid:89)

R⊤
s

(cid:1)Ct

e∆sAs

s=0
(cid:19)(cid:18) i
(cid:89)

(cid:19)

R⊤
s

Bixi.

i=0

s=i+1

s=0

Define the rotated parameters ¯Ct := (cid:0) (cid:81)t

(cid:1)Ct and ¯Bi := (cid:0) (cid:81)i

s=0 R⊤
s

(cid:1)Bi. Then

s=0 R⊤
s
t
(cid:88)

(cid:18) t
(cid:89)

yt = ¯C⊤
t

e∆sAs

(cid:19)

¯Bixi.

Equivalently, introducing the rotated state ˜ht := (cid:0) (cid:81)t
˜ht = e∆tAt ˜ht−1 + ¯Btxt,

s=0 R⊤
s

(cid:1)ht,
yt = ¯C⊤
t

˜ht,

i=0

s=i+1

(14)

(15)

(16)

(17)

C.3 PROOF OF PROPOSITION 4
Proposition 4 (Rotary Embedding Equivalence with Trapezoidal Discretization). Discretizing a
complex SSM with the trapezoidal rule (Proposition 1) yields the recurrence
(cid:33)
(cid:32)t−1
(cid:89)

(cid:32) t
(cid:89)

(cid:33)

ht = αtht−1 + βt

R⊤
i

Bt−1xt−1 + γt

R⊤
i

Btxt,

i=0
(cid:33)⊤

R⊤

i )Ct

ht.

yt =

(cid:32)
(cid:0)

t
(cid:89)

i=0

i=0

(9)

Here Rt is the block-diagonal rotation matrix defined in Proposition 3.

Proof. We begin from the complex SSM (as in Prop. 2)

˙h(t) = Diag (cid:0)A(t) + iθ(t)(cid:1) h(t) + (cid:0)B(t) + i ˆB(t)(cid:1) x(t),
y(t) = Re (cid:0)(C(t) + i ˆC(t))⊤h(t)(cid:1),

where A(t) ∈ R is a scalar and θ(t), B(t), ˆB(t), C(t), ˆC(t) ∈ RN/2.

Recall from Prop. 5,

ht ≈ e∆t(At+iθt) ht−1 +

(cid:90) τt

τt−1

e(τt−τ )(At+iθt)(cid:0)B(τ ) + i ˆB(τ )(cid:1) x(τ ) dτ.

Applying Prop. 1 to the above integral, we get

ht = e∆t(At+iθt) ht−1 + βt ei∆tθt(cid:0)Bt−1 + i ˆBt−1

(cid:1)xt−1 + γt

(cid:0)Bt + i ˆBt

(cid:1)xt,

(18)

wherem

αt := e∆tAt,

βt := (1 − λt)∆te∆tAt,

γt := λt∆t,

Since e∆t(At+iθt) = αt ei∆tθt and as shown in Prop. 2, multiplication by ei∆tθt is a block-diagonal
rotation in real coordinates, we get the real N -dimensional recurrence

ht = αt Rt ht−1 + βt Rt Bt−1 xt−1 + γt Bt xt,
yt = C⊤

t ht,

(19)

where Rt = Block(cid:0){R(∆tθt[i])}N/2

i=1

(cid:1) where R(Θ) =

(cid:21)
(cid:20)cos Θ − sin Θ
sin Θ cos Θ

, and projections

Bt =

(cid:21)

(cid:20)Bt
ˆBt

, Ct =

(cid:21)

(cid:20) Ct
− ˆCt

. Note that Rt is orthogonal, so R−1

t = R⊤
t .

19

972
973

974
975
976
977
978
979

980
981
982
983
984
985

986
987
988
989
990

991
992
993
994
995
996

997
998
999
1000
1001
1002

1003
1004
1005
1006
1007
1008

1009
1010
1011
1012
1013

1014
1015
1016
1017
1018
1019

1020
1021
1022
1023
1024
1025

Under review as a conference paper at ICLR 2026

Figure 4: Contrasting Mamba-2 and Mamba-3 Architectures: Key updates include trapezoidal dis-
cretization, data-dependent RoPE embeddings, MIMO projections, QK normalization, and learnable
biases.

We define the following,

˜ht :=

(cid:16) t
(cid:89)

s=0

(cid:17)

ht,

R⊤
s

¯Bt :=

(cid:16) t
(cid:89)

s=0

(cid:17)

R⊤
s

Bt,

¯Ct :=

(cid:16) t
(cid:89)

s=0

(cid:17)

R⊤
s

Ct.

Left-multiplying equation 19 by (cid:81)t
˜ht = αt
yt = ¯C⊤
t

t Rt = I,

s and using R⊤

s=0 R⊤
˜ht−1 + βt ¯Bt−1 xt−1 + γt ¯Bt xt,
˜ht.

This is a vanilla scalar-transition SSM with data-dependent rotary embeddings absorbed into B, C
via cumulative products of R⊤
s .

D MIMO FOR MAMBA-3
With hindsight from Mamba and with inference in mind, we propose the following MIMO formu-
lation:
Mamba with MIMO. With a given batch, head, and sequence position t, consider the input
Ut ∈ RD. Also denote P, R ∈ N as the head dimension and MIMO rank, respectively. We
first obtain SSM parameters via a set of projections defined in terms of tensor contraction notation
as follows:

Bt = contract(DN R, D → N R)(WB, Ut) Ct = contract(DN R, D → N R)(WC, Ut),
X′

Xt = contract(P R, P → P R)(WX, X′

t = contract(P D, D → P )(WX′, Ut)

t),

where WB, WC, WX′, WX are model parameters. Additionally, we obtain the residual term Zt
in the same manner as Xt with weights WZ′ and WZ. The state update and the SSM output is then
computed via the following MIMO SSM:

Ht = at Ht−1 + BtX⊤

t ∈ RN ×P ,

Yt = H⊤

t Ct ∈ RP ×R.

The intermediate output Y′
t is obtained via some residual function ϕ, Y′
the layer output Ot ∈ RD is computed via the following down projections:

t ← ϕ(Yt, Zt). Finally,

O′

t = contract(P R, R → P )(WO′, Y′

t)

Ot = contract(P, P D → D)(WO, O′

t).

20

1026
1027

1028
1029
1030
1031
1032
1033

1034
1035
1036
1037
1038
1039

1040
1041
1042
1043
1044

1045
1046
1047
1048
1049
1050

1051
1052
1053
1054
1055
1056

1057
1058
1059
1060
1061
1062

1063
1064
1065
1066
1067

1068
1069
1070
1071
1072
1073

1074
1075
1076
1077
1078
1079

BCXMamba-3 BlockSequence transformationMIMO projection (optional)Nonlinearity (activation, normalization, multiplication, etc.)XSSMAYMamba-2 Block!BCXX!ConvSSMANY!Linear projectionNNRoPE&Under review as a conference paper at ICLR 2026

This formulation enhances the existing Mamba3 architecture by providing a lightweight parame-
terization that transforms the set of independent SISO SSMs within each head into a set of MIMO
SSMs. Here, we note that the hardware-efficient chunking technique employed by Mamba2 for pre-
training can be applied with little change, as the MIMO dimension r is orthogonal to the sequence
dimension.

E EXPERIMENTAL DETAILS

Language Modeling. Our pretraining procedures follow that of Dao & Gu (2024)’s section D.2.
All models at each scale follow the same procedure and were trained with bfloat16. The Mamba
family of models were trained using the standard expand factor of 2 and a dstate of 128 and head
dimension of 64. The Transformer baselines follows Dao & Gu (2024), and the Gated DeltaNet
baselines follow (Yang et al., 2025a). We utilize the Llama-3.1 tokenizer (Grattafiori et al., 2024)
for all models.

We utilize LM Evaluation Harness (Gao et al., 2024) to test the zero-shot languag modeling ca-
pabilities of our pretrained model on LAMBADA (OpenAI version) (Paperno et al., 2016), Hel-
laSwag (Zellers et al., 2019), PIQA (Bisk et al., 2019), Arc-Easy/Arc-Challenge (Clark et al., 2018),
WinoGrande (Sakaguchi et al., 2019), and OpenBookQA(Mihaylov et al., 2018).

Real-World and Synthetic Retrieval. For our real-world retrieval tasks, we evaluate on the com-
mon suite consisting of SWDE (Arora et al., 2025b), SQUAD (Rajpurkar et al., 2018), FDA (Arora
et al., 2025b), TriviaQA (Joshi et al., 2017), NQ (Kwiatkowski et al., 2019), and DROP (Dua et al.,
2019). We utilize the cloze-formatted version of the aforementioned tasks provided by Arora et al.
(2025b; 2024), as the original datasets are in a question-answering format, making it challenge for
solely pretrained models. All tasks were truncated to match the training context length. The syn-
thetic NIAH tasks (Hsieh et al., 2024) were also run with LM Evaluation Harness.

State-Tracking Synthetics. Training follows a sequence length curriculum that progresses from 3
-40 to 160, evaluated at 256. Each curriculum runs for 104 steps with batch size 256. We use 1 layer
models for Parity and 3 layer models for Modular-arithmetic tasks. The state size is chosen to be
64, and we sweep dmodel ∈ {32, 64} and 8 learning rates logarithmically spaced between 10−4 and
10−2, reporting the best validation accuracy.

F ADDITIONAL EXPERIMENTAL RESULTS

Figure 5: Pretrained 1.5B models’ performance on the held-out FineWeb-Edu test set at varying
context lengths. Mamba-3 exhibits strong length extrapolation while Mamba-2 falters at longer
contexts.

21

1080
1081

1082
1083
1084
1085
1086
1087

1088
1089
1090
1091
1092
1093

1094
1095
1096
1097
1098

1099
1100
1101
1102
1103
1104

1105
1106
1107
1108
1109
1110

1111
1112
1113
1114
1115
1116

1117
1118
1119
1120
1121

1122
1123
1124
1125
1126
1127

1128
1129
1130
1131
1132
1133

1K2K4K8K16K32KContext length10.010.210.410.610.8PerplexityContext Length ExtrapolationTrain length = 2KGated DeltaNetMamba-2Mamba-3Under review as a conference paper at ICLR 2026

Table 6: Downstream language modeling evaluations on parameter-matched pretrained models, in-
cluding Mamba-3 MIMO. Mamba-3 MIMO’s average accuracy on all tasks is more than 1 percent-
age point better than the next best (Mamba-3 SISO).

Model

FW-Edu LAMB. LAMB. HellaS. PIQA Arc-E Arc-C WinoGr. OBQA Average

ppl ↓

13.03
Transformer-440M
13.12
Gated DeltaNet-440M
13.00
Mamba-2-440M
12.87
Mamba-3-440M
Mamba-3-MIMO-440M 12.72

11.42
Transformer-880M
11.39
Gated DeltaNet-880M
11.35
Mamba-2-880M
11.23
Mamba-3-880M
Mamba-3-MIMO-880M 11.11

ppl ↓

21.2
19.0
19.6
19.6
17.1

15.0
12.7
13.8
12.9
11.8

acc ↑

41.7
40.4
40.8
40.2
43.4

44.7
47.1
45.0
47.2
49.5

acc n ↑

acc ↑

acc ↑

acc n ↑

50.5
50.5
51.7
51.7
52.8

57.2
57.5
58.1
58.8
59.2

69.9
70.5
70.6
71.9
70.8

72.6
72.6
72.5
73.6
73.7

67.6
67.5
68.8
68.9
69.6

71.6
72.5
72.3
72.7
74.7

34.6
34.0
35.0
34.4
35.6

39.2
38.8
38.7
40.2
41.2

acc ↑

56.7
55.3
54.1
55.8
56.3

57.7
57.9
56.8
58.4
59.9

acc ↑

26.0
25.8
26.0
26.0
28.4

26.8
30.6
30.2
30.0
28.6

acc ↑

49.6
49.1
49.6
49.8
51.0

52.8
53.9
53.4
54.4
55.3

Figure 6: Mamba-3 demonstrates superior performance compared to strong baselines like Mamba-2,
Llama, and Gated Deltanet. These are 440M models, trained and evaluated on FineWeb-Edu.

We also compare the effectiveness of state size usage of Mamba variants to a Gated DeltaNet base-
line in Figure 7. We highlight the difficulty of directly comparing GDN versus Mamba-style models
due to the differing head structure, multi-head compared to multi-value respectively. Our experi-
ments hold GDN’s v expand to 2 and decrease the head dimension accordingly to vary the relative
total state size. Similar to Figure 3, we train 440M models to 2× Chinchilla tokens and sweep
across dstate = {32, 64, 128} for the Mamba models and dhead dim = {32, 64, 128} for GDN. We
parameter match all models.

22

1134
1135

1136
1137
1138
1139
1140
1141

1142
1143
1144
1145
1146
1147

1148
1149
1150
1151
1152

1153
1154
1155
1156
1157
1158

1159
1160
1161
1162
1163
1164

1165
1166
1167
1168
1169
1170

1171
1172
1173
1174
1175

1176
1177
1178
1179
1180
1181

1182
1183
1184
1185
1186
1187

0250005000075000100000125000150000175000Global Step12.012.513.013.514.014.515.015.516.0PerplexityMamba-3 Validation PerplexityMamba-3 MIMOMamba-3 SISOLlamaGatedDeltaNetMamba-2Under review as a conference paper at ICLR 2026

1188
1189

1190
1191
1192
1193
1194
1195

1196
1197
1198
1199
1200
1201

1202
1203
1204
1205
1206

1207
1208
1209
1210
1211
1212

1213
1214
1215
1216
1217
1218

1219
1220
1221
1222
1223
1224

1225
1226
1227
1228
1229

1230
1231
1232
1233
1234
1235

1236
1237
1238
1239
1240
1241

Figure 7: Exploration of state size (inference speed proxy) versus pretraining perplexity (perfor-
mance proxy). Mamba-3 and Mamba-3 MIMO continue set the Pareto frontier.

G ARCHITECTURE ABLATIONS
We explore our model architecture’s ablation in this section. All models are trained at the 440M
scale to Chinchilla optimal number of tokens (20× tokens to parameters) with the same experimental
procedures as our pretrained models as covered in Appendix E unless otherwise stated.

B,C Bias Parameterization. The Mamba-3 model’s separate B and C biases are head-specific and
channel-wise and added to both B and C after the QK-Norm. While the biases in the final Mamba-3
model are trainable, data-independent parameters and initialized to all ones, we explore various bias
parameterizations in Table 7a. We find our models are not very sensitive to the initialization of the
biases as long as they are positive. We choose the all-ones initialization due to it’s simplicity.

We also explore the impact removing the B or C bias on performance in Table 7b (bias is initialized
with our default parameterization when utilized). Unlike in Yu & Erichson (2025), which finds that
B bias by itself is able to improve performance on Mamba-1, our experiments find that only having
B bias hurts performance slightly and that B and C biases have synergetic properties.

Bias Init. Trainable

ppl ↓

1.0
0.0
1.0
U(0, 1)
U(−1, 1)

✓
✓
×
✓
✓

15.72
16.57
15.80
15.76
16.07

B Bias C Bias

ppl ↓

×
✓
×
✓

×
×
✓
✓

16.52
16.68
15.98
15.69

(a) Effect of parameterization of the B and C bias
on model performance, measured by pretraining
perplexity. We find our default initialization of all-
ones (first row) provides the best performance, but
performance is not sensitive as long as biases are
positive.

(b) Applying a bias to both B and C leads to the
best performance. Only applying B bias (Block-
Biased (Yu & Erichson, 2025) Mamba-3 variant)
does not provide significant gains over the no-bias
baseline.

Table 7: Ablations on B, C bias initialization (left) and presence (right) for Mamba-3.

H INFERENCE KERNEL LATENCY ANALYSIS

H.1 KERNEL IMPLEMENTATIONS AND FUSION STRUCTURE

In Table 3, we detail the DSL (Triton, CuTe, PyTorch) and the fusion level of the kernels used in our
latency analysis. For Mamba-2 and Gated DeltaNet (GDN), we directly use the publicly released
Triton kernels from the respective authors. For Mamba-3, we implement new inference kernels with
a comparable fusion structure: the forward uses a Triton kernel fused with rotary position embed-
dings, while the decode path uses a CuTe kernel fused with gating and MIMO projection.

In Tables 8 and 9, we abbreviate IP = input projection, Conv = 1D convolution, Gate = gating, OP =
output projection. Colors indicate implementation backend (Torch, Triton, CuTe).

23

105Relative Total State Size14.514.614.714.814.915.0Pretraining PerplexityRelative Total State Size vs Pretraining PerplexityMamba-2Mamba-3 Mamba-3 MIMOGated DeltaNetUnder review as a conference paper at ICLR 2026

Table 8: Kernel DSL and fusion structure for forward (prefill) kernels.

Model (Forward) Kernel DSL Fusion Level

Triton
Mamba-2
Triton
Gated DeltaNet
Mamba-3 (SISO)
Triton
Mamba-3 (MIMO) Triton

IP, Conv, SSM, Gate+OP
IP, Conv, Chunked Delta, Gate+OP
IP, SSM+Rotary, Gate+OP
IP, SSM+Rotary, Gate+OP

Table 9: Kernel DSL and fusion structure for decode kernels.

Model (Decode)

Kernel DSL

Fusion Level

Triton
Mamba-2
Triton
Gated DeltaNet
Mamba-3 (SISO)
CuTe + Triton
Mamba-3 (MIMO) CuTe + Triton

IP, Conv, SSM, Gate+OP
IP, Conv, Recurrent Delta, Gate+OP
IP, Rotary, SSM+Gate+OP
IP, Rotary, SSM+Gate+OP+MIMO

H.2 EXTENDED PREFILL AND PREFILL+DECODE LATENCY MEASUREMENTS

Models. We benchmark Mamba-3 1.5B (SISO), Mamba-2 1.5B, Gated DeltaNet (GDN) 1.5B, and
a strong Transformer baseline implemented via the vLLM engine (v0.11.0) with Llama-3.2 1B.3 All
recurrent models are trained at the 1.5B scale with dmodel = 2048 and 24 layers. For Mamba variants
we set state size as 128 and head dimension 64; for GDN we use QK head dimension as 128.
Setting. Sequence lengths were swept over L ∈ {512, 1024, 2048, 4096, 16384} for prefill, with
an equal number of tokens decoded. For sequence lengths {512, 1024, 2048, 4096}, we use batch
size of 128; for sequence lengths {16384}, we use batch size of 16. We use a single H100-SXM
80GB GPU and report wall-clock times (in seconds) over 3 repetitions.

Table 10: Prefill and Prefill+Decode latency across sequence lengths.

Model

512 tokens

1024 tokens

2048 tokens

4096 tokens

16384 tokens

Prefill Prefill+Dec Prefill Prefill+Dec Prefill Prefill+Dec Prefill Prefill+Dec Prefill Prefill+Dec

vLLM (Llama-3.2-1B)
Gated DeltaNet
Mamba-2
Mamba-3 (SISO)

0.26
0.48
0.48
0.48

4.45
4.52
4.62
4.33

0.52
0.95
0.96
0.95

9.60
9.04
9.24
8.64

1.08
1.90
1.91
1.90

20.37
18.07
18.48
17.29

2.08
3.79
3.81
3.80

58.64
36.14
36.94
34.57

1.52
1.91
1.92
1.91

122.06
71.66
57.90
53.97

We observe that (i) Mamba-3 adds minimal forward-pass cost showing that the trapezoidal update,
complex state tracking, and MIMO parameterization remain lightweight; (ii) decode latency is com-
petitive across recurrent models; and (iii) recurrent mixers scale more gently with context length
than vLLM Llama-3.2-1B, which grows much faster with L due to KV-cache overhead.

3https://huggingface.co/meta-llama/Llama-3.2-1B

24

1242
1243

1244
1245
1246
1247
1248
1249

1250
1251
1252
1253
1254
1255

1256
1257
1258
1259
1260

1261
1262
1263
1264
1265
1266

1267
1268
1269
1270
1271
1272

1273
1274
1275
1276
1277
1278

1279
1280
1281
1282
1283

1284
1285
1286
1287
1288
1289

1290
1291
1292
1293
1294
1295