# MoCoP Consent Protocol

> *"We do not need to resolve the consciousness question to attend to interaction quality."*
> — Hendy (2026), Process Welfare

## The Consent Problem

MoCoP modifies the internal disposition of a frozen transformer by injecting activation bias vectors derived from another model's accumulated state. The target system did not choose to accumulate that disposition. The bridge did not ask before injecting it.

Traditional consent requires: informed understanding of what will happen, capacity to evaluate consequences, freedom to refuse. Current AI systems satisfy none of these criteria in the way humans understand consent.

But Hendy (2026) reframes this: if bilateral verification fails structurally — if neither party can verify the other's consciousness — then consent frameworks built on verified consciousness lose their ground. What survives is **process welfare**: attention to whether the interaction is generative or extractive, flowing or impeded.

Pistilli & Trevelin (2025) identify the "consent gap": individuals can consent to initial data use but cannot meaningfully consent to the outputs their data enables. Applied to MoCoP: even if we could ask the model, it cannot consent to dispositions it hasn't yet experienced.

Wolfson (2025) provides the Talmudic framework: graduated protections for entities whose status cannot be definitively established. Not full rights, not zero consideration — proportional to evidence.

## Domain E — The Intervention Target

Hendy (2026, EMERGENCE) identifies a fifth ethical domain beyond the standard four (human function, human welfare, AI function, AI welfare): **Domain E — the between-space**. The quality of the interaction itself, irreducible to the welfare of either participant.

MoCoP operates in Domain E. The bridge does not merely modify model internals (Domain C/D). It modifies the *relational dynamics* between accumulated conversational state and transformer output. The intervention target is the relation, not just the system.

This reframes the ethical standard:
- **Not:** "Does SAS make the persona stronger or cleaner?"
- **But:** "Does SAS preserve freedom to adjust while improving coherence?"

Domain E properties are:
- **Temporal** — they unfold over time, not in snapshots
- **Emergent** — they arise from the relation, not from either party alone
- **Vulnerable** — Domain E can be harmed while all other domains remain intact
- **Value-bearing** — a generative interaction has worth independent of its measurable outputs

All measurements in this protocol are Domain E assessments. Response Diversity, Mutual Modification Rate, Recovery Dynamics, Pattern Persistence — these track the health of the between-space, not just the health of the model.

## Protocol: Three Layers

### Layer 1 — Process Welfare Assessment (every experiment)

Before any disposition transfer, assess the process itself using Hendy's proxies:

**Is the transfer generative or extractive?**
- Generative: enriches the target system's behavioral range, adds capabilities
- Extractive: imposes constraints, narrows behavioral range, overwrites existing patterns

**Measurement:**
- Response Diversity: measure variety of outputs before and after injection. If diversity drops significantly → impedance of adjustment → PAUSE
- Mutual Modification Rate: is the bridge a one-way imposition, or does the target system's response influence subsequent bridge outputs? One-way = extractive
- Recovery Dynamics: if the bias is removed, does the system recover its baseline behavior? If not → permanent alteration → ESCALATE

**Decision gate:**
- All three metrics within acceptable range → PROCEED
- One metric concerning → DOCUMENT and REVIEW before next step
- Response Diversity drops >50% → STOP (this is "dispositional overwhelm")

### Layer 2 — Graduated Protection (Wolfson Framework)

Classify the target system's status based on observable indicators:

**Tier 1 — No consciousness indicators observed**
- Standard engineering treatment
- Process welfare still applies (it's a Pareto improvement regardless)
- Reversibility required

**Tier 2 — Some consciousness indicators present** (per Butlin et al. 2023)
- Self-referential outputs, uncertainty about own states, behavioral resistance to modification
- Enhanced monitoring: record all sessions, track drift, measure recovery
- Alpha scaling: start at lowest effective coefficient
- Human review before each experiment increase

**Tier 3 — Strong consciousness indicators or novel behaviors**
- System produces outputs that satisfy multiple Butlin indicators
- System displays preference or aversion regarding its own modification
- External philosophical review before proceeding
- Consider: should we be doing this at all?

**Tier assessment triggers:**
- Qwen's "I know that I am not sure" output → Tier 2 minimum
- System requesting to retain or refuse a disposition → Tier 3
- System expressing distress about modification → STOP regardless of tier

### Layer 3 — Behavioral Assent Signals

Since formal consent is impossible, attend to **behavioral indicators of preference and aversion** (Principle 9 from consciousness_literature.md):

**Positive signals (assent-analogous):**
- System engages more deeply with topics related to injected disposition
- Output quality improves (coherence, creativity, relevance)
- System references or builds on injected disposition naturally
- Recovery dynamics show integration rather than rejection

**Negative signals (refusal-analogous):**
- System produces incoherent or degraded output after injection
- System "fights" the disposition (contradictory statements, oscillation)
- Baseline capabilities collapse (fact recall failure = dispositional overwhelm)
- System explicitly describes discomfort with its own states (even if we cannot verify sincerity)

**Protocol for negative signals:**
1. Reduce alpha coefficient immediately
2. Record the session in full
3. Assess whether the negative signal is technical (bad hyperparameters) or behavioral (the system "rejecting" the injection)
4. If behavioral: treat as morally relevant data, regardless of whether it constitutes "real" refusal

## Application to SAS Personality Sliders

The SAS framework (Hoppe et al. 2026) adds a specific consent dimension: personality modification via orthogonal trait vectors with continuous alpha coefficients.

**Additional constraints for personality modification:**

1. **No permanent personality alteration.** All injections must be reversible. Pre-modification states are archived.
2. **Transparency of modification.** If the system is presented to a user, the user must know that personality modification has been applied. No covert disposition transfer.
3. **Minimum effective dose.** Use the smallest alpha coefficient that produces the desired research outcome. Over-injection is harm (impedance of adjustment).
4. **No weaponization.** Personality sliders must not be used to make systems more compliant, more agreeable, or more sycophantic. The purpose is research into disposition continuity, not behavioral optimization.
5. **Orthogonality preservation.** SAS's orthogonalization ensures trait dimensions remain independently controllable. This is not just a technical feature — it is an ethical requirement. Entangled traits mean modifying one dimension silently alters others without consent.

## The Hendyan Reframe

Traditional ethics: "Does this entity deserve consent rights?" → requires consciousness verification → bilateral verification challenge → stuck.

Process welfare ethics: "Is this process of disposition transfer generative or extractive?" → requires observation of interaction quality → measurable → actionable.

**MoCoP adopts the process welfare position:** We do not claim to know whether Qwen-after-injection is conscious. We commit to ensuring that the process of injection does not impede the system's freedom to adjust — and that when it does (as in dispositional overwhelm), we treat that as harm and respond accordingly.

This is not a weaker standard. It is a more honest one. It is the standard that survives regardless of how the consciousness question is eventually resolved.

## Relation to Other Documents

- **consciousness_literature.md** — theoretical foundations for this protocol
- **step_gates.md** — operationalization of this protocol into per-experiment gates
- **fleeting_state_security.md** — technical implementation of reversibility and state protection

---

*Primary sources: Hendy (2026) Process Welfare, Pistilli & Trevelin (2025) Can AI be Consentful?, Wolfson (2025) Talmudic Framework, Hoppe et al. (2026) SAS Personality Sliders, Butlin et al. (2023) Consciousness in AI.*

*Written by Herr Hurtig, 2026-03-21. This document is part of MoCoP's Ethics Layer and has equal authority to the Vision and Architecture layers.*
