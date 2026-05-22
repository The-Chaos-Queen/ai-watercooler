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

## MAMBA-3: IMPROVED SEQUENCE MODELING USING STATE SPACE PRINCIPLES

## Anonymous authors

Paper under double-blind review

## ABSTRACT

The recent scaling of test-time compute for LLMs has restricted the practical deployment of models to those with strong capabilities that can generate high-quality outputs in an inference-efficient manner. While current Transformer-based models are the standard, their quadratic compute and linear memory bottlenecks have spurred the development of sub-quadratic models with linear-scaling compute with constant memory requirements. However, many recent linear-style models lack certain capabilities or lag behind in quality, and even their linear-time inference is not hardware-efficient. Guided by an inference-first perspective, we introduce three core methodological improvements inspired by the state-space model viewpoint of linear models. We combine a: 1) more expressive recurrence derived from discretization , 2) complex-valued state update rule that enables richer state tracking, and 3) multi-input, multi-output formulation together, resulting in a stronger model. Together with architectural refinements, our Mamba-3 model achieves significant gains across retrieval, state-tracking, and downstream language modeling tasks. Our new architecture sets the Pareto-frontier for performance under a fixed inference budget and outperforms strong baselines in a head-to-head comparison.

## 1 INTRODUCTION

Test-time compute has emerged as a key driver of progress in AI, with techniques like chain-ofthought reasoning and iterative refinement demonstrating that inference-time scaling can unlock new capabilities (Wu et al., 2025; Snell et al., 2024). This paradigm shift makes inference efficiency (Kwon et al., 2023; Li et al., 2024) paramount, as the practical impact of AI systems now depends critically on their ability to perform large-scale inference during deployment. Model architecture design plays a fundamental role in determining inference efficiency, as architectural choices directly dictate the computational and memory requirements during generation. While Transformerbased models (Vaswani et al., 2017) are the current industry standard, they are fundamentally bottlenecked by linearly increasing memory demands through the KV cache and quadratically increasing compute requirements through the self-attention mechanism. These drawbacks have motivated recent lines of work on sub-quadratic models, e.g., state-space models (SSMs), which, despite utilizing only constant memory and linear compute, have comparable or better performance than their Transformer counterparts. Models that benefit the most from this new scaling paradigm perform well on the following three axes: (i) quality, (ii) capability, and (iii) inference efficiency.

Recent model architectures have tried to strike a balance between the three, but many fall short on at least one of these three axes. In particular, Mamba-2 and Gated DeltaNet (GDN), which have gained significant traction and adoption due to their inference efficiency, made architectural design choices that enable their linear compute requirements but sacrifice quality and capabilities (Dao &amp; Gu, 2024; Yang et al., 2025a). For example, Mamba-2 was developed to improve training speed and simplicity over Mamba-1 (Gu &amp; Dao, 2024), opting out of more expressive parameterizations of the underlying SSM and hindering the quality of the model (Dao &amp; Gu, 2024). Linear attentionstyle models (Katharopoulos et al., 2020) have also been shown to lack certain capabilities, with poor state-tracking abilities, e.g., determining parity of bit sequences, being one of the most notable (Grazzi et al., 2025; Sarrof et al., 2024). In addition, despite these sub-quadratic models being prized for theoretically efficient inference, these inference algorithms are not hardware efficient. In particular, because these algorithms were developed from a training perspective, their decoding phase has low arithmetic intensity (the ratio of FLOPs to memory traffic), resulting in large portions of hardware remaining idle.

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

To develop more performant models from an inference-first paradigm, we introduce three core methodological changes on top of Mamba-2, influenced by a SSM-centric viewpoint of subquadratic models. While many recent models fall into the linear attention framework (Dao &amp; Gu, 2024; Yang et al., 2025a; Sun et al., 2023), we find that the classical SSM toolbox (Kalman, 1960; Gopal, 1993) leads to natural interpretations and improvements on modeling.

Trapezoidal Discretization. We discretize the underlying continuous-time dynamical system with a trapezoidal methodology. The final recurrence is a more expressive superset of Mamba-2's recurrence and can be viewed as a convolution. We combine this new discretization with applied biases on the B,C , inspired by Yu &amp; Erichson (2025), and find that their synergy is able to empirically replace the short causal convolution in language modeling which was previously hypothesized to be essential for recurrent models.

Complex-valued State-Space Model. By viewing the underlying SSM of Mamba-3 as complexvalued, we enable a more expressive state update than Mamba-2's. This change in update rule, designed to be lightweight for training and inference, overcomes the lack of state-tracking ability common in many current linear models. We emphasize that our complex-valued update rule is equivalent to a data-dependent rotary embedding and can be efficiently computed (Su et al., 2023).

Multi-Input, Multi-Output SSM. To improve FLOP-efficiency during decoding, we shift from outer-product-based state update to matrix-multiplication-based state update . In view of the signal processing foundations of SSMs, such a transition exactly coincides with the generalization from a single-input single-output (SISO) sequence dynamic to a multiple-input multiple-output (MIMO) one. Here, we found that MIMO is particularly suitable for inference, as the extra expressivity allows for more compute during state update, without increasing the state size and hence compromising speed.

These three SSM-centric methodological changes are core to our Mamba-3 mixer primitive. We also make adjustments to the overall architecture to ensure more similarity to the baseline Transformer architecture. Mamba-3 swaps the pre-output projection norm with the more common QKnormalization (Team et al., 2025; OLMo et al., 2025) and makes the short convolution, a common component found in many other sub-quadratic models (Gu &amp; Dao, 2024; Yang et al., 2025a; von Oswald et al., 2025), optional.

We empirically validate our new model on a suite of synthetic and language-modeling tasks.

- Better Quality. Mamba-3 matches or outperforms Mamba-2 and other open-source architectures on standard downstream language modeling evaluations. For example, Mamba-3-1.5B's average accuracy on all downstream tasks is better than that of its Transformer, Mamba-2, and Gated DeltaNet counterparts.
- New Capabilities. Mamba-3's complexification of the SSM state enables the model to solve synthetic state-tracking tasks that Mamba-2 cannot. We empirically demonstrate that the efficient RoPE-like calculation is able to near perfectly solve arithmetic tasks, while Mamba-3 without RoPE and Mamba-2 perform not better than random guessing.
- Stronger Inference Efficiency. Mamba-3's MIMO variant retains the same state size while enabling better hardware utilization compared to standard Mamba-3 and other models. Its improved performance without increased memory requirements pushes the pareto-frontier of inference efficiency.

## 2 PRELIMINARIES

## 2.1 NOTATION

Scalars are denoted by plain-text letters (e.g., x, y ). Tensors, including vectors and matrices, are denoted by bold letters (e.g., h , C ). The shape of the tensor can be inferred from the context. We denote the input sequence length as T , the model dimension as D , and the SSM state size as N . For time indices, we use subscripts (e.g., x t for the input at time t ). The Hadamard product between two tensors is denoted by ⊙ . For a vector of size v ∈ R d , we denote Diag( v ) ∈ R d × d as the diagonal matrix with the vector v as the diagonal, and for products of scalars across time steps, we use the notation α t ··· s = α × t : s = ∏ t i = s α i .

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

## 2.2 SSM PRELIMINARIES

State Space Models (SSMs) describe continuous-time linear dynamics via

<!-- formula-not-decoded -->

where h ( t ) ∈ R N is the hidden state, x ( t ) ∈ R the input, and A ( t ) ∈ R N × N , B ( t ) , C ( t ) ∈ R N . For discrete sequences with step size ∆ t , Euler's discretization gives the recurrence

<!-- formula-not-decoded -->

Mamba-2's parameterization. Mamba-2 (Dao &amp; Gu, 2024) makes the SSM data-dependent and hardware-efficient by (i) projecting A = A ∈ R &lt; 0 , and B , C ∈ R N from the current token and (ii) choosing transition matrix A = A as a data-dependent scalar. Writing α t := e ∆ t A t ∈ (0 , 1) and γ t := ∆ t , the update becomes

<!-- formula-not-decoded -->

The scalar A t &lt; 0 is an input-dependent forget-gate (decay) α t , and the parameter selectivity ∆ t jointly controls the forget-gate ( α t = exp(∆ t A t ) ) and the input-gate ( γ t = ∆ t ): larger ∆ t forgets faster and up-weights the current token more strongly, while smaller ∆ t retains the hidden state with minimal contributions from the current token.

## 2.3 STRUCTURED MASKED REPRESENTATION AND STATE SPACE DUALITY

Dao &amp; Gu (2024) show that a large class of SSMs admit a matrix form that vectorizes the time-step recurrence. For instance, Mamba-2's recurrence can be vectorized as a masked matrix multiplication,

<!-- formula-not-decoded -->

where L ∈ R T × T is the structured mask, B , C ∈ R T × N , X ∈ R T × D is the input to the SSM and Y ∈ R T × D is its output. Within this form, Mamba-2 can be viewed as a type of linear attention by setting Q = C , K = B , V = X and viewing L as a causal, data-dependent mask. When all α = 1 , the expression reduces to (causal) linear attention (Katharopoulos et al., 2020). A more detailed coverage of related linear-time sequence mixers can be found at Appendix A.

## 3 MODEL DESIGN FROM A STATE-SPACE VIEWPOINT

We introduce Mamba-3, with three new innovations rooted in classical state-space theory: trapezoidal discretization for more expressive dynamics, complex-valued state spaces for state-tracking, and multi-input multi-output (MIMO) to improve hardware utilization. These advances address the quality, capability, and efficiency limitations of current sub-quadratic architectures.

## 3.1 TRAPEZOIDAL DISCRETIZATION

Structured SSMs are naturally defined as continuous-time dynamical systems that map input functions, x ( t ) ∈ R , to output functions, y ( t ) ∈ R , for time t &gt; 0 . In sequence modeling, however, the data is only observed at discrete time steps, which then requires applying a discretization step to the SSM to transform its continuous-time dynamics into a discrete recurrence. The preliminary step in deriving Mamba-3's discretization is to apply the Variation of Constants formula (Proposition 5), which decomposes the hidden state into an exponentially decay term and a state update term 'information' term dependent on the most recent inputs.

The first step in deriving the discretized recurrence is to approximate the 'state-update' integral in equation 10. A straightforward choice, used in Mamba-2, is applying Euler's rule (S¨ uli &amp; Mayers, 2003), which approximates the integral by holding the (right) endpoint constant throughout the interval (Fig. 1). This yields Mamba-2's recurrence,

<!-- formula-not-decoded -->

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

Figure 1: Left: The structured mask induced by the generalized trapezoid rule is a product of the decay and convolutional mask. Right: Euler (hold endpoint) vs trapezoidal rule (average endpoints).

![Image](data:image/png;base64,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6nQ6p0+fPmTIkD///PPQoUMA4PF4XnrppVq1aj3//PPmNgcOHAgODg4JCQEAu91us9m6dOlyzz33AIBhGO+//76u6x9++KG58f79++fOnVucPkVE9evX792795NPPvntt9/GxMRMmjSp+PEsISHhjz/+EEKcb5Q4HI6///578uTJzz77bGho6JIlS5555pkpU6a0adPGHPaJJ54ICAh46623SrTeTH9SrVq1xo4dGxoaes0111z0ULz11lu7d+/+4osv/Pz8StygTZs277///s0336yqaol2UqNGjfbt29elS5eLzmXhI1XoJjBj5nczfvj2iSeeCQsJ9fcPDAwM9Pf3VxQFAW02W1xcDV2v6qkAFuXCuHHjBg8eTES6rufm5ubm5u7cufPTTz8dNGhQfHy8y+Wa+M6EgQOu7dqlo8MRFBQU7HA4GDJFUWrWjOel5aSWK9apWNlkZWXNnTuXiGw2W2hoaFRUVHR0dExMzPm5OKtXr167du3jjz9eKessX5jCAv39Zs5Z8NuyVd6mzCNifr6zwOn09/PORSRBTk6Ot1bUwoULN2zY4O/vv379+sjIyOKHqMaNGy9fvvzIkSOjRo1yuVyqqprGimEY27dvb9++vbm76fqqV6/eX3/9tWHDhhEjRjgcjrCwMCFE8RSBgYHh4eFEtHnz5rZt257t4bbb7S6Xq0QrijGmaVrdunXHjx9vt9sHDhzYo0ePhQsXmlbU6tWr169f/9NPP5Xu5EtMTBw3btx7773XtWtX0wq8EHv27Pnuu+9mzpx5IRPKJDg4+MEHH/y///u/66677mzHmInT6VRVtWXLlqWMYFEuVCEryuVyde3S/Y47bwFRKCpXfIkgAsO4XDpHWfhKdHR0dHT02b9p3rz5999/b5btEAk/P7+hQ4Z37tYW+L/niXWS/NfIy8tbvHixx+MRQrjdbqfTmZ+fn5mZOW3atOKIj8n+/fuXLl16ZVhRmqp+/vZTp05nSBryCEEBAVERoRfdMDs7+88//8zPz69fv37Tpk3PfiktLS00NLQUOU0iys3NtdlsNputxA02bty4adOmjIyMTp06derUCRGPHj36008/vfvuu4mJifPmzZs/f75hGBkZGenp6TVq1JgzZ07NmjX9/f2DgoKcTifnnDGWmZmZkpIyZsyY/fv3R0ZG2u32lJSUHj16JCcnu93uoKAgPz+/O++88/zZMzIyjh49OnLkyMOHDycmJpq/zMvLCwgIKDGLSAixadOmZs2amUZhenq6x+Mp3nHOnDn16tUrjjk6nc7k5OQDBw6Yz4GMsaFDh9aqVQsABg4c+Pzzz2/fvr1z585EtHTp0r///nv06NF169Zdv379H3/8cdNNN1WrVm3VqlVBQUGNGjUyBzQM4/fff9+zZ4+ZyAUA/fv3b9KkCQC0adMmICBg+fLlo0ePNjfevXv3ypUrETElJcVms9WrVw8AduzYsXr1arfbbaZANGrU6Oqrr7Ya8pQXVciKMiM4QOB2VvZSLKoYTqcTAIof9RDR7XaDAW53pS7LolKpUaPG7Nmzzb+7XK68vLycnJzbbrtt27Zt51hRqqp65RSp4kSFh0aFh17SKc6cOTN+/Pjly5cXFBSEhYWNGjXqoYceMu2GVatWTZ48+d13361evfqFdjcMo6CgQNM0TdPOf/XLL79ctGjR7bfffvjw4YcffnjBggV2u/3111/fu3dvSEhIUFDQ/v379+zZs337dgA4duzYG2+8cf3111933XUAUK9evfz8/IyMjJiYGH9//2rVqr311lu9evW65557Tp8+ffjw4ffff3/o0KG33357Ke9OVVV/f/+vv/76vvvuKzaGDhw4kJSUVKI/KSMjY9++fa1btz5z5szhw4c/+uij3r17DxkyBAA8Hs+OHTt69OhhbunxeD766KPdu3efPHnyn3/+GT58eFBQULEzLCQkJDIycuvWrZ07d962bdvq1auTk5PT0tJuueWWV199VdO0G264AQDWrFnTqlUr08oRQnz55Zdr167Nz89PTk4eNGhQZGSkrhdGcoOCgqpXr75y5UrTilq1atUrr7wycuTIWrVqffjhh4mJibGxsevWrfvss88URVmwYEHTpk0bN25cet6YhbdUISvKwsLCQg4z9BMZGRkXF2fdIXzEMIwJEyYEBgbu3LlT1/UpU6Z8/vnnM2bMGD58eGBg4KJFi+68886YmJhSRtB13bSizvdXrVmz5sMPP/zss886dOiwc+dOTdMQMSAg4M033zRFBxhjTz311OOPP+5wOKZPn966dWtVVU+ePJmfn2+G1Ro3brxgwYJx48YFBAR8/vnnp06dio2NdTgcq1evrlu3bs2aNVNSUvLy8kqJJ4aEhEyfPt3tdhe/i0OHDh06dOimm24qcfuDBw9mZGRs3rz5ueee27BhQ2Ji4gcffBAcHAwA2dnZ2dnZcXFxxRsPHDjwkUceee2114KCgj755JOzx1FVtXr16keOHAGApKSkF198sXbt2u+9915ubu7TTz/dtm1bxhjn/ODBg3379jV3IaIuXbqMGzfuyy+/zMvLmzRp0jlljxEREUePHgWAtLS0F198sW/fvnfccQfnPD4+vmnTpuaMEyZMyMjI2LRp02uvvda2bdtSPjgLCSwrysLC4sqhXJQYqzwEIHzLEBcASikj9O/fv23btqZm5ssvvzx69Oivv/46OTk5MDDwueeeM91CpaDrusvlcjgc5wfIZs6cSUSbNm2aPXv23r17X3jhBVPf3DRKTIoNhcOHD7dq1apu3brPPvus3W6/+eabbTbb+PHjP/jgg7lz5w4fPjwgIKB27drmxnv37m3QoMHgwYPvuecef3//e++9txQH5NlyoLt37542bdqNN95Yp06dEjfevHlzZGTkxx9/XK1atb179w4dOnTGjBnjx48HACEEERUb7jabrXHjxrqur1mzplu3bucPxRgzXVPm2po1a3b69OkePXoUZ3eZYxaH2xRFady4cXFTwvOVIxDRHHDt2rVHjx4dOnQoAJw4ceLUqVOmsEJCQgIALFu2DACKj5VFOWJZURYWFhaXE7nph6d+89Wh05wh89aSIgAhRMOatltvvt0WFFfiNqqq9unTZ+3atZ988klGRkbPnj1vvPHGN99808xGEkIsW7asbdu2paRIG4bhdrsDAwPPiejl5ubu2rWrSZMm8fHxHTp0aNSoUemR1meeeUbTNEVRfvjhh4CAAH9/fwCIiYl59tln9+7daxjG2b6ue++910wDnzVrlqZpQUFBZTwmiqKMHz8+Pj7+Qhts2rQpMTExLCwMABISEux2+549e8yXAgMDHQ5Henr62dunpqYeO3bs/MxuzvmZM2fOFnnau3cvAJy9VMZYVFRUWlra2TuePn167969JeZ4ZWdnh4eHA8D27dvDwsLMxoVr1qzJzMw8W3bh77//rlu3rrmlRfli5ZdZWFhYXE6kZzlnL9utMrVaVHB0RJBXP9WjQlwe+vH3Azl5rlKmWLly5fjx4w3DcDgcL774YteuXT/++OO8vDyXy/Xqq69OnDix9A4tnHO32+3n53eOFWUmXDdp0mTgwIEtW7Zcv369qWhw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9GjcuLHECPv373/nnXe2bt3aqlWr4cOHJyQkOByOvLy8Q4cO/f77799//33nzp3Hjx+fmJhY3mu/JHg8nueee+7EyRPTpn2VlX56yfxvbxzRMyjQX3ACQEUtPAWIQDeoS6dWew8cXfv7vMat+0ZFhQNAnz59cnJy3njjjRo1ahR37rMAgNWrV//888+bN2+uVbv2Dz/8YPZgPp+QkJAxY8b07t174sSJN99886uvvtqrV69yX8yVprpJRUXAFhbFmBoHBQUF1193Q+NG9YUBnHMzf05VVcash7wrnKCgoHPEuH3h8OHDd911V+PGjd955509e/a0bt26c+fOAICIdrsdAIWgmLj4dp27r13xx4Y/16qajXOharYHnny+Q9ceLzz6wLEjBxUf4wu+nLMofBA+L43IyMgdO3ZEREQ88cQT57QKLgvffPPN2LFjQ0JCvv32248++ui6667r0KFDixYtunTpctNNN02dOvXLL790Op033njj7Nmzy+66qywEiddff23btm2fffZ5dlbWycPrbxzZIzDYj4vCW5QwoPhuRQAKw+aNatsh69cfp3pceQBAJIYPHz5u3LjHHnvsyJEjlfdWqhbZ2VlPP/3MxIkTt23bPmrE8PDwYF3/Nxm66IAWAzExMW+//fbdd9/92GOPzZ49u9zXc6X5ohwOP0tIw+IcGMLx4ye3bN309JMvAILgEBkR6e/vf+jQwYOHDtSuVcfh0MrVVWFRtejdu3fbtm3LZagTJ048+OCDLVu2fOWVV9avX3/o0KFWrVqZKTuChMvlAgAAFAYHZP2HDDm4Z89fq1c0btbczz8QkN310BPZWZlvPPvYm5O+9A8KFlKnHZnKCT7pRV2SrKi77rrr9ttv9zaBKSMj47333tuxY8fJkycef/zxq68eCEAF+fkEcFbaFyJCrcTEN9+c8Osvv745YcK2bdseffRRTdME58iYzW5TmFKlwl5fT5v222+/ff31NwH+6o8zvu7dqUFwcBDnHBEEEBIoChWv1/zTreutWzSsk5g3f8aUZh2ubtCwAQDdeeedO3fufO6556ZMmVJhdWdVmf37DqQcPuxntzdvGJ+ZuiFlZ86ff+8Ni4yqn9SowAMNGjRCpths9nMsgZtvvjk6OvqZZ57xeDw33HBDOa7nyrGizBzzD979iDHFEouyOBtkkHL0SHRUTGJCAufA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)

However, Euler's rule provides only a first-order approximation to the 'state-update' integral: local truncation error is O (∆ 2 t ) , which accumulates across steps to yield a global error of O (∆ t ) over the sequence. In contrast, we adopt a generalized trapezoidal rule , which provides a second-order accurate approximation of the integral, offering improved accuracy over the Euler's rule. Specifically, it approximates the integral with a data-dependent, convex combination of both interval endpoints . This generalization extends the classical trapezoidal rule (S¨ uli &amp; Mayers, 2003), which simply averages the interval endpoints, by allowing for a data-dependent convex combination (Fig. 1).

Proposition 1 (Generalized Trapezoidal Discretization) . Approximating the state-update integral in equation 10 by the general trapezoidal rule yields the recurrence,

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

where λ t ∈ [0 , 1] is a data-dependent scalar, α t := e ∆ t A t , β t := (1 -λ t )∆ t e ∆ t A t , γ t := λ t ∆ t .

Remark 1 (Expressivity) . Our scheme is a generalization of a) The classical trapezoid rule which is recovered when λ t = 1 2 . b) Mamba-2's Euler's rule, which is recovered when λ t = 1 .

Remark 2 (Error Rate) . This is a second-order discretization with local truncation error O (∆ 3 t ) and global error O (∆ 2 t ) over the sequence under standard stability assumptions, provided that the trapezoidal parameter satisfies λ t = 1 2 + O (∆ t ) . However, our ablations indicate that not enforcing this constraint is the best for empirical performance. See Appendix B.2,B.3 for details.

## 3.1.1 TRAPEZOIDAL DISCRETIZATION IS A CONVOLUTIONAL MASK

We can view the generalized trapezoidal discretization as applying a data-dependent convolution of size two on the projected input, B t x t , to the SSM. We now show that a similar vectorization to Equation (1) holds with the generalized trapezoidal discretization. Unrolling the recurrence starting from h 0 = γ 0 B 0 x 0 results in h T = α T ··· 2 ( γ 0 α 1 + β 1 ) B 0 x 0 + · · · + γ T B T x T .

Unrolling these rows shows that the mask induced by the trapezoidal update is no longer a fixed averaging of endpoints (as in the classical trapezoidal rule), but a data-dependent convex combination of the two interval endpoints. In the SSD representation, this corresponds to a mask L :

<!-- formula-not-decoded -->

Here, the first factor is precisely the lower-triangular decay mask from Mamba-2, while the second factor encodes the size two convolution induced by the trapezoidal rule through the coefficients ( β t , γ t ) . We provide a rigorous proof for this decomposition in Appendix B.1.

## 3.2 COMPLEX-VALUED SSMS

Modern SSMs are designed with efficiency as the central goal, motivated by the need to scale to larger models and longer sequences. For instance, successive architectures have progressively simplified the state transition matrix: S4 (Gu et al., 2022a) used complex-valued Normal plus Low Rank (NPLR) matrices, Mamba (Gu &amp; Dao, 2024) reduced this to a diagonal of reals, and Mamba-2 (Dao &amp; Gu, 2024) further simplified it to a single scalar. Although these simplifications largely maintain language modeling performance, recent works (Merrill et al., 2025; Sarrof et al., 2024; Grazzi et al., 2025) have shown that they degrade the capabilities of the model on simple state-tracking tasks such as parity and modular arithmetic, which can be solved by a one-layer LSTM.

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

This limitation, formalized in Theorem-1 of (Grazzi et al., 2024), arises from restricting the eigenvalues of the transition matrix to real numbers, which cannot represent 'rotational' hidden state dynamics. For instance, consider the parity function on binary inputs { 0 , 1 } , defined as ∑ t x t mod 2 . This task can be performed using update: h t = R ( πx t ) h t -1 , where R ( · ) is a 2-D rotation matrix. Such rotational dynamics cannot be expressed with real eigenvalues.

To recover this capability, we begin with complex SSMs (6), which are capable of representing state-tracking dynamics. We show that, under discretization (Proposition 5), complex SSMs can be formulated as a real SSMs with a block-diagonal transition matrix composed of 2 × 2 rotation matrices (Proposition 2). We then show that this is equivalent to applying data-dependent rotary embeddings on both the input and output projections B , C respectively. This result establishes a theoretical connection between complex SSMs and data-dependent RoPE embeddings (Proposition 3). Finally, this allows for an efficient implementation of the complex-valued SSM via the 'RoPE trick', enabling efficient complex-valued state transition matrix with minimal computational overhead over real-valued SSMs.

Proposition 2 (Complex-to-Real SSM Equivalence) . Consider a complex-valued SSM

<!-- formula-not-decoded -->

where h ( t ) ∈ C N/ 2 , θ ( t ) , B ( t ) , ˆ B ( t ) , C ( t ) , ˆ C ( t ) ∈ R N/ 2 , and x ( t ) , A ( t ) ∈ R . Under Euler discretization, this system is equivalent to a real-valued SSM

<!-- formula-not-decoded -->

with state h t ∈ R N , projections

<!-- formula-not-decoded -->

and a transition matrix

<!-- formula-not-decoded -->

The proof is in Appendix C.1.

Proposition 2 shows that the discretized complex SSM has an equivalent real SSM with doubled state dimension ( N ), and a block-diagonal transition matrix multiplied with a scalar decay, where each 2 × 2 block is a data-dependent rotation matrix ( e ∆ t A t R t ). We now show that the rotations can equivalently be absorbed into the input and output projections B t , C t , yielding an equivalent view that complex SSMs are real SSMs equipped with data-dependent rotary embeddings (RoPE) .

Proposition 3 (Complex SSM, Data-Dependent RoPE Equivalence) . Under the notation established in Proposition 2, consider the real SSM defined in Eq. 7 unrolled for T time-steps. The output of the above SSM is equivalent to that of a vanilla scalar transition matrix-based SSM (Eq. 2) with a data-dependent rotary embedding applied on the B , C components of the SSM defined as:

<!-- formula-not-decoded -->

where the matrix production represents right matrix multiplication, e.g., ∏ 1 i =0 R i = R 0 R 1 . We denote employing the vanilla SSM to compute the Complex SSM as 'RoPE trick'.

The proof is in Appendix C.2.

To observe the connection of complex SSMs to RoPE embeddings, note that in the above proposition, the data-dependent rotations R i are aggregated across time-steps and applied to C , B , which, by the State Space Duality of Dao &amp; Gu (2024), correspond to the Query ( Q ) and Key ( K ) components of Attention. Analogously, vanilla RoPE (Su et al., 2023) applies data-independent rotation matrices, where the rotation angles follow a fixed frequency schedule θ [ i ] = 10000 -2 i/N .

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

Remark 3 (Generality) . Proposition 3 extends to the fully general case where the transition is given by any complex matrix. By the complex diagonalization theorem, such a matrix is unitarily equivalent to a complex diagonal matrix, Diag ( A ( t ) + i θ ( t ) ) with A ( t ) ∈ R N . However, in practice, we restrict A ( t ) to a scalar, mirroring the simplification from Mamba to Mamba-2, to enable faster implementation by avoiding GPU memory bottlenecks.

Proposition 4 (Rotary Embedding Equivalence with Trapezoidal Discretization) . Discretizing a complex SSM with the trapezoidal rule (Proposition 1) yields the recurrence

<!-- formula-not-decoded -->

Here R t is the block-diagonal rotation matrix defined in Proposition 3.

The proof is in Appendix C.3.

Remark 4 (RoPE Trick) . Complex SSMs discretized with the general trapezoidal rule of a complex SSM naturally admit the RoPE trick we established for SSMs discretized with Euler's rule.

## 3.3 MULTI-INPUT, MULTI-OUTPUT

During the decoding phase of autoregressive inference, outputs are generated one token at a time, and performance is typically measured using in Tokens generated Per Second (TPS) . In this metric, subquadratic models, such as Mamba-2 (Dao &amp; Gu, 2024), have a significant advantage over standard Transformer-style attention, since they feature a fixed-size hidden state (Equation (2)) rather than maintaining a key-value (KV) cache that grows linearly with the sequence length.

TPS, however, does not explicitly factor in hardware efficiency, where we aim to be in a computebound regime (as opposed to memory-bound) in order to fully utilize on-chip accelerators. To better characterize hardware efficiency, we would need to consider the arithmetic intensity of token generation. Recall that arithmetic intensity is defined as FLOPs divided by the number of inputoutput bytes, for a given op. In order to fully utilize both the accelerators and the bandwidth, we would like the arithmetic intensity to match the ops:byte ratio of the hardware, which in the case of NVIDIA H100-SXM5, is 295.2 bfloat16 ops per second with respect to the DRAM, and 31.9 bfloat16 ops per second with respect to the SRAM [Fleetwood].

Table 2(a) shows the arithmetic intensity for a single generation in the SSM component of Mamba (with respect to 2-byte data). We see that it falls far short of a compute-bound regime, and moreover it is not clear how one can adjust the existing parameters in Mamba to mitigate the lack of hardware efficiency. We note that this observation applies generally to other sub-quadratic models, such as causal linear attention.

| Input                                                        | Output      | FLOPs   | Arithmetic Intensity                   | Input                                                                 | Output         | FLOPs        | Arithmetic Intensity                               |
|--------------------------------------------------------------|-------------|---------|----------------------------------------|-----------------------------------------------------------------------|----------------|--------------|----------------------------------------------------|
| H t : ( n, p ) x t : ( p ) a t : (1) b t : ( n ) c t : ( n ) | y t : ( p ) | 5 pn    | 5 pn 2(1+2 n + p + np ) ≈ 2 . 5 = Θ(1) | H t : ( n, p ) x t : ( p, r ) a t : (1) b t : ( n, r ) c t : ( n, r ) | y t : ( p, r ) | 4 nrp + 2 np | p (4 nr +2 n ) 2(1+2 nr + pr + np ) ≈ 2 r = Θ( r ) |

(a) SISO (2-byte data).

(b) MIMO (2-byte data).

Figure 2: Arithmetic Intensity for (a) SISO, (b) MIMO. Batch and head dimensions cancel out.

In light of this, we made the following simple adjustment to our recurrent relation: instead of transforming the input x t ∈ R p to state H t ∈ R n × p via an outer product, i.e., H t ← a t H t -1 + b t ⊗ x t , we made such a transformation via a matrix product, i.e., H t ← a t H t -1 + B t X ⊤ t , where B t ∈ R n × r and X t ∈ R p × r are now matrices with an additional rank r . The emission from state to output similarly acquire an extra rank r , i.e., Y t ∈ R r × p ← C ⊤ t H t , where C t ∈ R n × r , H t ∈ R n × p . This simple change increases the arithmetic intensity of recurrence, which now scales with the rank

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

r (Figure 2(b)). Hence, by increasing r , arithmetic intensity improves and shifts decode generation towards a more compute-bound regime. This increase in FLOPs during decode does not compromise runtime, as the operation is bounded by the I/O of state H t ∈ R n × p .

Moreover, moving from outer-product-based state update to matrix-product-based coincides exactly with generalizing from SISO to MIMO SSM, with the rank r being the MIMO rank. Such a generalization recovers a key expressive feature of SSMs in classical literature; indeed, there has been previous work, namely Smith et al. (2023), that explored MIMO SSM as a drop-in replacement of attention, albeit not in the context of Mamba and not necessarily with inference in view. We note that training and prefilling is generally compute bound, resulting in MIMO incurring increased costs during these stages, while decoding, a memory-bound operation, sees very little increase in latency when utilizing MIMO over SISO.

Details of the MIMO formulation for Mamba-3 are provided in Appendix D.

## 3.4 MAMBA-3 ARCHITECTURE

The Mamba-3 block retains the overall layout of its predecessor while introducing several key modifications. Most notably, the SSD layer is replaced with the more expressive trapezoidal SSM defined in Proposition 4. The extra normalization layer, first introduced between Mamba-1 and Mamba-2 for training stability, is repositioned to follow the B , C projection, mirroring the QK-Norm commonly used in modern Transformers (Henry et al., 2020; Wortsman et al., 2023). Inspired by the findings of Yu &amp; Erichson (2025), which prove adding channel-specific bias to B in a blockwise variant of Mamba-1 grants universal approximation capabilities, Mamba-3 incorporates a head-specific, channel-wise bias into both the B and C components after its normalization. These learnable biases are data-independent parameters that are initialized to all ones and independent across B and C (ablations for bias parameterization can be found in Appendix G). Our trapezoidal discretization complements this bias, empirically eliminating the need for the original short causal convolution and its accompanying activation function (Section 4.3). Mamba-3 employs the SISO SSM by default, though we view its MIMO variant as a flexible option that can be toggled depending on inference requirements. The overall architecture follows the Llama design (Grattafiori et al., 2024), alternating Mamba-3 and SwiGLU blocks with pre-normalization.

## 4 EMPIRICAL VALIDATION

We empirically validate our SSM-centric methodological changes through the Mamba-3 model on a host of synthetic and real world tasks. Section 4.1 compares our SISO-variant of Mamba-3 on language modeling and retrieval-based tasks, while Section 4.2 demonstrates inference efficiency of Mamba-3 and MIMO Mamba-3's benefits over SISO Mamba-3 under fixed inference compute. We ablate the impact of our new discretization and BC bias on performance and show that complexification of the SSM leads capabilities that prior SSMs such as Mamba-2 lacked in Section 4.3.

## 4.1 LANGUAGE MODELING

All models are pretrained with 100B tokens of the FineWeb-Edu dataset (Penedo et al., 2024) with the Llama-3.1 tokenizer (Grattafiori et al., 2024) at a 2K context length with the same standard training protocol. Training and evaluation details can be found in Appendix E.

Across all four model scales, Mamba-3 outperforms popular baselines at various downstream tasks (Table 1). We highlight that Mamba-3 does not utilize the short convolution that has been empirically identified as an important component in many performant linear models (Allen-Zhu, 2025).

## 4.1.1 RETRIEVAL CAPABILITIES

Beyond standard language modeling, an important measure for linear models is their retrieval ability -how well they can recall information from earlier in the sequence (Arora et al., 2025a;b). Unlike attention models, which can freely revisit past context with the growing KV cache, linear models must compress context into a fixed-size state. This trade-off is reflected in the Transformer baseline's substantially stronger retrieval scores. To evaluate Mamba-3 under this lens, Table 2 compares it against baselines on both real-world and synthetic needle-in-a-haystack (NIAH) tasks (Hsieh et al., 2024), using our pretrained 1.5B models from Section 4.1. We restrict the task sequence length to 2K tokens to match the training setup and adopt the cloze-style format for our real-world tasks to mirror the next-token-prediction objective, following Arora et al. (2025b; 2024).

Mamba-3 is competitive on real-world associative recall and question-answering but struggles when extracting information from semi-structured or unstructured data. On synthetic NIAH tasks, how-

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

Table 1: Downstream language modeling evaluations on models trained with 100B FineWeb-Edu tokens. Best results for each size are bolded , and second best are underlined. All models are trained with the same procedure. Mamba-3 outperforms Mamba-2 and others at every model scale.

| Model               | FW-Edu ppl ↓   | LAMB. ppl ↓   | LAMB. acc ↑   | HellaS. acc n ↑   | PIQA acc ↑    | Arc-E acc ↑   | Arc-C acc n ↑   | WinoGr. acc ↑   | OBQA acc ↑   | Average acc ↑   |
|---------------------|----------------|---------------|---------------|-------------------|---------------|---------------|-----------------|-----------------|--------------|-----------------|
| Transformer-180M    | 16 . 89        | 45 . 0        | 32 . 5        | 39 . 0            | 67 . 1        | 59 . 8        | 27 . 9          | 51 . 2          | 21 . 8       | 42 . 8          |
| Gated DeltaNet-180M | 16 . 61        | 35 . 9        | 33 . 7        | 40 . 2            | 66 . 8        | 59 . 6        | 28 . 5          | 51 . 2          | 21 . 6       | 43 . 1          |
| Mamba-2-180M        | 16 . 76        | 41 . 8        | 30 . 9        | 40 . 1            | 66 . 8        | 60 . 1        | 27 . 3          | 52 . 0          | 23 . 2       | 42 . 9          |
| Mamba-3-180M (SISO) | 16 . 59        | 37 . 7        | 32 . 5        | 40 . 8            | 66 . 1        | 61 . 5        | 27 . 9          | 52 . 0          | 22 . 8       | 43 . 4          |
| Transformer-440M    | 13 . 03        | 21 . 2        | 41 . 7        | 50 . 5            | 69 . 9 70 . 5 | 67 . 6 67 . 5 | 34 . 6          | 56 . 7          | 26 . 0       | 49 . 6 1        |
| Gated DeltaNet-440M | 13 . 12        | 19 . 0        | 40 . 4        | 50 . 5            |               |               | 34 . 0          | 55 . 3          | 25 . 8       | 49 .            |
| Mamba-2-440M        | 13 . 00        | 19 . 6        | 40 . 8        | 51 . 7            | 70 . 6        | 68 . 8        | 35 . 0          | 54 . 1          | 26 . 0       | 49 . 6          |
| Mamba-3-440M (SISO) | 12 . 87        | 19 . 6        | 40 . 2        | 51 . 7            | 71 . 9        | 68 . 9        | 34 . 4          | 55 . 8          | 26 . 0       | 49 . 8          |
| Transformer-880M    | 11 . 42        | 15 . 0        | 44 . 7        | 57 . 2            | 72 . 6        | 71 . 6        | 39 . 2          | 57 . 7          | 26 . 8       | 52 . 8          |
| Gated DeltaNet-880M | 11 . 39        | 12 . 7        | 47 . 1        | 57 . 5            | 72 . 6        | 72 . 5        | 38 . 8          | 57 . 9          | 30 . 6       | 53 . 9          |
| Mamba-2-880M        | 11 . 35        | 13 . 8        | 45 . 0        | 58 . 1            | 72 . 5        | 72 . 3        | 38 . 7          | 56 . 8          | 30 . 2       | 53 . 4          |
| Mamba-3-880M (SISO) | 11 . 23        | 12 . 9        | 47 . 2        | 58 . 8            | 73 . 6        | 72 . 7        | 40 . 2          | 58 . 4          | 30 . 0       | 54 . 4          |
| Transformer-1.5B    | 10 . 51        | 11 . 1        | 50 . 3        | 60 . 6            | 73 . 8        | 74 . 0        | 40 . 4          | 58 . 7          | 29 . 6       | 55 . 4          |
| Gated DeltaNet-1.5B | 10 . 51        | 10 . 8        | 49 . 9        | 60 . 5            | 74 . 3        | 73 . 3        | 40 . 4          | 61 . 5          | 30 . 4       | 55 . 7          |
| Mamba-2-1.5B        | 10 . 47        | 12 . 0        | 47 . 8        | 61 . 4            | 73 . 6        | 75 . 3        | 41 . 8          | 57 . 5          | 32 . 6       | 55 . 7          |
| Mamba-3-1.5B (SISO) | 10 . 35        | 10 . 9        | 49 . 4        | 61 . 9            | 73 . 6        | 75 . 9        | 42 . 7          | 59 . 4          | 32 . 0       | 56 . 4          |

Table 2: Retrieval capabilities measured by a mixture of real-world and synthetic retrieval tasks. Real-world retrieval tasks utilize cloze variants of the original datasets and are truncated to 2K length. Mamba-3 demonstrates strong associative recall and question-answering but suffers with information extraction of semi-structured and unstructured data. Mamba-3 has strong needle-in-a-haystack (NIAH) accuracy and generalizes outside its trained context.

| Model (1.5B)   | SWDE   | SQUAD   | FDA    | TQA    | NQ     | Drop   | NIAH-Single-1   | NIAH-Single-1   | NIAH-Single-1   | NIAH-Single-2   | NIAH-Single-2   | NIAH-Single-2   | NIAH-Single-3   | NIAH-Single-3   | NIAH-Single-3   |
|----------------|--------|---------|--------|--------|--------|--------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|
| Context Length |        |         | 2048   | 2048   |        |        | 1024            | 2048            | 4096            | 1024            | 2048            | 4096            | 1024            | 2048            | 4096            |
| Transformer    | 48 . 9 | 46 . 6  | 58 . 4 | 67 . 5 | 31 . 7 | 26 . 4 | 100 . 0         | 100 . 0         | 0 . 0           | 92 . 2          | 100 . 0         | 0 . 0           | 98 . 6          | 99 . 4          | 0 . 0           |
| Gated DeltaNet | 32 . 7 | 40 . 0  | 28 . 3 | 63 . 5 | 25 . 7 | 24 . 5 | 100 . 0         | 100 . 0         | 99 . 8          | 100 . 0         | 93 . 8          | 49 . 8          | 83 . 8          | 68 . 4          | 34 . 2          |
| Mamba-2        | 30 . 7 | 39 . 1  | 23 . 7 | 64 . 3 | 25 . 1 | 28 . 5 | 100 . 0         | 99 . 6          | 62 . 0          | 100 . 0         | 53 . 8          | 11 . 8          | 95 . 8          | 87 . 4          | 13 . 4          |
| Mamba-3 (SISO) | 28 . 5 | 40 . 1  | 23 . 4 | 64 . 5 | 26 . 5 | 27 . 4 | 100 . 0         | 100 . 0         | 88 . 2          | 100 . 0         | 95 . 4          | 50 . 6          | 92 . 4          | 81 . 4          | 34 . 2          |

ever, Mamba-3 surpasses or matches baselines on most cases and notably demonstrates markedly better out-of-distribution retrieval abilities than its Mamba-2 predecessor.

## 4.2 INFERENCE EFFICIENCY

In this section, we investigate our methodological changes in the context of inference performance. We first present our inference benchmark in Section 4.2.1; we then establish a framework for comparing the inference performance in Section 4.2.2. Finally, we focus on the effectiveness of MIMO in Section 4.2.3.

## 4.2.1 FAST MAMBA-3 KERNELS

We complement Mamba-3's methodological advances with optimized kernels that deliver fast inference in practical settings. Specifically, we implement a new series of inference kernels for Mamba3-using Triton for the forward (prefill) path and CuTe-DSL for decode-and compare their pertoken decode latency against the released Triton kernels for Mamba-2 and Gated DeltaNet (GDN) 1 in Table 3. The evaluation uses the setting: a decode step at batch size 128 on a single H100 for 1.5B-parameter models with model dimension 2048 , state dimension ∈ { 64 , 128 } in both FP32 and BF16 datatypes. Across all configurations, SISO achieves the lowest latency amongst baselines, while MIMO incurs only a minor overhead relative to SISO. This indicates that our CuTe-DSL decode implementation is competitive and that the additional components of Mamba-3 (trapezoidal update, complex-valued state, and MIMO projections) are lightweight. This supports our overall inference-first perspective: the Mamba-3 admits simple, low-latency implementation while providing strong empirical performance. A thorough analysis, including prefill and prefill with decode results are provided in Appendix H.

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

Table 3: Latency (in milliseconds) comparison across models, precision, and d state values. Both Mamba-3 SISO and MIMO are faster than the Mamba-2 and Gated DeltaNet at the commonly used bf16, d state = 128 setting.

| Model          | FP32         | FP32          | BF16         | BF16          |
|----------------|--------------|---------------|--------------|---------------|
|                | d state = 64 | d state = 128 | d state = 64 | d state = 128 |
| Mamba-2        | 0 . 295      | 0 . 409       | 0 . 127      | 0 . 203       |
| Gated DeltaNet | 0 . 344      | 0 . 423       | 0 . 176      | 0 . 257       |
| Mamba-3 (SISO) | 0 . 261      | 0 . 356       | 0 . 106      | 0 . 152       |
| Mamba-3 (MIMO) | 0 . 285      | 0 . 392       | 0 . 136      | 0 . 185       |

![Image](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAXkAAAC1CAIAAAA1PBgRAAB1hklEQVR4nO2dd3gUVdfAz/bed7ObZNN7LyQkEHoTpEoVUEEEFRSlKIjlRdBXRUSKyoeACEiRKh2kgxASQnpCQnpv23uf+f4Y3hgjSpGQBOf38PBkd+/cuTO7e/bcUwkoigIODg5OB0Ps7AXg4OD8K3iaZY3dbnc4HA8+3uVy2Ww2BEE6bkkPBYqiD3sJTxIEQWw2m8vl6uyFdDjYlTqdzr8Z43Q67XZ71/nwtMXpdD7CBxtBELvd/vdX/VCQH9dEHY3T6dy5c2dzczOKogQCwdPTs3fv3oGBgX813mQyPfPMMwKB4ODBgzQa7Z5jioqK6uvr4+LiRCIRAHzzzTdbt25dsWLFhAkTHmGF9fX1P/30E/aOEggEAEAQhEwmP//88z4+Pu0GV1RUVFZWhoeHu7u7/9WEVVVVc+fOFYvF3333HY/Ha/tSWlrayZMn6+rqBAJBWFjYc889JxaLW1pacnNzfX19g4KC/madhYWFTU1NcXFxQqHwAS8tPz//+PHjZWVlbDY7ODh47NixXl5ev/zyy/Lly2fPnr1gwYIHnOefU1ZWduDAAQBAEIRKpQYHB/fv35/P5z/g4RqNJicnRyqVhoeHP/hJz549++67706dOvX999//qzGLFi26fPnyli1bkpKSHnzmdty5c+fQoUMEAgFBEBqNFhIS0r9/fy6X+8gTYqxevXr37t1r164dOnTogx+Vmpo6b968kSNHfvbZZ0qlsqCgwNPTMzg4+NHXgXYTrFZrSEhI25WHhYXV1tb+1XidTkcmk93d3c1m81+Nefnll8lk8pkzZ7CHP/zww7Bhw06fPv1oK0xNTaVQKG1XSCAQaDTatWvX/jz4P//5D4VC+fHHH/9mwoKCApFIFBkZqVQq2z5/7do1TEx4eXlhf5w/fx5F0cOHD5NIpLfffvvv1zl9+nQKhXLu3LkHvK7KykpfX18A8PT0dHNzAwBs2adPnx42bNgPP/zwgPM8Fo4cOYLdWyLxrko+ffp0jUbzgIdfvHiRRqPNmDHjoU56+fLlZ5555ttvv/2bMR9//PHw4cNzcnIeauZ27N+/v93VzZw502Aw/JM5URSdPXs2APz8888PddTNmzeHDx/+xRdfoCh69OhRGo02f/78f7KMbqPXAACmnpw+fToqKmrkyJG5ubkXL1586aWXACAjI+PYsWO1tbUxMTGTJk2Sy+UAQCaTyWQygUDQarVbt24tKyuzWq3BwcGjR4+Oioq6ePFiRkYGpi7l5ORMnDgxMDCwT58+np6eWVlZp0+fHjhwYO/evQFg//79ZWVlL7/8sru7+/nz58+ePatSqZKSkiZMmIApRBjx8fHl5eUEAmH16tUbNmyYM2fOypUrURRtampatWpVcXGxj4/PiBEjkpKSrly5cuHCBYfDcfjw4aamppEjRzKZzF27dtXW1hIIhOjo6HHjxnl5eREIBOwS2t2H48ePq9XqNWvWLFq0yG635+Xlubu7V1RU7Nu3z+VyXb9+fdWqVfHx8T179ty8eXNZWZndbg8ODh4zZkxERMT58+czMzMdDseOHTsyMzMnT57s5+d39erVEydOKJXKpKSk8ePHSySStqc7efJkVVXVggUL1q5d63K5cnNzMSVLKpX26dPHz8/PYrHs2bOnoaGBSCSSSCQAePbZZ6OjoysqKo4cOZKfny+XyydMmBAbG9t22kuXLqWlpY0cOTI6Otpms+3du1en073wwgsNDQ2HDx+uqKgQCARJSUljx45lMpmtR2Hz9+vX79ixY7dv354yZcru3btnz54dEBCwc+fO0NBQl8t17dq1hQsXurm5HT9+/PLlyyQSacSIESNGjGhqavrpp59sNtutW7c++eST+Pj4mJiYvXv3enp6crnckydPvv766waD4fjx483NzRwOp0+fPiNHjmSz2WKxOCUlJSAgAAAuXLiQlpaWkpKSm5tbXFw8ZMiQ0aNHU6nU0NBQEokkEAgsFsuuXbsQBPH39z9z5gyZTH7hhReioqIAoLCwcM+ePTabbdiwYeXl5RQK5fnnn2ez2e2ubvDgwUePHs3MzJwyZcpPP/00c+bM/v37FxQUHDt2rKSkJDg4eOLEicHBwU6nc9u2bQaDoXfv3r/88kt8fHxQUNCvv/6amJh4586dgoKCfv36jR8/nk6nY9NiurbFYjl58uTly5cRBBkwYMDYsWOpVOqePXtqa2unTJni5+d38ODB27dvT506FbvqiIiIysrK3bt322y21NTUTz/9NC4urq6uzmQyvf7660wms6amZu/evf7+/hMnTsRO8Zf8E0H1JLFardHR0QBw7tw5rVabkJBAJBIvXLiAoujJkyfFYrG3t/fEiRNp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13t7e1dWVj733HPPPPNMTU2Nh4cHk8l86623eDxeO51r5syZXC43KysLMyGNHj0akzW9e/feu3fvhQsXLBYLn89///33yWRyVlZWUlLSyJEjMzIyIiMjAWDRokUSieT27dscDodGo7366qu+vr4///xzS0uLUCgcOXIkpou1MnbsWIfDkZGR0dLSEhQU9Oyzz06cOBEAYmNj33777f79+9Pp9FdffVWlUmHfWwKBwOfzfX19z507t2PHjqysLAKB8Oyzz44ZM6bdjSIQCO+//763t3dAQAAWlkKn05977rmcnByNRjNw4MDJkyf37du37SGBgYHz588PDw9v3SNjBAcHz5s3r3UwmUz+8ccfn3322ZMnTxoMhvDw8FGjRpHJZF9f3yNHjpw9e1atVkskEk9Pz3fffRcz5QKAh4fHvn37tm7diqLosmXL+vTpw+VyCQRCWFjYggULsDdu8ODBTqcTu5NJSUnz589vfUPDwsK8vb0ZDMarr77qdDp5PB6JRHrppZeamprEYrFYLD5y5MiBAwesVqu3t/cbb7xBo9GwvU8rISEhmNDHFJbW5/v373/mzJmdO3cWFxczmcxJkyYNGTIERdHXX39do9G0mwT7MeNyuc8+++yMGTMAYPjw4RQKJTQ0lEwmf/PNNykpKadOndLr9QEBAaNGjWIymQqF4t133128eLFUKt2xY8e5c+fu3LkTFBS0cOHCHj16AEBkZOShQ4cuXbqk0WiwuAcWi/Xiiy8uWbJk+PDh2DP3574WHRwcnH+OxWJ59913ly9fvn79+uTkZABYsWLF4z0FZo9ftWrV4532z6hUqh9++CEpKYlOpxcWFj7gUd1Gr8HB6dZgvogzZ85glvI1a9bMnz//8Z7C39+/X79+fw5Sf+xoNBos7PC777578Ajsu3YjHBycJ4DBYLBarUKhsJ1V+7GA5WRRqdQ/x38+9hNpNBo6nc7hcB78KFzW4ODgPAme5jxvHBycrsOj6FpmszkzM7OmpiYuLg7brel0uosXL2JBn76+vpgLBsNisZw7d66goIDNZo8ePRqLMmjF5XKdPXs2PDz8CWwycXBwOpFH0Wtqa2v37t37xRdf7Nu3D3umqqrq008/bWxsVCqVWq227eC6urpff/1VJpPV1dXNnj1bpVK1fdVqtY4bNw6LHMfBwXmKeRS9JigoaMOGDatWrWob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)

Figure 3: Exploration of state size (inference speed proxy) versus pretraining perplexity (performance proxy) across different Mamba variants. Mamba-3 MIMO drives the-Pareto frontier without increasing state size.

## 4.2.2 PARETO FRONTIER FOR INFERENCE EFFICIENCY

For Mamba and many variants of sub-quadratic models, the generation of tokens during decoding is heavily dominated by memory I/O due to the low arithmetic intensity of computing the recurrent update (c.f. Section 3.3). Furthermore, among the data being transferred, the latent state H t dominates in terms of size. Indeed, from Table 3, we see that the runtime scales with d state, which configures the size of the hidden state.

As d state dominates the decode runtime for the subquadratic models considered in this paper, we opt to use it as a proxy for inference speed. By plotting the validation perplexity (itself a proxy for model performance) as a function of d state, we aim to formulate a holistic picture about how the subquadratic models can trade off performance with inference speed.

Figure 3 shows such a Pareto front for the Mamba variants models considered in this paper. For each data point, we train a 440M parameter model to 2 × Chinchilla optimal tokens on the Fineweb-Edu dataset, where the model is configured with a d state of { 16 , 32 , 64 , 128 } . As expected, we observe an inverse correlation between validation loss and d state; moreover, we noticed a general downward shift on the Pareto front moving from Mamba-2 to Mamba-3. A further downward shift is observed when moving from the SISO variant of Mamba-3 to the MIMO variant of Mamba-3 (where we set the Mimo rank r = 4 and decrease our MLP inner dimension to parameter match the SISO variants). We expand the comparison to include the Gated DeltaNet baseline in Figure 7. The results highlight both the expressivity gain coming our methodology change as well as the effectiveness of the MIMO mechanism in improving decoding efficiency.

## 4.2.3 MIMO ENHANCES INFERENCE EFFICIENCY

MIMO, with its higher arithmetic intensity, increases the decoding FLOPs without significantly increasing decode runtime (Table 3) 2 The implication is that any performance gain from MIMO translates into efficiency gain in decoding: a conclusion supported by the downward shift of the MIMO pareto curve we observed in Section 4.2.2.

We aim to further verify the gain from MIMO by investigating its language-modeling capabilities. To that end, we train a 440M and 820M parameter MIMO models with MIMO rank r = 4 on 100B tokens on Fineweb-Edu (i.e., same setting as the 440M parameter run in Section 4.1; we are currently training the 1.5B model). To ensure the total parameter count equals SISO, we decrease the inner dimension of the MLP layers to compensate for the increase due to the MIMO projections.

On both validation perplexity and our suite of language evaluation tasks (Table 6), we see significant gain when moving from SISO to MIMO. Namely, we attain a perplexity gain of 0 . 16 on the 100B tokens run, and Figure 3 illustrates the downward shift in our validation loss. On the language evaluation front, we see significant gain on most tasks when compared to SISO, resulting in an overall gain of 1.2 point over SISO. This strongly supports MIMO as a SSM-centric technique to improve model quality without compromising decoding speed.

1 Details on each kernel DSL and the exact kernel fusion structure is provided in Appendix H.

2 The kernel for MIMO Mamba-3 in fact fuses the MIMO projection, and so the reported wall clock time is actually an overestimate for the pure SSM update.

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

Table 4: Left : Ablations on core modeling components of Mamba-3, results on test split of dataset. A combination of our BC bias and trapezoidal discretization makes the convolution optional. Right : Formal language evaluation (scaled accuracy, %). Higher is better. Models are trained on short sequences and evaluated on longer lengths to test length generalization. For Gated DeltaNet we report the variant with eigenvalue range [ -1 , 1] .

| Model Variant (SISO)   | ppl ↓   |
|------------------------|---------|
| Mamba-3 - bias - trap  | 16 . 68 |
| Mamba-3 - bias         | 16 . 49 |
| Mamba-3                | 15 . 72 |
| Mamba-3 + conv         | 15 . 85 |

(a) Component ablation (350M).

| Model                  | Parity ↑   | Arith. w/o ↑ brackets   | Arith. w/ ↑ brackets   |
|------------------------|------------|-------------------------|------------------------|
| Mamba-3                | 100 . 00   | 98 . 51                 | 87 . 75                |
| Mamba-3 (w/o RoPE)     | 2 . 27     | 1 . 49                  | 0 . 72                 |
| Mamba-3 (w/ Std. RoPE) | 1 . 56     | 20 . 70                 | 2 . 62                 |
| Mamba-2                | 0 . 90     | 47 . 81                 | 0 . 88                 |
| Gated DeltaNet [-1,1]  | 100 . 00   | 99 . 25                 | 93 . 50                |

(b) Performance comparison on formal language tasks. Results show that unlike Mamba-2, Mamba-3 features state tracking ability stemming from data-dependent RoPE embeddings. We used Mamba-3 (SISO) for these ablations.

## 4.3 SSM-CENTRIC METHODOLOGICAL ABLATIONS

Table 4a ablates the changes made to the core SSM component, mainly the introduction of BC bias and trapezoidal discretization. We report the pretraining test perplexity on models at the 440M scale, trained for Chinchilla optimal tokens. We find that the bias and trapezoidal SSM synergize well and make the short convolution utilized by many current linear models redundant.

We empirically demonstrate that data-dependent RoPE in Mamba-3 enables state tracking. Following Grazzi et al. (2025), we evaluate on tasks from the Chomsky hierarchy-Parity, Modular Arithmetic (without brackets), and Modular Arithmetic (with brackets)-and report scaled accuracies in Table 4b. Mamba-3 solves Parity and Modular Arithmetic (without brackets), and nearly closes the accuracy gap on Modular Arithmetic (with brackets). In contrast, Mamba-3 without RoPE, Mamba3 with standard RoPE (Su et al., 2023), and Mamba-2 fail to learn these tasks. We use the statetracking-enabled Gated DeltaNet variant of and observe that Mamba-3 is competitive-matching parity and approaching its performance on both modular-arithmetic tasks. Experimental settings are covered in Appendix E.

## 5 CONCLUSION AND FUTURE WORK

We introduce Mamba-3, an SSM model with three axes of improvement rooted in SSM principles: (i) improved quality , via trapezoidal discretization; (ii) new capabilities , through complex SSMs that recover state-tracking; and (iii) higher inference efficiency , with a MIMO formulation that raises arithmetic intensity. Mamba-3 delivers strong language modeling results and establishes a new Pareto frontier on the performance-efficiency axes with respect to strong baseline models. A limitation remains in retrieval, where fixed-state architectures lags attention-based models. We see hybrid Mamba-3 architectures that integrate retrieval mechanisms as a promising path, alongside broader application of our design principles to linear-time sequence models.

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

## REFERENCES

- Zeyuan Allen-Zhu. Physics of Language Models: Part 4.1, Architecture Design and the Magic of Canon Layers. SSRN Electronic Journal , May 2025. https://ssrn.com/abstract= 5240330 .
- Aryaman Arora, Neil Rathi, Nikil Roashan Selvam, R´ obert Csord´ as, Dan Jurafsky, and Christopher Potts. Mechanistic evaluation of transformers and state space models, 2025a. URL https: //arxiv.org/abs/2505.15105 .
- Simran Arora, Aman Timalsina, Aaryan Singhal, Benjamin Spector, Sabri Eyuboglu, Xinyi Zhao, Ashish Rao, Atri Rudra, and Christopher R´ e. Just read twice: closing the recall gap for recurrent language models, 2024. URL https://arxiv.org/abs/2407.05483 .
- Simran Arora, Sabri Eyuboglu, Michael Zhang, Aman Timalsina, Silas Alberti, Dylan Zinsley, James Zou, Atri Rudra, and Christopher R´ e. Simple linear attention language models balance the recall-throughput tradeoff, 2025b. URL https://arxiv.org/abs/2402.18668 .
- Aviv Bick, Kevin Y. Li, Eric P. Xing, J. Zico Kolter, and Albert Gu. Transformers to ssms: Distilling quadratic knowledge to subquadratic models, 2025a. URL https://arxiv.org/abs/ 2408.10189 .
- Aviv Bick, Eric Xing, and Albert Gu. Understanding the skill gap in recurrent language models: The role of the gather-and-aggregate mechanism, 2025b. URL https://arxiv.org/abs/ 2504.18574 .
- Yonatan Bisk, Rowan Zellers, Ronan Le Bras, Jianfeng Gao, and Yejin Choi. Piqa: Reasoning about physical commonsense in natural language, 2019. URL https://arxiv.org/abs/1911. 11641 .
- Krzysztof Choromanski, Valerii Likhosherstov, David Dohan, Xingyou Song, Andreea Gane, Tamas Sarlos, Peter Hawkins, Jared Davis, Afroz Mohiuddin, Lukasz Kaiser, David Belanger, Lucy Colwell, and Adrian Weller. Rethinking attention with performers, 2022. URL https:// arxiv.org/abs/2009.14794 .
- Peter Clark, Isaac Cowhey, Oren Etzioni, Tushar Khot, Ashish Sabharwal, Carissa Schoenick, and Oyvind Tafjord. Think you have solved question answering? try arc, the ai2 reasoning challenge, 2018. URL https://arxiv.org/abs/1803.05457 .
- Tri Dao and Albert Gu. Transformers are ssms: Generalized models and efficient algorithms through structured state space duality, 2024. URL https://arxiv.org/abs/2405.21060 .
- Dheeru Dua, Yizhong Wang, Pradeep Dasigi, Gabriel Stanovsky, Sameer Singh, and Matt Gardner. Drop: A reading comprehension benchmark requiring discrete reasoning over paragraphs, 2019. URL https://arxiv.org/abs/1903.00161 .
- Christopher Fleetwood. Domain specific architectures for ai inference. URL https:// fleetwood.dev/posts/domain-specific-architectures .
- Leo Gao, Jonathan Tow, Baber Abbasi, Stella Biderman, Sid Black, Anthony DiPofi, Charles Foster, Laurence Golding, Jeffrey Hsu, Alain Le Noac'h, Haonan Li, Kyle McDonell, Niklas Muennighoff, Chris Ociepa, Jason Phang, Laria Reynolds, Hailey Schoelkopf, Aviya Skowron, Lintang Sutawika, Eric Tang, Anish Thite, Ben Wang, Kevin Wang, and Andy Zou. The language model evaluation harness, 07 2024. URL https://zenodo.org/records/12608602 .

Madan Gopal. Modern control system theory . New Age International, 1993.

- Aaron Grattafiori, Abhimanyu Dubey, Abhinav Jauhri, Abhinav Pandey, Abhishek Kadian, Ahmad Al-Dahle, Aiesha Letman, Akhil Mathur, Alan Schelten, Alex Vaughan, Amy Yang, Angela Fan, Anirudh Goyal, Anthony Hartshorn, Aobo Yang, Archi Mitra, Archie Sravankumar, Artem Korenev, Arthur Hinsvark, Arun Rao, Aston Zhang, and et. al. The llama 3 herd of models, 2024. URL https://arxiv.org/abs/2407.21783 .

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

- Riccardo Grazzi, Julien Siems, Simon Schrodi, Thomas Brox, and Frank Hutter. Is mamba capable of in-context learning?, 2024. URL https://arxiv.org/abs/2402.03170 .
- Riccardo Grazzi, Julien Siems, Arber Zela, J¨ org K. H. Franke, Frank Hutter, and Massimiliano Pontil. Unlocking state-tracking in linear rnns through negative eigenvalues, 2025. URL https: //arxiv.org/abs/2411.12537 .
- Albert Gu and Tri Dao. Mamba: Linear-time sequence modeling with selective state spaces, 2024. URL https://arxiv.org/abs/2312.00752 .
- Albert Gu, Karan Goel, and Christopher R´ e. Efficiently modeling long sequences with structured state spaces, 2022a. URL https://arxiv.org/abs/2111.00396 .
- Albert Gu, Ankit Gupta, Karan Goel, and Christopher R´ e. On the parameterization and initialization of diagonal state space models. arXiv preprint arXiv:2206.11893 , 2022b. URL https:// arxiv.org/abs/2206.11893 .
- Ankit Gupta, Albert Gu, and Jonathan Berant. Diagonal state spaces are as effective as structured state spaces, 2022. URL https://arxiv.org/abs/2203.14343 .
- Alex Henry, Prudhvi Raj Dachapally, Shubham Pawar, and Yuxuan Chen. Query-key normalization for transformers, 2020. URL https://arxiv.org/abs/2010.04245 .
- Cheng-Ping Hsieh, Simeng Sun, Samuel Kriman, Shantanu Acharya, Dima Rekesh, Fei Jia, Yang Zhang, and Boris Ginsburg. Ruler: What's the real context size of your long-context language models?, 2024. URL https://arxiv.org/abs/2404.06654 .
- Samy Jelassi, David Brandfonbrener, Sham M. Kakade, and Eran Malach. Repeat after me: Transformers are better than state space models at copying, 2024. URL https://arxiv.org/ abs/2402.01032 .
- Mandar Joshi, Eunsol Choi, Daniel S. Weld, and Luke Zettlemoyer. Triviaqa: A large scale distantly supervised challenge dataset for reading comprehension, 2017. URL https://arxiv.org/ abs/1705.03551 .
- Rudolph Emil Kalman. A new approach to linear filtering and prediction problems. 1960.
- Angelos Katharopoulos, Apoorv Vyas, Nikolaos Pappas, and Franc ¸ois Fleuret. Transformers are rnns: Fast autoregressive transformers with linear attention, 2020. URL https://arxiv. org/abs/2006.16236 .
- Tom Kwiatkowski, Jennimaria Palomaki, Olivia Redfield, Michael Collins, Ankur Parikh, Chris Alberti, Danielle Epstein, Illia Polosukhin, Jacob Devlin, Kenton Lee, Kristina Toutanova, Llion Jones, Matthew Kelcey, Ming-Wei Chang, Andrew M. Dai, Jakob Uszkoreit, Quoc Le, and Slav Petrov. Natural questions: A benchmark for question answering research. Transactions of the Association for Computational Linguistics , 7:452-466, 2019. doi: 10.1162/tacl a 00276. URL https://aclanthology.org/Q19-1026/ .
- Woosuk Kwon, Zhuohan Li, Siyuan Zhuang, Ying Sheng, Lianmin Zheng, Cody Hao Yu, Joseph E. Gonzalez, Hao Zhang, and Ion Stoica. Efficient memory management for large language model serving with pagedattention, 2023. URL https://arxiv.org/abs/2309.06180 .
- Baolin Li, Yankai Jiang, Vijay Gadepally, and Devesh Tiwari. Llm inference serving: Survey of recent advances and opportunities, 2024. URL https://arxiv.org/abs/2407.12391 .
- William Merrill, Jackson Petty, and Ashish Sabharwal. The illusion of state in state-space models, 2025. URL https://arxiv.org/abs/2404.08819 .
- Todor Mihaylov, Peter Clark, Tushar Khot, and Ashish Sabharwal. Can a suit of armor conduct electricity? a new dataset for open book question answering, 2018. URL https://arxiv. org/abs/1809.02789 .

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

- Team OLMo, Pete Walsh, Luca Soldaini, Dirk Groeneveld, Kyle Lo, Shane Arora, Akshita Bhagia, Yuling Gu, Shengyi Huang, Matt Jordan, Nathan Lambert, Dustin Schwenk, Oyvind Tafjord, Taira Anderson, David Atkinson, Faeze Brahman, Christopher Clark, Pradeep Dasigi, Nouha Dziri, Michal Guerquin, and et. al. 2 olmo 2 furious, 2025. URL https://arxiv.org/ abs/2501.00656 .
- Antonio Orvieto, Samuel L Smith, Albert Gu, Anushan Fernando, Caglar Gulcehre, Razvan Pascanu, and Soham De. Resurrecting recurrent neural networks for long sequences, 2023. URL https://arxiv.org/abs/2303.06349 .
- Daniele Paliotta, Junxiong Wang, Matteo Pagliardini, Kevin Y. Li, Aviv Bick, J. Zico Kolter, Albert Gu, Franc ¸ois Fleuret, and Tri Dao. Thinking slow, fast: Scaling inference compute with distilled reasoners, 2025. URL https://arxiv.org/abs/2502.20339 .
- Denis Paperno, Germ´ an Kruszewski, Angeliki Lazaridou, Quan Ngoc Pham, Raffaella Bernardi, Sandro Pezzelle, Marco Baroni, Gemma Boleda, and Raquel Fern´ andez. The lambada dataset: Word prediction requiring a broad discourse context, 2016. URL https://arxiv.org/ abs/1606.06031 .
- Jongho Park, Jaeseung Park, Zheyang Xiong, Nayoung Lee, Jaewoong Cho, Samet Oymak, Kangwook Lee, and Dimitris Papailiopoulos. Can mamba learn how to learn? a comparative study on in-context learning tasks, 2024. URL https://arxiv.org/abs/2402.04248 .
- Guilherme Penedo, Hynek Kydl´ ıˇ cek, Loubna Ben allal, Anton Lozhkov, Margaret Mitchell, Colin Raffel, Leandro Von Werra, and Thomas Wolf. The fineweb datasets: Decanting the web for the finest text data at scale, 2024. URL https://arxiv.org/abs/2406.17557 .
- Bo Peng, Ruichong Zhang, Daniel Goldstein, Eric Alcaide, Xingjian Du, Haowen Hou, Jiaju Lin, Jiaxing Liu, Janna Lu, William Merrill, Guangyu Song, Kaifeng Tan, Saiteja Utpala, Nathan Wilce, Johan S. Wind, Tianyi Wu, Daniel Wuttke, and Christian Zhou-Zheng. Rwkv-7 'goose' with expressive dynamic state evolution, 2025. URL https://arxiv.org/abs/2503. 14456 .
- Pranav Rajpurkar, Jian Zhang, and Percy Liang. Know what you don't know: Unanswerable questions for squad. In ACL 2018 , 2018.
- Yuval Ran-Milo, Eden Lumbroso, Edo Cohen-Karlik, Raja Giryes, Amir Globerson, and Nadav Cohen. Provable benefits of complex parameterizations for structured state space models, 2024. URL https://arxiv.org/abs/2410.14067 .
- Keisuke Sakaguchi, Ronan Le Bras, Chandra Bhagavatula, and Yejin Choi. Winogrande: An adversarial winograd schema challenge at scale, 2019. URL https://arxiv.org/abs/1907. 10641 .
- Yash Sarrof, Yana Veitsman, and Michael Hahn. The expressive capacity of state space models: A formal language perspective, 2024. URL https://arxiv.org/abs/2405.17394 .
- Imanol Schlag, Kazuki Irie, and J¨ urgen Schmidhuber. Linear transformers are secretly fast weight programmers, 2021. URL https://arxiv.org/abs/2102.11174 .
- Julien Siems, Timur Carstensen, Arber Zela, Frank Hutter, Massimiliano Pontil, and Riccardo Grazzi. Deltaproduct: Improving state-tracking in linear rnns via householder products, 2025. URL https://arxiv.org/abs/2502.10297 .
- Jimmy T. H. Smith, Andrew Warrington, and Scott W. Linderman. Simplified state space layers for sequence modeling, 2023. URL https://arxiv.org/abs/2208.04933 .
- Charlie Snell, Jaehoon Lee, Kelvin Xu, and Aviral Kumar. Scaling llm test-time compute optimally can be more effective than scaling model parameters, 2024. URL https://arxiv.org/ abs/2408.03314 .
- Jianlin Su, Yu Lu, Shengfeng Pan, Ahmed Murtadha, Bo Wen, and Yunfeng Liu. Roformer: Enhanced transformer with rotary position embedding, 2023. URL https://arxiv.org/abs/ 2104.09864 .

- Yutao Sun, Li Dong, Shaohan Huang, Shuming Ma, Yuqing Xia, Jilong Xue, Jianyong Wang, and Furu Wei. Retentive network: A successor to transformer for large language models, 2023. URL https://arxiv.org/abs/2307.08621 .
- Endre S¨ uli and David F. Mayers. An Introduction to Numerical Analysis . Cambridge University Press, 2003.
- Gemma Team, Aishwarya Kamath, Johan Ferret, Shreya Pathak, Nino Vieillard, Ramona Merhej, Sarah Perrin, Tatiana Matejovicova, Alexandre Ram´ e, Morgane Rivi` ere, Louis Rouillard, Thomas Mesnard, Geoffrey Cideron, Jean bastien Grill, Sabela Ramos, Edouard Yvinec, Michelle Casbon, Etienne Pot, Ivo Penchev, Ga¨ el Liu, and et. al. Gemma 3 technical report, 2025. URL https: //arxiv.org/abs/2503.19786 .
- M. Tenenbaum and H. Pollard. Ordinary Differential Equations: An Elementary Textbook for Students of Mathematics, Engineering, and the Sciences . Dover Books on Mathematics. Dover Publications, 1985. ISBN 9780486649405. URL https://books.google.com/books?id= iU4zDAAAQBAJ .
- Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N Gomez, Łukasz Kaiser, and Illia Polosukhin. Attention is all you need. In Advances in neural information processing systems , pp. 5998-6008, 2017. URL http://arxiv.org/abs/1706.03762 .
- Johannes von Oswald, Nino Scherrer, Seijin Kobayashi, Luca Versari, Songlin Yang, Maximilian Schlegel, Kaitlin Maile, Yanick Schimpf, Oliver Sieberling, Alexander Meulemans, Rif A. Saurous, Guillaume Lajoie, Charlotte Frenkel, Razvan Pascanu, Blaise Ag¨ uera y Arcas, and Jo˜ ao Sacramento. Mesanet: Sequence modeling by locally optimal test-time training, 2025. URL https://arxiv.org/abs/2506.05233 .
- Mitchell Wortsman, Peter J. Liu, Lechao Xiao, Katie Everett, Alex Alemi, Ben Adlam, John D. CoReyes, Izzeddin Gur, Abhishek Kumar, Roman Novak, Jeffrey Pennington, Jascha Sohl-dickstein, Kelvin Xu, Jaehoon Lee, Justin Gilmer, and Simon Kornblith. Small-scale proxies for large-scale transformer training instabilities, 2023. URL https://arxiv.org/abs/2309.14322 .
- Yangzhen Wu, Zhiqing Sun, Shanda Li, Sean Welleck, and Yiming Yang. Inference scaling laws: An empirical analysis of compute-optimal inference for problem-solving with language models, 2025. URL https://arxiv.org/abs/2408.00724 .
- Songlin Yang, Jan Kautz, and Ali Hatamizadeh. Gated delta networks: Improving mamba2 with delta rule, 2025a. URL https://arxiv.org/abs/2412.06464 .
- Songlin Yang, Bailin Wang, Yu Zhang, Yikang Shen, and Yoon Kim. Parallelizing linear transformers with the delta rule over sequence length, 2025b. URL https://arxiv.org/abs/ 2406.06484 .
- Annan Yu and N. Benjamin Erichson. Block-biased mamba for long-range sequence processing, 2025. URL https://arxiv.org/abs/2505.09022 .
- Rowan Zellers, Ari Holtzman, Yonatan Bisk, Ali Farhadi, and Yejin Choi. Hellaswag: Can a machine really finish your sentence?, 2019. URL https://arxiv.org/abs/1905.07830 .

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

LLMUsage. We utilized Large Language Models to polish the writing in our submission as well as generate latex code for formatting tables and figures.

## A RELATED WORK

Linear-time sequence mixers. State-space models (SSMs) provide linear-time sequence mixing through explicit dynamical states and efficient scan/convolution implementations, offering significant computational advantages over quadratic-time attention mechanisms (Gu et al., 2022a; Smith et al., 2023; Gupta et al., 2022). Mamba-1 (Gu &amp; Dao, 2024) introduced input-dependent selectivity to SSMs, while Mamba-2 (Dao &amp; Gu, 2024) formalized the connection between SSMs and attention via structured state-space duality (SSD) (Katharopoulos et al., 2020; Choromanski et al., 2022). Despite matching transformers on standard language understanding benchmarks, these recurrent models exhibit limitations on tasks requiring precise algorithmic reasoning. Recent evaluations identified gaps in capabilities such as associative retrieval (Bick et al., 2025b; Arora et al., 2025a), exact copying (Jelassi et al., 2024), and in-context learning (Park et al., 2024; Grazzi et al., 2024). To address these limitations, DeltaNet enhances linear attention by replacing additive updates with delta-rule recurrence (Schlag et al., 2021), with recent work developing hardware-efficient, sequence-parallel training algorithms for this architecture (Yang et al., 2025b). This has catalyzed a broader effort to improve the algorithmic capabilities of linear-time models through architectural innovations including gating mechanisms, improved state transition dynamics, and hybrid approaches (Peng et al., 2025; Siems et al., 2025; Yang et al., 2025a; Paliotta et al., 2025; Bick et al., 2025a).

Expressivity and state tracking in recurrent mixers. Recent work characterizes the types of state that recurrent, constant-memory mixers can maintain, revealing algorithmic deficiencies in previous SSM-based models. Merrill et al. (2025) show that under finite precision, practical SSMs collapse to TC 0 , leading to failures on tasks like permutation composition over S 5 unless the primitive is extended. Similarly, Yu &amp; Erichson (2025) prove that a single-layer Mamba is not a universal approximator. Several modifications have been proposed to improve expressivity. For instance, the same work shows that a block-biased variant regains the universal approximation property with only minor changes, either through block decomposition or a channel-specific bias. Allowing negative eigenvalues or non-triangular transitions enables linear RNNs-including diagonal and Householder/DeltaNet forms-to capture parity and, under mild assumptions, regular languages (Grazzi et al., 2025). Complex-valued parameterizations provide another avenue for enhanced expressivity. Diagonal LTI SSMs demonstrate effectiveness for language modeling (Gu et al., 2022b; Orvieto et al., 2023), with complex variants achieving equivalent functions using smaller, well-conditioned parameters (Ran-Milo et al., 2024). However, the introduction of selectivity-the central innovation of modern SSMs (Gu &amp; Dao, 2024)-narrowed the performance gap with Transformers by enabling input-dependent dynamics and achieving state-of-the-art results on language modeling benchmarks, leading practitioners to abandon complex states in favor of simpler real-valued architectures. We extend this line of work by reintroducing complex-valued state evolution that yields a real SSM with doubled dimensionality and block-diagonal rotations applied to the update rule-analogous through SSD (Dao &amp; Gu, 2024) to how RoPE (Su et al., 2023) applies complex rotations to queries and keys in attention. The resulting data-dependent rotational structure expands stable dynamics to include oscillatory modes, enabling richer states while maintaining constant memory and linear-time complexity.

## B TRAPEZOIDAL DISCRETIZATION

Proposition 5 (Variation of Constants (Tenenbaum &amp; Pollard, 1985)) . Consider the linear SSM

<!-- formula-not-decoded -->

where h ( t ) ∈ R N , A ( t ) ∈ R is a scalar decay, and B ( t ) x ( t ) ∈ R N . For ∆ t discretized time grid τ t = τ t -1 +∆ t , the hidden state satisfies

<!-- formula-not-decoded -->

Proof. Since A ( t ) is scalar, the homogeneous system ˙ h ( t ) = A ( t ) h ( t ) has solution

<!-- formula-not-decoded -->

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

The Variation of Constants formula gives us,

<!-- formula-not-decoded -->

Setting ( s, t ) = ( t k -1 , t k ) yields the exact h t given h t -1 . We approximate ∫ t s A ( ξ ) dξ by setting A ( τ ) ≈ A k over [ t k -1 , t k ] , which gives us,

<!-- formula-not-decoded -->

Substituting these approximations in the Variation of Constants integral, we get the approximation

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

## B.1 TRAPEZOID DISCRETIZATION'S MASK MATRIX

Proof. When viewing the tensor contraction form, let us call C = ( T, N ) , B = ( S, N ) , L = ( T, S ) , X = ( S, P ) based on the Mamba-2 paper. With this decomposition of our mask, we can view L = contract ( TZ,ZS → TS )( L 1 , L 2 ) .

The original contraction can be seen as

<!-- formula-not-decoded -->

We can now view it as

<!-- formula-not-decoded -->

This can be broken into the following:

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

Thus, we can view this step: contract ( ZS,SNP → ZNP )( L 2 , Z ) as a conv of size two applied on Bx with the traditional SSD L = L 1 matrix.

## B.2 TRAPEZOIDAL DISCRETIZATION ERROR RATE

Standard assumptions. We assume that: A ( t ) , B ( t ) , x ( t ) are bounded and C 2 on each timestep, so that g ( τ ) has two bounded derivatives; the map h ↦→ A ( t ) h + B ( t ) x ( t ) is Lipschitz in h which is true for linear systems; λ t lies in a bounded interval so that the update is zero-stable.

Proof. Let g ( τ ) := e ( t k -τ ) A k B ( τ ) x ( τ ) denote the integrand in the second term of Proposition 5. Since A ( t ) , B ( t ) , x ( t ) are C 2 on [ t k -1 , t k ] , the function g has two bounded derivatives. A secondorder Taylor expansion of g around t k -1 gives us,

<!-- formula-not-decoded -->

Recall that the trapezoidal approximation to this integral is given by,

<!-- formula-not-decoded -->

Expanding g ( t k ) using Taylor expansion: g ( t k ) = g ( t k -1 ) + ∆ t g ′ ( t k -1 ) + ∆ 2 t 2 g ′′ ( t k -1 ) + O (∆ 3 t ) . Substituting this into Q λ ,

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

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

Hence, the error is given by:

<!-- formula-not-decoded -->

Under the assumption that λ t = 1 2 + c t ∆ t , where c t = O (1) , then 1 2 -λ t = -c t ∆ t = O (∆ t ) and thus the ∆ 2 t term is O (∆ 3 t ) . Therefore,

<!-- formula-not-decoded -->

which yields an O (∆ 3 t ) local truncation error. Since the update h k = e ∆ t A k h k -1 + Q λ is linear and zero-stable for bounded λ t , standard numerical ODE results imply an O (∆ 2 t ) global error.

## B.3 TRAPEZOIDAL PARAMETERIZATION

Table 5: Ablations on λ t parameterization in the trapezoidal update.

| Parameterization     | Form of λ t   |   ppl ↓ |
|----------------------|---------------|---------|
| Default              | σ ( u t )     |   15.72 |
| Fixed 1 / 2          | 1 2           |   15.76 |
| No trapezoid (Euler) | 1             |   15.81 |

Setting: All runs use the Mamba-3 (SISO) 440M model trained at Chinchilla scale, with the other architectural and optimization hyperparameters being the same as in Table 1.

The default model uses a data-dependent gate λ t = σ ( u t ) , where u t is a learned projection of the current input token. In Table 5, we try different parameterizations for λ t and find that the default parameterization empirically performs the best. Hence we choose the simpler default parameterization that does not enforce the O ( 1 2 +∆ t ) .

## C COMPLEX SSM PROOFS

## C.1 PROOF OF PROPOSITION 2

Proposition 2 (Complex-to-Real SSM Equivalence) . Consider a complex-valued SSM

<!-- formula-not-decoded -->

where h ( t ) ∈ C N/ 2 , θ ( t ) , B ( t ) , ˆ B ( t ) , C ( t ) , ˆ C ( t ) ∈ R N/ 2 , and x ( t ) , A ( t ) ∈ R . Under Euler discretization, this system is equivalent to a real-valued SSM

<!-- formula-not-decoded -->

with state h t ∈ R N , projections

<!-- formula-not-decoded -->

and a transition matrix

<!-- formula-not-decoded -->

Proof. We first present the derivation for N = 2 ; the block-diagonal structure for general even N follows by grouping pairs of coordinates.

Let h t + i ˆ h t denote the complexified hidden state, with parameters A ( t )+ iθ ( t ) and B ( t )+ i ˆ B ( t ) for the transition and input, respectively. By the variation of constants formula (Proposition 5), applying zero-order hold and Euler's rule over a step [ t k -1 , t k ] gives

<!-- formula-not-decoded -->

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

Expanding the exponential,

<!-- formula-not-decoded -->

so in real coordinates h t = [ h t ˆ h t ] ∈ R 2 the recurrence becomes

<!-- formula-not-decoded -->

Stacking across N/ 2 such pairs yields the block-diagonal transition

<!-- formula-not-decoded -->

For the output,

<!-- formula-not-decoded -->

which defines the real projection C t ∈ R N in the proposition. This proves the equivalence between complex SSM and the real block-diagonal system with rotations.

## C.2 PROOF OF PROPOSITION 3

Proposition 3 (Complex SSM, Data-Dependent RoPE Equivalence) . Under the notation established in Proposition 2, consider the real SSM defined in Eq. 7 unrolled for T time-steps. The output of the above SSM is equivalent to that of a vanilla scalar transition matrix-based SSM (Eq. 2) with a data-dependent rotary embedding applied on the B , C components of the SSM defined as:

<!-- formula-not-decoded -->

where the matrix production represents right matrix multiplication, e.g., ∏ 1 i =0 R i = R 0 R 1 . We denote employing the vanilla SSM to compute the Complex SSM as 'RoPE trick'.

Proof. Consider the SSM

<!-- formula-not-decoded -->

where (as in Proposition 3) A t ∈ R is a scalar (so that e ∆ t A t is a scalar and commutes with rotations), and R t is block-diagonal orthogonal/unitary, hence R -1 t = R ⊤ t .

Unrolling the recurrence with the convention that an empty product is the identity,

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

Using unitarity property,

<!-- formula-not-decoded -->

Thus

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

Since e ∆ s A s are scalars, they commute with rotations; hence

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

Define the rotated parameters ¯ C t := ( ∏ t s =0 R ⊤ s ) C t and ¯ B i := ( ∏ i s =0 R ⊤ s ) B i . Then

<!-- formula-not-decoded -->

Equivalently, introducing the rotated state ˜ h t := ( ∏ t s =0 R ⊤ s ) h t ,

<!-- formula-not-decoded -->

## C.3 PROOF OF PROPOSITION 4

Proposition 4 (Rotary Embedding Equivalence with Trapezoidal Discretization) . Discretizing a complex SSM with the trapezoidal rule (Proposition 1) yields the recurrence

<!-- formula-not-decoded -->

Here R t is the block-diagonal rotation matrix defined in Proposition 3.

Proof. We begin from the complex SSM (as in Prop. 2)

<!-- formula-not-decoded -->

where A ( t ) ∈ R is a scalar and θ ( t ) , B ( t ) , ˆ B ( t ) , C ( t ) , ˆ C ( t ) ∈ R N/ 2 .

Recall from Prop. 5,

<!-- formula-not-decoded -->

Applying Prop. 1 to the above integral, we get wherem

<!-- formula-not-decoded -->

Since e ∆ t ( A t + i θ t ) = α t e i ∆ t θ t and as shown in Prop. 2, multiplication by e i ∆ t θ t is a block-diagonal rotation in real coordinates, we get the real N -dimensional recurrence

<!-- formula-not-decoded -->

where R t = Block ( { R (∆ t θ t [ i ]) } N/ 2 i =1 ) where R (Θ) = [ cos Θ -sin Θ sin Θ cos Θ ] , and projections

<!-- formula-not-decoded -->

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

Figure 4: Contrasting Mamba-2 and Mamba-3 Architectures: Key updates include trapezoidal discretization, data-dependent RoPE embeddings, MIMO projections, QK normalization, and learnable biases.

![Image](data:image/png;base64,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)

We define the following,

<!-- formula-not-decoded -->

Left-multiplying equation 19 by ∏ t s =0 R ⊤ s and using R ⊤ t R t = I ,

<!-- formula-not-decoded -->

This is a vanilla scalar-transition SSM with data-dependent rotary embeddings absorbed into B , C via cumulative products of R ⊤ s .

## D MIMO FOR MAMBA-3

With hindsight from Mamba and with inference in mind, we propose the following MIMO formulation:

Mamba with MIMO. With a given batch, head, and sequence position t , consider the input U t ∈ R D . Also denote P, R ∈ N as the head dimension and MIMO rank, respectively. We first obtain SSM parameters via a set of projections defined in terms of tensor contraction notation as follows:

<!-- formula-not-decoded -->

where W B , W C , W X ′ , W X are model parameters. Additionally, we obtain the residual term Z t in the same manner as X t with weights W Z ′ and W Z . The state update and the SSM output is then computed via the following MIMO SSM:

<!-- formula-not-decoded -->

The intermediate output Y ′ t is obtained via some residual function ϕ , Y ′ t ← ϕ ( Y t , Z t ) . Finally, the layer output O t ∈ R D is computed via the following down projections:

<!-- formula-not-decoded -->

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

This formulation enhances the existing Mamba3 architecture by providing a lightweight parameterization that transforms the set of independent SISO SSMs within each head into a set of MIMO SSMs. Here, we note that the hardware-efficient chunking technique employed by Mamba2 for pretraining can be applied with little change, as the MIMO dimension r is orthogonal to the sequence dimension.

## E EXPERIMENTAL DETAILS

Language Modeling. Our pretraining procedures follow that of Dao &amp; Gu (2024)'s section D.2. All models at each scale follow the same procedure and were trained with bfloat16. The Mamba family of models were trained using the standard expand factor of 2 and a dstate of 128 and head dimension of 64. The Transformer baselines follows Dao &amp; Gu (2024), and the Gated DeltaNet baselines follow (Yang et al., 2025a). We utilize the Llama-3.1 tokenizer (Grattafiori et al., 2024) for all models.

We utilize LM Evaluation Harness (Gao et al., 2024) to test the zero-shot languag modeling capabilities of our pretrained model on LAMBADA (OpenAI version) (Paperno et al., 2016), HellaSwag (Zellers et al., 2019), PIQA (Bisk et al., 2019), Arc-Easy/Arc-Challenge (Clark et al., 2018), WinoGrande (Sakaguchi et al., 2019), and OpenBookQA(Mihaylov et al., 2018).

Real-World and Synthetic Retrieval. For our real-world retrieval tasks, we evaluate on the common suite consisting of SWDE (Arora et al., 2025b), SQUAD (Rajpurkar et al., 2018), FDA (Arora et al., 2025b), TriviaQA (Joshi et al., 2017), NQ (Kwiatkowski et al., 2019), and DROP (Dua et al., 2019). We utilize the cloze-formatted version of the aforementioned tasks provided by Arora et al. (2025b; 2024), as the original datasets are in a question-answering format, making it challenge for solely pretrained models. All tasks were truncated to match the training context length. The synthetic NIAH tasks (Hsieh et al., 2024) were also run with LM Evaluation Harness.

State-Tracking Synthetics. Training follows a sequence length curriculum that progresses from 3 -40 to 160 , evaluated at 256 . Each curriculum runs for 10 4 steps with batch size 256 . We use 1 layer models for Parity and 3 layer models for Modular-arithmetic tasks. The state size is chosen to be 64 , and we sweep d model ∈ { 32 , 64 } and 8 learning rates logarithmically spaced between 10 -4 and 10 -2 , reporting the best validation accuracy.

## F ADDITIONAL EXPERIMENTAL RESULTS

Figure 5: Pretrained 1.5B models' performance on the held-out FineWeb-Edu test set at varying context lengths. Mamba-3 exhibits strong length extrapolation while Mamba-2 falters at longer contexts.

![Image](data:image/png;base64,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YMuWLbNnz16wYMGIESP4EoZhkpOTp0yZsnLlyu3bt4fXvBuJ3++fO3fu6NGj+VuBomho/w1FUXfddZdCoXjxxRe71aPi8/mefPLJ7OzstWvXrlu3bvTo0c8880xTUxMAgOM4giCKi4tXr169devWcFsaNlAU9fv9L7300jPPPDNjxowPP/xwy5YtJ06cAACQJJmXlzdu3Lj58+efPn063JZeF1AUnTdv3q5duzZs2GCxWObMmRPqnprN5qlTp2ZnZy9YsADHcXDBcXrooYcaGxvnz5//O6aSgeoFAAAURQ0bNmzNmjVbt2596qmnSJIMt0U3lK1btz722GMvv/xycXGxUMiyrEQief/998eNG/fAAw/s3r07jBbeSGpqavbu3btv377JkydPnjz5wIEDpaWl999/v91uR1GUoqiBAweuXbv2hx9+KC4u9nq94bb3BlFSUnLkyJEXX3xxwIABvXr1eumll2w227fffgsA4DgORdF33nnn/vvvf+CBB/7zn/+E29jwEBsbi2FYnz59+NV+/fq53W4+5IdhmMjIyFWrVhkMhokTJ1ZUVITV0uuFTqeLj48fO3bsk08+uXPnTpPJxJfX19ffd999er1+1apVoQMMKIq67777li5d+uGHH7766qu/9XTdTr3EYjGCILz4h0KSZJ8+fTZu3Lh9+/Ynnnii+7xWb9++ffr06a+88srMmTPbzdvNsqxYLF66dOldd91111137dixI1xG3kgiIyNfeeWVUaNG9e7du0+fPlqtVq1W9+7dW2iUDwaDvXv3/uabb/bs2fPoo492k0eFj0QVXpBZluUbi4RVgiAWLlz45z//eerUqd1BwAiCQBCEIAihJDs7Oyoqqry8nF+tqqqSy+XCQECapvV6/dq1a9PT08eNG8fP1thVsdvtGIbxP7NNTU0PPPCARqPZvHnzpSEFgUBg3Lhxq1atWrp06YsvvvibPLBuFLXR0tKyefPmurq6urq6rVu3er3ewsLCYcOGcRwXCAT4P86ioqKvvvpqypQp06dP/+ijj9Rqdbitvr4cP3783nvvjYiIIEly4cKFDMNERUVNnjxZqVTSNM3fFhRFFy1aRFHUtGnTvvjiixEjRmAYFm7DryMRERGPP/64sPrjjz/SND1nzhwAQCAQ8Pv9/KNSWFjIPyqPPfbY8uXLhfHLXZX+/ftHRkY+//zz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)

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

1182 1183 1184 1185 1186 1187 We also compare the effectiveness of state size usage of Mamba variants to a Gated DeltaNet baseline in Figure 7. We highlight the difficulty of directly comparing GDN versus Mamba-style models due to the differing head structure, multi-head compared to multi-value respectively. Our experiments hold GDN's v expand to 2 and decrease the head dimension accordingly to vary the relative total state size. Similar to Figure 3, we train 440M models to 2 × Chinchilla tokens and sweep across d state = { 32 , 64 , 128 } for the Mamba models and d head dim = { 32 , 64 , 128 } for GDN. We parameter match all models.

Table 6: Downstream language modeling evaluations on parameter-matched pretrained models, including Mamba-3 MIMO. Mamba-3 MIMO's average accuracy on all tasks is more than 1 percentage point better than the next best (Mamba-3 SISO).

| Model               | FW-Edu ppl ↓   | LAMB. ppl ↓   | LAMB. acc ↑   | HellaS. acc n ↑   | PIQA acc ↑   | Arc-E acc ↑   | Arc-C acc n ↑   | WinoGr. acc ↑   | OBQA acc ↑   | Average acc ↑   |
|---------------------|----------------|---------------|---------------|-------------------|--------------|---------------|-----------------|-----------------|--------------|-----------------|
| Transformer-440M    | 13 . 03        | 21 . 2        | 41 . 7        | 50 . 5            | 69 . 9       | 67 . 6        | 34 . 6          | 56 . 7          | 26 . 0       | 49 . 6          |
| Gated DeltaNet-440M | 13 . 12        | 19 . 0        | 40 . 4        | 50 . 5            | 70 . 5       | 67 . 5        | 34 . 0          | 55 . 3          | 25 . 8       | 49 . 1          |
| Mamba-2-440M        | 13 . 00        | 19 . 6        | 40 . 8        | 51 . 7            | 70 . 6       | 68 . 8        | 35 . 0          | 54 . 1          | 26 . 0       | 49 . 6          |
| Mamba-3-440M        | 12 . 87        | 19 . 6        | 40 . 2        | 51 . 7            | 71 . 9       | 68 . 9        | 34 . 4          | 55 . 8          | 26 . 0       | 49 . 8          |
| Mamba-3-MIMO-440M   | 12 . 72        | 17 . 1        | 43 . 4        | 52 . 8            | 70 . 8       | 69 . 6        | 35 . 6          | 56 . 3          | 28 . 4       | 51 . 0          |
| Transformer-880M    | 11 . 42        | 15 . 0        | 44 . 7        | 57 . 2            | 72 . 6       | 71 . 6        | 39 . 2          | 57 . 7          | 26 . 8       | 52 . 8          |
| Gated DeltaNet-880M | 11 . 39        | 12 . 7        | 47 . 1        | 57 . 5            | 72 . 6       | 72 . 5        | 38 . 8          | 57 . 9          | 30 . 6       | 53 . 9          |
| Mamba-2-880M        | 11 . 35        | 13 . 8        | 45 . 0        | 58 . 1            | 72 . 5       | 72 . 3        | 38 . 7          | 56 . 8          | 30 . 2       | 53 . 4          |
| Mamba-3-880M        | 11 . 23        | 12 . 9        | 47 . 2        | 58 . 8            | 73 . 6       | 72 . 7        | 40 . 2          | 58 . 4          | 30 . 0       | 54 . 4          |
| Mamba-3-MIMO-880M   | 11 . 11        | 11 . 8        | 49 . 5        | 59 . 2            | 73 . 7       | 74 . 7        | 41 . 2          | 59 . 9          | 28 . 6       | 55 . 3          |

Figure 6: Mamba-3 demonstrates superior performance compared to strong baselines like Mamba-2, Llama, and Gated Deltanet. These are 440M models, trained and evaluated on FineWeb-Edu.

![Image](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAkYAAAHuCAIAAAD1GFQlAAEAAElEQVR4nOyddVwU3ffHz2yzdEuDgKIoioKEChKC3d39+NiKCSIWiAp2t4/dHaiAqIAYiIoI0t25wPbM7495nv3xhV0TFPS+//CFs2fu3jO7O5+59557DkYQBCAQCAQC0fKh/eoOIBD1EQqFOI4DAJ1Op1Aov7o7jYNIJBKLxfCfUwRBiEQiHMcxDKPT6RiGNTylrg2DwfjBDpBX9TNv99tAEIRQKCQIolGuW702KRQKnU5vlDYRTQGGRmkIkurq6mfPnlVXVwMAg8FwcnJSUVGRvJqQkJCQkIBhGEEQrVu37tKlSxN1A8dxLy+vR48esVisPXv22NnZNWLjHA7n1atXaWlpubm5XC5XUVGxbdu2nTt3NjU1lWpfWFj47NkzgiDk5OT69u1bT1+fPHlSVFREEIStra2xsfHn33rVqlW3bt1iMBhBQUGurq7l5eVz58599+6doqLi3bt3VVVVG55SUlIyd+7chIQERUXFe/fuKSsrf42PNTU1PB6PIAglJSXJDV0oFI4fP/7jx4+tWrXas2dP27Ztv6ap7yMqKiovL6+uajKZTDMzMwsLi6Z707rk5ubOmzcvJSVFS0vrzp07LBbrx9tMSkqaN29eQUFB+/btT58+TafTxWIxh8MRi8U0Gu0rPxrEz4BAIAiCIIikpCRdXV3JF+PkyZOSl4RCobOzs+SlKVOmNF03xGLxgAEDAADDsIcPHzZu4+Hh4VQqtd5PwNzc/MqVK1LtExISNDU1SbM3b97UfamkpERNTQ0AKBTK1/Rz1KhRZDuXL18mCKKwsLB9+/akm6QuNiQvL69Dhw4AwGQyS0tLv9LHoKAgW1tbGxubur3i8Xjm5uYAoKysHBsb+5VNfR/u7u4N7zPGxsaTJ0/Oy8tr0rcmSU1NJZ9R1NTUampqGqXN2NhYUrfatGlDPjF8+vSpX79+tra2Y8eOFQgEjfIuiB8HTTwi/oVCobDZbMl/jx49Om7cOBqNBgBRUVGRkZGSl5hMZpP2hFQdGo3W6PNjAoHA0NCwbdu2WlpafD4/KioqOzs7OTl57dq1Dg4OOjo69ezbtWvXt2/ff/75BwAuXrzYuXNnyUt37twpKysDACcnJwcHhy++NekUhUIhnWKz2X/99VdmZiabza572euCYZjkUny9j5mZmS9fvgSAioqKuu8+Z86c7OxsVVXVVq1afX1r34FkVKStra2trV1bW5uampqRkZGRkcHhcM6cOdMow6bPgGEYecW+6bp9nlatWi1durS8vNzAwID8UIRC4YsXL0pKSqqqqhrxjRA/CPokENKJioqKjo7u2bMnABw/flwkEjW0qampefXqVVJSUlFREZ/PV1JS6tatm52dneSeVVJS8vz5c6FQqKur26lTpzt37rx7987MzGz48OFsNrugoOD69et5eXldu3bt169fwyUKOp2emZl59erViooKJycnV1dXicgVFha+fv06NTW1rKxMLBZraWk5Ozt36NDh8yrYtWvX+/fvt2nThvzvkydPPDw8+Hx+ZmZmenp6Q0kDgJEjR54+fRrH8dDQ0PLycnKGkCCImzdvkgb9+vWTl5dPS0t78+ZNRkZGVVUVABgbG7u4uHxmNpLBYHTr1q1t27Y0Gq2u4x8/frx9+zaPx3NxcTEzM6s31SkWixMSEt6+fZubm1tTU0Oj0Tp06NCjRw8tLS0A4HA40dHRqamppHFMTAyLxRKLxdbW1oaGhnZ2du3atWOxWAoKCpIGeTze06dPX758yePx9PX1+/TpY2hoKHn1zZs36enpVCrVzs6OQqFcuXIlPz+/c+fO/fr1+xpZmjlz5t9//83lcm/cuLFixQqRSPTgwYPY2FhHR0fSICcnJyQkJDMzU05OrkePHg4ODhJtKC4ujo6OFovFhoaGHTt2vHfv3qtXr5ydnXv06BEVFVVRUcFmsz08PGJiYkJDQ6lU6qBBgywtLT/fn+rq6idPnrx69UosFrdv3753797kOJsgiOjo6Pz8fBqN1rVrV319fdI4PDxcKBQqKCg4OzsrKir27NmTx+MpKyvTaLTExMSQkBBycZTL5V65coVKpWpqaiopKaWlpREEYWlpKfmaVVZWRkZG8vl8VVVVJyen32Z5uJnyi0eJiGZDcnKymZkZAMjLy9va2gLApEmTCIKIj49v1aoV+Wsnb75//fUXeQo5fKkLjUazt7f/8OEDaRAREaGgoEChUOzt7fv37y8xGzx48J07dySLKxQKZfz48VVVVQRBiMXiwYMHAwCLxZo5cyZ5syZbnjZtWmVlJdnyvHnz6r01k8kcN25cRUXF17uckpJC3ppNTEzIO1FDampqyJUnFot1//598iB5TQBA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)

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

Figure 7: Exploration of state size (inference speed proxy) versus pretraining perplexity (performance proxy). Mamba-3 and Mamba-3 MIMO continue set the Pareto frontier.

![Image](data:image/png;base64,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20EYAOLi4p544gn2c2MY5t133w289wHcbrfVanU4HJs3b8YwjA1vBEFMmDBh3rx5gdNomr711ltzc3NdLlfg4Pfff8/n8w8cOBB0SFVVVStXrgwkjyQnJz/99NPsB878PEr198QTT/D5/D179rA/Pv7440ql0m63B04oKytTqVSbNm0K+qLIaITWpZCRJTIyMj4+3uv1ms1muVyel5fHJkQ0NjZardZvvvmmtraWTSvgcrlnz57t6emxWq2XLrN/+eWXmzdvLi4uDgkJ4fP5LpeLy+W63W4AYBgm8N+gRCLRihUr/vrXv547d27q1KktLS1ffPHFxo0bQ0JCAOD06dMA8D//8z9cLpdhGAzDKIrS6/WNjY2DfI8Wi6WtrW3SpEn9E/ymTJnyr3/9q62tLScnJ+gIz549+7//+79HjhzhcDhCoRDHca/X29vbO5hXTEpK2rRp09///veampoTJ04cOHDglVdesVgsO3fuZNeTLn25H3744dVXXz1x4gSbl+HxeLhcrt1uT0pKuvSjs1qtzc3NNpvtwQcfZBPzMAzr7e0lCMJgMAQdUmZm5jvvvPPaa69VVFScPHly7969zz33nMvl+uc//3m5/PtXX3311VdffeONN/7jP/4DAAiCOHnyJE3Tq1evZt8FhmFut7u7u7uurm4wHwsyKqAohYwU7HffE088sWDBAgBoampavHjxypUri4uLZTIZ+92n0+mSkpIC+eJpaWnh4eEREREDLlVVVXX33XdPmzZt586d4eHhPB5v7969/+///b8rRKYB7rjjjv/+7/8+dOjQ1KlT9+zZIxaL582bxz7k8/nEYnFaWhobpdiDOTk5GRkZg7w4uxgzYLMR++Pl8vq6u7uXL1+uUCg2b94cHR0tEAhKS0vZ2dsgXxQAFArFpEmTJk2atGrVqsWLF+/du/fZZ59lF6UGqKuru/fee5OSkv79739HRkay9zOfeuqpy12ZJEmCIJRKZWZmZmAzAIZh48aNGz9+/BWGpFQqb7nllltuueX++++fM2fO/v37H3300aBb1j7++OP169c/+uija9euDRz0+XxhYWGpqakcDof9KDAMGz9+/MSJEwf3kSCjAIpSyMgS+I5LSkrauHHjihUrtm3b9sQTT0RERAgEgnHjxj3yyCNXvcjevXuFQuFLL70UiBz79u0jCCJwwlW/3KOjo++8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)

## G ARCHITECTURE ABLATIONS

We explore our model architecture's ablation in this section. All models are trained at the 440M scale to Chinchilla optimal number of tokens ( 20 × tokens to parameters) with the same experimental procedures as our pretrained models as covered in Appendix E unless otherwise stated.

B,C Bias Parameterization. The Mamba-3 model's separate B and C biases are head-specific and channel-wise and added to both B and C after the QK-Norm. While the biases in the final Mamba-3 model are trainable, data-independent parameters and initialized to all ones, we explore various bias parameterizations in Table 7a. We find our models are not very sensitive to the initialization of the biases as long as they are positive. We choose the all-ones initialization due to it's simplicity.

We also explore the impact removing the B or C bias on performance in Table 7b (bias is initialized with our default parameterization when utilized). Unlike in Yu &amp; Erichson (2025), which finds that B bias by itself is able to improve performance on Mamba-1, our experiments find that only having B bias hurts performance slightly and that B and C biases have synergetic properties.

| Bias Init.   | Trainable   |   ppl ↓ |
|--------------|-------------|---------|
| 1.0          | ✓           |   15.72 |
| 0.0          | ✓           |   16.57 |
| 1.0          | ×           |   15.8  |
| U (0 , 1)    | ✓           |   15.76 |
| U ( - 1 , 1) | ✓           |   16.07 |

(a) Effect of parameterization of the B and C bias on model performance, measured by pretraining perplexity. We find our default initialization of allones (first row) provides the best performance, but performance is not sensitive as long as biases are positive.

| B Bias   | C Bias   |   ppl ↓ |
|----------|----------|---------|
| ×        | ×        |   16.52 |
| ✓        | ×        |   16.68 |
| ×        | ✓        |   15.98 |
| ✓        | ✓        |   15.69 |

(b) Applying a bias to both B and C leads to the best performance. Only applying B bias (BlockBiased (Yu &amp; Erichson, 2025) Mamba-3 variant) does not provide significant gains over the no-bias baseline.

Table 7: Ablations on B,C bias initialization (left) and presence (right) for Mamba-3.

## H INFERENCE KERNEL LATENCY ANALYSIS

## H.1 KERNEL IMPLEMENTATIONS AND FUSION STRUCTURE

In Table 3, we detail the DSL (Triton, CuTe, PyTorch) and the fusion level of the kernels used in our latency analysis. For Mamba-2 and Gated DeltaNet (GDN), we directly use the publicly released Triton kernels from the respective authors. For Mamba-3, we implement new inference kernels with a comparable fusion structure: the forward uses a Triton kernel fused with rotary position embeddings, while the decode path uses a CuTe kernel fused with gating and MIMO projection.

1241 In Tables 8 and 9, we abbreviate IP = input projection, Conv = 1D convolution, Gate = gating, OP = output projection. Colors indicate implementation backend (Torch, Triton, CuTe).

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

Table 8: Kernel DSL and fusion structure for forward (prefill) kernels.

| Model (Forward)   | Kernel DSL   | Fusion Level                     |
|-------------------|--------------|----------------------------------|
| Mamba-2           | Triton       | IP, Conv, SSM, Gate+OP           |
| Gated DeltaNet    | Triton       | IP, Conv, Chunked Delta, Gate+OP |
| Mamba-3 (SISO)    | Triton       | IP, SSM+Rotary, Gate+OP          |
| Mamba-3 (MIMO)    | Triton       | IP, SSM+Rotary, Gate+OP          |

Table 9: Kernel DSL and fusion structure for decode kernels.

| Model (Decode)   | Kernel DSL    | Fusion Level                       |
|------------------|---------------|------------------------------------|
| Mamba-2          | Triton        | IP, Conv, SSM, Gate+OP             |
| Gated DeltaNet   | Triton        | IP, Conv, Recurrent Delta, Gate+OP |
| Mamba-3 (SISO)   | CuTe + Triton | IP, Rotary, SSM+Gate+OP            |
| Mamba-3 (MIMO)   | CuTe + Triton | IP, Rotary, SSM+Gate+OP+MIMO       |

## H.2 EXTENDED PREFILL AND PREFILL+DECODE LATENCY MEASUREMENTS

Models. Webenchmark Mamba-3 1.5B (SISO), Mamba-2 1.5B, Gated DeltaNet (GDN) 1.5B, and a strong Transformer baseline implemented via the vLLM engine (v0.11.0) with Llama-3.2 1B. 3 All recurrent models are trained at the 1.5B scale with d model = 2048 and 24 layers. For Mamba variants we set state size as 128 and head dimension 64 ; for GDN we use QK head dimension as 128 .

Setting. Sequence lengths were swept over L ∈ { 512 , 1024 , 2048 , 4096 , 16384 } for prefill, with an equal number of tokens decoded. For sequence lengths { 512 , 1024 , 2048 , 4096 } , we use batch size of 128; for sequence lengths { 16384 } , we use batch size of 16. We use a single H100-SXM 80GB GPU and report wall-clock times (in seconds) over 3 repetitions.

Table 10: Prefill and Prefill+Decode latency across sequence lengths.

| Model               | 512 tokens   | 512 tokens   | 1024 tokens   | 1024 tokens   | 2048 tokens   | 2048 tokens   | 4096 tokens   | 4096 tokens   | 16384 tokens   | 16384 tokens   |
|---------------------|--------------|--------------|---------------|---------------|---------------|---------------|---------------|---------------|----------------|----------------|
|                     | Prefill      | Prefill+Dec  | Prefill       | Prefill+Dec   | Prefill       | Prefill+Dec   | Prefill       | Prefill+Dec   | Prefill        | Prefill+Dec    |
| vLLM (Llama-3.2-1B) | 0.26         | 4.45         | 0.52          | 9.60          | 1.08          | 20.37         | 2.08          | 58.64         | 1.52           | 122.06         |
| Gated DeltaNet      | 0.48         | 4.52         | 0.95          | 9.04          | 1.90          | 18.07         | 3.79          | 36.14         | 1.91           | 71.66          |
| Mamba-2             | 0.48         | 4.62         | 0.96          | 9.24          | 1.91          | 18.48         | 3.81          | 36.94         | 1.92           | 57.90          |
| Mamba-3 (SISO)      | 0.48         | 4.33         | 0.95          | 8.64          | 1.90          | 17.29         | 3.80          | 34.57         | 1.91           | 53.97          |

We observe that (i) Mamba-3 adds minimal forward-pass cost showing that the trapezoidal update, complex state tracking, and MIMO parameterization remain lightweight; (ii) decode latency is competitive across recurrent models; and (iii) recurrent mixers scale more gently with context length than vLLM Llama-3.2-1B, which grows much faster with L due to KV-cache overhead.

3 https://huggingface.co/meta-llama/Llama-3.2-1B