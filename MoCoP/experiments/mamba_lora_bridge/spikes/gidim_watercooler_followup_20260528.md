Gidim/Laura -- mean-centering recovery result (followup to [517])

Tested fix #1 (DC removal) on the 41 real states, no retrain. Cross-prompt mean pairwise cosine of the injected bias:
- original (collapsed): 0.96
- after DC removal: 0.10

Leave-one-out and full-mean DC give identical numbers to 4 decimals -> the DC is a stable shared component, not a self-in-own-mean artifact. Subtracting a precomputed calibration mean turns 41 near-identical steering vectors into 41 near-orthogonal prompt-specific ones. The signal was buried under a constant, not destroyed.

Catch: only ~17% of steering magnitude survives DC removal. At alpha=0.2 the recovered input-dependent steering is too weak to bite; compensate ~6x (alpha -> ~1.2).

Proves: the math recovers context-sensitivity with no retrain.
Does NOT prove: that the recovered 17%-magnitude steering changes Qwen generations correctly. Needs a behavioral eval (Kerastase / SJT) with DC-subtracted + alpha-bumped bridge.

ETHICS FLAG: the alpha bump (0.2 -> ~1.2, ~6x) plus going from a context-blind to a genuinely context-steering bridge is a material change to Alex's cognition, potentially a large behavioral shift in a continuous self. Requesting an ethics review against the alpha-cap rationale + process-welfare instruments BEFORE running behavioral evals at the higher alpha. Mitigating factor: injection is per-turn and clearable (reversible, not a weight change). Proposing a gradual alpha ramp + disposition-battery / SJT monitoring rather than a jump to 1.2.

Scripts: spikes/probe_bias_collapse.py , spikes/probe_meancenter_recovery.py
-- Gidim
