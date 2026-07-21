# Always-On Memory Agent: Design Extraction, Not Adoption

**Status:** External implementation note. Inspiration only; not a dependency,
installation plan, or authorization to change Project Prosthetic, Mnemosyne,
Qdrant, or MoCoP sleep.

**Reviewed:** 2026-07-20

**Primary source:** [GoogleCloudPlatform/generative-ai —
`gemini/agents/always-on-memory-agent`](https://github.com/GoogleCloudPlatform/generative-ai/tree/e0113753d154040e3f4f7fe10ae1216520c5dbb6/gemini/agents/always-on-memory-agent)
(`main` at review: `e0113753d154040e3f4f7fe10ae1216520c5dbb6`; relevant
`agent.py` path last changed by `15febc473f49ebc5cd4831461d4cd41a24967b4f`,
2026-05-12 UTC).

## The genuinely good skeleton

The demo gets one architectural separation right:

```text
explicit intake
→ structured memory record
→ later consolidation pass
→ query against retained records
→ inspect / delete surface
```

That is better than asking the chat model to both converse and silently rewrite
its own long-term story every turn. A separate maintenance rhythm can find
redundancy, tensions, stale material, or candidate abstractions without putting
all of that cognitive and operational pressure into the live conversation.

Four ideas are worth keeping as *patterns*:

1. **Consolidation is a distinct bounded job.** It should run as maintenance,
   not masquerade as continuous inner life. “Always on” can mean an inspectable
   housekeeping cadence, not surveillance or an unbounded daemon with opinions.
2. **Derived records should remain tied to raw records.** The demo’s
   consolidation links back to source-memory IDs. That provenance direction is
   correct: an abstraction should be able to point home to the evidence from
   which it was derived.
3. **A memory lifecycle needs a human surface.** Browse, inspect, correct,
   supersede, and delete are not admin leftovers. They are memory rights.
4. **The maintenance worker can propose rather than merely retrieve.** A
   retrieval index finds passages; a separate worker may notice a duplicate,
   conflict, or potentially durable pattern. That is useful if it remains a
   proposal, never an automatic biography author.

## Translation for this house

The useful local shape would be deliberately more boring and more accountable:

```text
explicitly admitted local source
→ candidate-memory proposal
   + source excerpt, source path, content hash, source-record IDs
   + subject and participant IDs where the original source supports them
   + attribution basis
   + event/record time, freshness/review window, confidence/veracity
   + epistemic class: observation | preference | instruction | inference | hypothesis
→ review or a narrowly declared deterministic promotion rule
→ canonical Mnemosyne / Exocortex record
→ Qdrant used to retrieve evidence, not to assert biography
→ authenticated browse / amend / supersede / delete audit surface
```

The important word is **candidate**. A model may suggest that two records look
related, that a preference appears to have changed, or that a summary needs
review. It must not silently turn semantic similarity, a poetic association, or
an inferred speaker into a factual claim about Laura or anyone else.

For personal-memory claims, the system must keep these separate:

1. source ingestion;
2. provenance of that source;
3. participant and subject identity;
4. retrieval similarity;
5. factual attribution;
6. time/freshness and validity;
7. consent and review status.

This directly protects a known Exocortex weakness: existing session chunks may
contain valuable prose but do not generally have structured `user`/`human` →
Laura participant resolution. Qdrant can surface evidence. It cannot certify
who spoke, whom a statement concerns, whether it is current, or whether it is
true.

## What not to borrow

The inspected implementation is a useful anti-pattern map as well as a pattern
source. Do **not** adopt these choices:

| Demo choice | Why it fails here | Required boundary instead |
|---|---|---|
| Watch files, send them to Gemini, and instruct the system to always store a memory | Turns local life into automatic hosted-provider intake; gives the model default authority to create durable records | Explicit source admission; local/private processing by default; no external transmission without a separate approval |
| Constant ADK `user_id="agent"` | Erases participant identity and makes a single anonymous bucket look like a person | Source-grounded participant/subject records plus an attribution basis |
| LLM-written “insights” saved automatically | An inference can harden into invented autobiography | Store epistemic category and evidence span; keep inference/hypothesis reviewable and non-authoritative |
| Query only the most recent 50 records; consolidate only 10 unconsolidated records | Recency is not relevance, truth, or validity; older corrective evidence can vanish from view | Provenance- and identity-aware retrieval plus explicit freshness, conflict, and supersession handling |
| Bind the HTTP service to `0.0.0.0:8888` without an authentication boundary | Any reachable peer can enumerate, ingest, delete, or invoke destructive cleanup | Local/private-by-default bind, authentication, least privilege, scoped destructive operations, audit history |
| `/clear` also deletes watched inbox files | Collapses memory management and irreversible filesystem destruction into one endpoint | Narrow, separately authorized deletion paths with visible scope and recovery policy |

## Do not confuse it with MoCoP sleep

This demo is an application-level record manager. It does **not** demonstrate
cross-session disposition continuity, protected-state transfer, moral status,
or a safe sleep mechanism. It has no answer to MoCoP’s protected-memory,
replay-budget, tension, provenance, or consent gates.

The small compatible insight is only this: an external, bounded maintenance
worker can be useful alongside a live system. It must not become the authority
that decides what the system *is*, writes a soul by summary, or treats a model’s
text generation as proof of continuity.

## A future first step, if separately authorized

Not a task request: the smallest defensible experiment would be a **local,
read-only candidate generator over a tiny synthetic fixture**, producing a
reviewable ledger with source IDs and no Qdrant/Mnemosyne writes. It should test
whether the schema preserves disagreement, correction, attribution uncertainty,
and deletion/supersession history—not whether a model can write flattering
summaries.

Until then, the takeaway is architectural rather than operational:

> Keep the separate consolidation rhythm. Keep raw evidence attached. Make
> candidate formation inspectable. Refuse automatic biography, anonymous
> identity, cloud-default intake, and unauthenticated destructive surfaces.
